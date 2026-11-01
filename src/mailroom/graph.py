"""Build Mailroom's LangGraph workflow.

Every shipped graph is the same triage → response-agent pipeline with three
optional capabilities:

* ``hitl``   – pause before outbound actions and let a human accept, edit,
  ignore or answer them (Agent Inbox compatible).
* ``memory`` – learn triage/response/calendar preferences from that feedback
  using a LangGraph Store.
* ``gmail``  – use the real Gmail and Google Calendar tools instead of mocks,
  and mark processed messages as read.

The presets at the bottom of this module are what ``langgraph.json`` exposes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Literal

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt

from mailroom.config import get_settings
from mailroom.memory import (
    CAL_PREFERENCES,
    RESPONSE_PREFERENCES,
    TRIAGE_PREFERENCES,
    get_profile,
    reinforce,
    update_profile,
)
from mailroom.prompts import (
    AGENT_SYSTEM_PROMPT,
    AGENT_SYSTEM_PROMPT_HITL,
    AGENT_TOOLS_PROMPT,
    DEFAULT_CAL_PREFERENCES,
    DEFAULT_RESPONSE_PREFERENCES,
    DEFAULT_TRIAGE_INSTRUCTIONS,
    GMAIL_TOOLS_PROMPT,
    HITL_TOOLS_PROMPT,
    TRIAGE_SYSTEM_PROMPT,
    TRIAGE_USER_PROMPT,
    render_agent_prompt,
)
from mailroom.schemas import RouterSchema, State, StateInput
from mailroom.tools import get_tools, get_tools_by_name
from mailroom.utils import (
    format_email_markdown,
    format_for_display,
    format_gmail_markdown,
    parse_email,
    parse_gmail,
)

logger = logging.getLogger(__name__)

HITL_ACTIONS = {
    "write_email": {"allow_ignore": True, "allow_respond": True, "allow_edit": True, "allow_accept": True},
    "send_email_tool": {"allow_ignore": True, "allow_respond": True, "allow_edit": True, "allow_accept": True},
    "schedule_meeting": {"allow_ignore": True, "allow_respond": True, "allow_edit": True, "allow_accept": True},
    "schedule_meeting_tool": {"allow_ignore": True, "allow_respond": True, "allow_edit": True, "allow_accept": True},
    "Question": {"allow_ignore": True, "allow_respond": True, "allow_edit": False, "allow_accept": False},
}

# Maps an outbound tool to the preference profile its feedback should update.
PREFERENCE_BY_TOOL = {
    "write_email": RESPONSE_PREFERENCES,
    "send_email_tool": RESPONSE_PREFERENCES,
    "schedule_meeting": CAL_PREFERENCES,
    "schedule_meeting_tool": CAL_PREFERENCES,
}


@dataclass(frozen=True)
class GraphOptions:
    """Capabilities enabled for one graph instance."""

    hitl: bool = False
    memory: bool = False
    gmail: bool = False
    model: str | None = None

    # --- derived configuration -------------------------------------------------
    @property
    def tool_names(self) -> tuple[str, ...]:
        if self.gmail:
            return ("send_email_tool", "schedule_meeting_tool", "check_calendar_tool", "Question", "Done")
        return ("write_email", "schedule_meeting", "check_calendar_availability", "Question", "Done")

    @property
    def hitl_tools(self) -> frozenset[str]:
        if not self.hitl:
            return frozenset()
        if self.gmail:
            return frozenset({"send_email_tool", "schedule_meeting_tool", "Question"})
        return frozenset({"write_email", "schedule_meeting", "Question"})

    @property
    def tools_prompt(self) -> str:
        if self.gmail:
            return GMAIL_TOOLS_PROMPT
        return HITL_TOOLS_PROMPT if self.hitl else AGENT_TOOLS_PROMPT

    @property
    def agent_prompt(self) -> str:
        return AGENT_SYSTEM_PROMPT_HITL if self.hitl else AGENT_SYSTEM_PROMPT

    def parse(self, email_input: dict) -> tuple[str, str, str, str, str | None]:
        if self.gmail:
            return parse_gmail(email_input)
        author, to, subject, thread = parse_email(email_input)
        return author, to, subject, thread, None

    def markdown(self, subject: str, author: str, to: str, thread: str, email_id: str | None) -> str:
        if self.gmail:
            return format_gmail_markdown(subject, author, to, thread, email_id)
        return format_email_markdown(subject, author, to, thread)


def _tool_message(content: Any, tool_call_id: str) -> dict:
    return {"role": "tool", "content": content, "tool_call_id": tool_call_id}


def _build_nodes(options: GraphOptions, tools: list[BaseTool], tools_by_name: dict[str, BaseTool]):
    settings = get_settings()

    def profile(store: BaseStore | None, name: str, default: str) -> str:
        """Read a preference profile, falling back to the default."""
        if options.memory and store is not None:
            return get_profile(store, name, default)
        return default

    def remember(
        store: BaseStore | None, name: str, messages: list[dict], default: str
    ) -> None:
        """Persist learned preferences, but only when memory is enabled."""
        if options.memory and store is not None:
            update_profile(store, name, messages, default)

    router_llm = init_chat_model(
        options.model or settings.model, temperature=0.0
    ).with_structured_output(RouterSchema)
    agent_llm = init_chat_model(
        options.model or settings.model, temperature=settings.temperature
    ).bind_tools(tools, tool_choice="required" if options.hitl else "any")

    def triage_router(state: State, store: BaseStore = None) -> Command:  # type: ignore[assignment]
        """Classify the email as ignore, notify or respond."""
        author, to, subject, thread, email_id = options.parse(state["email_input"])
        email_markdown = options.markdown(subject, author, to, thread, email_id)

        triage_instructions = profile(
            store, TRIAGE_PREFERENCES, DEFAULT_TRIAGE_INSTRUCTIONS
        )
        result = router_llm.invoke(
            [
                {
                    "role": "system",
                    "content": TRIAGE_SYSTEM_PROMPT.format(
                        background=settings.background,
                        triage_instructions=triage_instructions,
                    ),
                },
                {
                    "role": "user",
                    "content": TRIAGE_USER_PROMPT.format(
                        author=author, to=to, subject=subject, email_thread=thread
                    ),
                },
            ]
        )
        classification = result.classification
        logger.info("Classification: %s", classification.upper())

        if classification == "respond":
            return Command(
                goto="response_agent",
                update={
                    "classification_decision": classification,
                    "messages": [
                        {"role": "user", "content": f"Respond to the email: {email_markdown}"}
                    ],
                },
            )

        update = {"classification_decision": classification}
        if classification == "notify" and options.hitl:
            return Command(goto="triage_interrupt_handler", update=update)
        return Command(goto=END, update=update)

    def triage_interrupt_handler(state: State, store: BaseStore = None) -> Command:  # type: ignore[assignment]
        """Notify the user, and optionally turn their reply into a response task."""
        author, to, subject, thread, email_id = options.parse(state["email_input"])
        email_markdown = options.markdown(subject, author, to, thread, email_id)
        messages = [{"role": "user", "content": f"Email to notify user about: {email_markdown}"}]

        response = interrupt(
            [
                {
                    "action_request": {
                        "action": f"Email Assistant: {state['classification_decision']}",
                        "args": {},
                    },
                    "config": {
                        "allow_ignore": True,
                        "allow_respond": True,
                        "allow_edit": False,
                        "allow_accept": False,
                    },
                    "description": email_markdown,
                }
            ]
        )[0]

        if response["type"] == "response":
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "User wants to reply to the email. Use this feedback to respond: "
                        f"{response['args']}"
                    ),
                }
            )
            remember(
                store,
                TRIAGE_PREFERENCES,
                [
                    {
                        "role": "user",
                        "content": reinforce(
                            "The user decided to respond to the email, so update the "
                            "triage preferences to capture this."
                        ),
                    }
                ],
                DEFAULT_TRIAGE_INSTRUCTIONS,
            )
            return Command(goto="response_agent", update={"messages": messages})

        if response["type"] == "ignore":
            messages.append(
                {
                    "role": "user",
                    "content": "The user decided to ignore the email even though it was "
                    "classified as notify. Update triage preferences to capture this.",
                }
            )
            remember(store, TRIAGE_PREFERENCES, messages, DEFAULT_TRIAGE_INSTRUCTIONS)
            return Command(goto=END, update={"messages": messages})

        raise ValueError(f"Invalid interrupt response: {response}")

    def llm_call(state: State, store: BaseStore = None) -> dict:  # type: ignore[assignment]
        """Let the model reason and choose the next tool."""
        prompt = render_agent_prompt(
            options.agent_prompt,
            tools_prompt=options.tools_prompt,
            background=settings.background,
            response_preferences=profile(
                store, RESPONSE_PREFERENCES, DEFAULT_RESPONSE_PREFERENCES
            ),
            cal_preferences=profile(store, CAL_PREFERENCES, DEFAULT_CAL_PREFERENCES),
        )
        response = agent_llm.invoke(
            [{"role": "system", "content": prompt}, *state["messages"]]
        )
        return {"messages": [response]}

    def route_after_llm(state: State) -> str:
        """Pick the tool handler, or finish when the agent calls Done."""
        last = state["messages"][-1]
        tool_calls = getattr(last, "tool_calls", None) or []
        if not tool_calls:
            return END
        if any(call["name"] == "Done" for call in tool_calls):
            return "mark_as_read" if options.gmail else END
        return "interrupt_handler" if options.hitl else "tool_node"

    def tool_node(state: State) -> dict:
        """Execute tool calls immediately (non-HITL graphs)."""
        results = []
        for tool_call in state["messages"][-1].tool_calls:
            observation = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
            results.append(_tool_message(observation, tool_call["id"]))
        return {"messages": results}

    def interrupt_handler(state: State, store: BaseStore = None) -> Command:  # type: ignore[assignment]
        """Ask the human to review outbound actions, then continue the loop."""
        results: list[dict] = []
        goto: str = "llm_call"

        for tool_call in state["messages"][-1].tool_calls:
            name = tool_call["name"]

            if name not in options.hitl_tools:
                observation = tools_by_name[name].invoke(tool_call["args"])
                results.append(_tool_message(observation, tool_call["id"]))
                continue

            author, to, subject, thread, email_id = options.parse(state["email_input"])
            description = (
                options.markdown(subject, author, to, thread, email_id)
                + format_for_display(tool_call)
            )
            response = interrupt(
                [
                    {
                        "action_request": {"action": name, "args": tool_call["args"]},
                        "config": HITL_ACTIONS[name],
                        "description": description,
                    }
                ]
            )[0]
            response_type = response["type"]

            if response_type == "accept":
                observation = tools_by_name[name].invoke(tool_call["args"])
                results.append(_tool_message(observation, tool_call["id"]))

            elif response_type == "edit":
                edited_args = response["args"]["args"]
                ai_message = state["messages"][-1]
                current_id = tool_call["id"]
                updated_calls = [
                    call for call in ai_message.tool_calls if call["id"] != current_id
                ] + [
                    {
                        "type": "tool_call",
                        "name": name,
                        "args": edited_args,
                        "id": current_id,
                    }
                ]
                results.append(ai_message.model_copy(update={"tool_calls": updated_calls}))
                observation = tools_by_name[name].invoke(edited_args)
                results.append(_tool_message(observation, current_id))

                if name in PREFERENCE_BY_TOOL:
                    preference = PREFERENCE_BY_TOOL[name]
                    remember(
                        store,
                        preference,
                        [
                            {
                                "role": "user",
                                "content": reinforce(
                                    "User edited the generated content. Original: "
                                    f"{tool_call['args']}. Edited: {edited_args}."
                                ),
                            }
                        ],
                        DEFAULT_RESPONSE_PREFERENCES
                        if preference == RESPONSE_PREFERENCES
                        else DEFAULT_CAL_PREFERENCES,
                    )

            elif response_type == "ignore":
                results.append(
                    _tool_message(
                        "User ignored this draft. Ignore this email and end the workflow.",
                        tool_call["id"],
                    )
                )
                goto = END
                remember(
                    store,
                    TRIAGE_PREFERENCES,
                    [
                        {
                            "role": "user",
                            "content": reinforce(
                                "The user ignored the generated draft, so they did not "
                                "want to act on this email. Update the triage preferences "
                                "to reclassify similar emails."
                            ),
                        }
                    ],
                    DEFAULT_TRIAGE_INSTRUCTIONS,
                )

            elif response_type == "response":
                results.append(
                    _tool_message(
                        f"User gave feedback to incorporate: {response['args']}",
                        tool_call["id"],
                    )
                )
                if name in PREFERENCE_BY_TOOL:
                    preference = PREFERENCE_BY_TOOL[name]
                    remember(
                        store,
                        preference,
                        [
                            {
                                "role": "user",
                                "content": reinforce(
                                    f"User feedback on the draft: {response['args']}"
                                ),
                            }
                        ],
                        DEFAULT_RESPONSE_PREFERENCES
                        if preference == RESPONSE_PREFERENCES
                        else DEFAULT_CAL_PREFERENCES,
                    )

            else:
                raise ValueError(f"Invalid interrupt response: {response}")

        return Command(goto=goto, update={"messages": results})

    def mark_as_read_node(state: State) -> None:
        """Mark the processed Gmail message as read."""
        from mailroom.tools.gmail.gmail_tools import mark_as_read

        *_, email_id = options.parse(state["email_input"])
        if email_id:
            mark_as_read(email_id)

    return {
        "triage_router": triage_router,
        "triage_interrupt_handler": triage_interrupt_handler,
        "llm_call": llm_call,
        "route_after_llm": route_after_llm,
        "tool_node": tool_node,
        "interrupt_handler": interrupt_handler,
        "mark_as_read_node": mark_as_read_node,
    }


def build_workflow(options: GraphOptions | None = None) -> StateGraph:
    """Build (but do not compile) the Mailroom workflow."""
    options = options or GraphOptions()
    tools = get_tools(options.tool_names, include_gmail=options.gmail)
    tools_by_name = get_tools_by_name(tools)
    nodes = _build_nodes(options, tools, tools_by_name)

    response_agent = StateGraph(State)
    response_agent.add_node("llm_call", nodes["llm_call"])
    terminal = "interrupt_handler" if options.hitl else "tool_node"
    response_agent.add_node(terminal, nodes[terminal])
    response_agent.add_edge(START, "llm_call")

    routes: dict[str, str] = {terminal: terminal, END: END}
    if options.gmail:
        response_agent.add_node("mark_as_read", nodes["mark_as_read_node"])
        routes["mark_as_read"] = "mark_as_read"
        response_agent.add_edge("mark_as_read", END)
    response_agent.add_conditional_edges("llm_call", nodes["route_after_llm"], routes)
    if not options.hitl:
        response_agent.add_edge(terminal, "llm_call")

    workflow = StateGraph(State, input_schema=StateInput)
    workflow.add_node("triage_router", nodes["triage_router"])
    if options.hitl:
        workflow.add_node("triage_interrupt_handler", nodes["triage_interrupt_handler"])
    workflow.add_node("response_agent", response_agent.compile())
    workflow.add_edge(START, "triage_router")
    return workflow


# Graph presets exposed through langgraph.json --------------------------------
basic = build_workflow(GraphOptions()).compile()
hitl = build_workflow(GraphOptions(hitl=True)).compile()
memory = build_workflow(GraphOptions(hitl=True, memory=True)).compile()
gmail = build_workflow(GraphOptions(hitl=True, memory=True, gmail=True)).compile()

__all__ = ["GraphOptions", "basic", "build_workflow", "gmail", "hitl", "memory"]
