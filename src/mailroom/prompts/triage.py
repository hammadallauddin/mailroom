"""Triage prompts: decide whether an email should be ignored, notified or answered."""

TRIAGE_SYSTEM_PROMPT = """
< Role >
Your role is to triage incoming emails based upon instructions and background information below.
</ Role >

< Background >
{background}.
</ Background >

< Instructions >
Categorize each email into one of three categories:
1. IGNORE - Emails that are not worth responding to or tracking
2. NOTIFY - Important information that is worth notification but doesn't require a response
3. RESPOND - Emails that need a direct response
Classify the below email into one of these categories.
</ Instructions >

< Rules >
{triage_instructions}
</ Rules >
"""

TRIAGE_USER_PROMPT = """
Please determine how to handle the below email thread:

From: {author}
To: {to}
Subject: {subject}
{email_thread}"""
