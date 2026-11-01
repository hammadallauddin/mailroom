"""Tool descriptions injected into the agent system prompt."""

STANDARD_TOOLS_PROMPT = """
1. triage_email(ignore, notify, respond) - Triage emails into one of three categories
2. write_email(to, subject, content) - Send emails to specified recipients
3. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - Schedule calendar meetings where preferred_day is a datetime object
4. check_calendar_availability(day) - Check available time slots for a given day
5. Done - E-mail has been sent
"""

AGENT_TOOLS_PROMPT = """
1. write_email(to, subject, content) - Send emails to specified recipients
2. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - Schedule calendar meetings where preferred_day is a datetime object
3. check_calendar_availability(day) - Check available time slots for a given day
4. Done - E-mail has been sent
"""

HITL_TOOLS_PROMPT = """
1. write_email(to, subject, content) - Send emails to specified recipients
2. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - Schedule calendar meetings where preferred_day is a datetime object
3. check_calendar_availability(day) - Check available time slots for a given day
4. Question(content) - Ask the user any follow-up questions
5. Done - E-mail has been sent
"""

# Memory-enabled graphs use the same tool surface as the HITL graph.
HITL_MEMORY_TOOLS_PROMPT = HITL_TOOLS_PROMPT

GMAIL_TOOLS_PROMPT = """
1. fetch_emails_tool(email_address, minutes_since) - Fetch recent emails from Gmail
2. send_email_tool(email_id, response_text, email_address, additional_recipients) - Send a reply to an email thread
3. check_calendar_tool(dates) - Check Google Calendar availability for specific dates
4. schedule_meeting_tool(attendees, title, start_time, end_time, organizer_email, timezone) - Schedule a meeting and send invites
5. triage_email(ignore, notify, respond) - Triage emails into one of three categories
6. Done - E-mail has been sent
"""

COMBINED_TOOLS_PROMPT = """
1. fetch_emails_tool(email_address, minutes_since) - Fetch recent emails from Gmail
2. send_email_tool(email_id, response_text, email_address, additional_recipients) - Send a reply to an email thread
3. check_calendar_tool(dates) - Check Google Calendar availability for specific dates
4. schedule_meeting_tool(attendees, title, start_time, end_time, organizer_email, timezone) - Schedule a meeting and send invites
5. write_email(to, subject, content) - Draft emails to specified recipients
6. triage_email(ignore, notify, respond) - Triage emails into one of three categories
7. check_calendar_availability(day) - Check available time slots for a given day
8. Done - E-mail has been sent
"""
