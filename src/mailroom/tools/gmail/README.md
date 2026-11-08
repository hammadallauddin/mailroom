# Gmail Integration Tools

Connect Mailroom to the Gmail and Google Calendar APIs.

## Graph

The `mailroom_gmail` preset in `src/mailroom/graph.py` is configured to use Gmail tools.
  
You simply need to run the setup below to obtain the credentials needed to run the graph with your own email.

## Setup Credentials

### 1. Set up Google Cloud Project and Enable Required APIs

#### Enable Gmail and Calendar APIs

1. Go to the [Google APIs Library and enable the Gmail API](https://developers.google.com/workspace/gmail/api/quickstart/python#enable_the_api)
2. Go to the [Google APIs Library and enable the Google Calendar API](https://developers.google.com/workspace/calendar/api/quickstart/python#enable_the_api)

#### Create OAuth Credentials

1. Authorize credentials for a desktop application [here](https://developers.google.com/workspace/gmail/api/quickstart/python#authorize_credentials_for_a_desktop_application)
2. Go to Credentials → Create Credentials → OAuth Client ID
3. Set Application Type to "Desktop app"
4. Click "Create"

> Note: If using a personal email (non-Google Workspace) select "External" under "Audience"

<img width="1496" alt="Screenshot 2025-04-26 at 7 43 57 AM" src="https://github.com/user-attachments/assets/718da39e-9b10-4a2a-905c-eda87c1c1126" />

> Then, add yourself as a test user
 
5. Save the downloaded JSON file (you'll need this in the next step)

### 2. Set Up Authentication Files

1. Move your downloaded client secret JSON file to the `.secrets` directory

```bash
# Create a secrets directory
mkdir -p src/mailroom/tools/gmail/.secrets

# Move your downloaded client secret to the secrets directory
mv /path/to/downloaded/client_secret.json src/mailroom/tools/gmail/.secrets/secrets.json
```

2. Run the Gmail setup script

```bash
# Run the Gmail setup script
python src/mailroom/tools/gmail/setup_gmail.py
```

-  This will open a browser window for you to authenticate with your Google account
-  This will create a `token.json` file in the `.secrets` directory
-  This token will be used for Gmail API access

## Use With A Local Deployment

### 1. Run the Gmail Ingestion Script with Locally Running LangGraph Server

1. Once you have authentication set up, run LangGraph server locally:

```
langgraph dev
```

2. Run the ingestion script in another terminal with desired parameters:

```bash
python src/mailroom/tools/gmail/run_ingest.py --email you@example.com --minutes-since 1000
```

- By default, this will use the local deployment URL (http://127.0.0.1:2024). The example fetches emails from the past 1000 minutes; the default window is 120 minutes.
- It will use the LangGraph SDK to pass each email to the locally running Mailroom graph.
- It will use the `mailroom_gmail` graph, which is configured to use Gmail tools.

#### Parameters:

- `--graph-name`: Name of the LangGraph to use (default: "mailroom_gmail")
- `--email`: The email address to fetch messages for (falls back to the `EMAIL_ADDRESS` environment variable)
- `--minutes-since`: Only process emails that are newer than this many minutes (default: 120)
- `--url`: URL of the LangGraph deployment (default: http://127.0.0.1:2024)
- `--early`: Stop after processing one email (default: false)
- `--include-read`: Include emails that have already been read (by default only unread emails are processed)
- `--rerun`: Accepted for CLI compatibility; it does not currently change ingestion behaviour
- `--skip-filters`: Accepted for CLI compatibility; it does not currently change ingestion behaviour

#### Troubleshooting:

- **Missing emails?** The Gmail API applies filters to show only important/primary emails by default. You can:
  - Increase the `--minutes-since` parameter to a larger value (e.g., 1000) to fetch emails from a longer time period
  - Use the `--include-read` flag to process emails marked as "read" (by default only unread emails are processed)
  - Try running with all options to process everything: `--include-read --minutes-since 1000`
  - Send yourself a test email and run with `--early` to verify the end-to-end flow

### 2. Connect to Agent Inbox

After ingestion, you can access your all interrupted threads in Agent Inbox (https://dev.agentinbox.ai/):
* Deployment URL: http://127.0.0.1:2024
* Assistant/Graph ID: `mailroom_gmail`
* Name: `Graph Name`

## Run A Hosted Deployment

### 1. Deploy to LangGraph Platform

1. Navigate to the deployments page in LangSmith
2. Click New Deployment
3. Connect it to your fork of this repository and the desired branch
4. Give it a name like `your-mailroom`
5. Add the following environment variables:
   * `GOOGLE_API_KEY` (or the key for your `MAILROOM_MODEL` provider)
   * `GMAIL_SECRET` - This is the full dictionary in `.secrets/secrets.json`
   * `GMAIL_TOKEN` - This is the full dictionary in `.secrets/token.json`
6. Click Submit
7. Get the `API URL` (https://your-mailroom-xxx.us.langgraph.app) from the deployment page

### 2. Run Ingestion with Hosted Deployment

Once your LangGraph deployment is up and running, you can test the email ingestion with:

```bash
python src/mailroom/tools/gmail/run_ingest.py --email you@example.com --minutes-since 2440 --include-read --url https://your-mailroom-xxx.us.langgraph.app
```

### 3. Connect to Agent Inbox

After ingestion, you can access your all interrupted threads in Agent Inbox (https://dev.agentinbox.ai/):
* Deployment URL: https://your-mailroom-xxx.us.langgraph.app
* Assistant/Graph ID: `mailroom_gmail`
* Name: `Graph Name`
* LangSmith API Key: `LANGSMITH_API_KEY`

### 4. Set up Cron Job

With a hosted deployment, you can set up a cron job to run the ingestion script at a specified interval.

To automate email ingestion, set up a scheduled cron job using the included setup script:

```bash
python src/mailroom/tools/gmail/setup_cron.py --email you@example.com --url https://your-mailroom-xxx.us.langgraph.app
```

#### Parameters:

- `--email`: Email address to fetch messages for (required)
- `--url`: LangGraph deployment URL (required)
- `--minutes-since`: Only fetch emails newer than this many minutes (default: 60)
- `--schedule`: Cron schedule expression (default: "*/10 * * * *" = every 10 minutes)
- `--graph-name`: Name of the graph to use (default: "mailroom_gmail")
- `--include-read`: Include emails marked as read (by default only unread emails are processed) (default: false)

#### How the Cron Works

The cron consists of two main components:

1. **`src/mailroom/cron.py`**: Defines a simple LangGraph graph that:
   - Calls the same `fetch_and_process_emails` function used by `run_ingest.py`
   - Wraps this in a simple graph so that it can be run as a hosted cron using LangGraph Platform

2. **`src/mailroom/tools/gmail/setup_cron.py`**: Creates the scheduled cron job:
   - Uses LangGraph SDK `client.crons.create` to create a cron job for the hosted `cron.py` graph

#### Managing Cron Jobs

To view, update, or delete existing cron jobs, you can use the LangGraph SDK:

```python
from langgraph_sdk import get_client

# Connect to deployment
client = get_client(url="https://your-deployment-url.us.langgraph.app")

# List all cron jobs
cron_jobs = await client.crons.list()
print(cron_jobs)

# Delete a cron job
await client.crons.delete(cron_job_id)
```

## How Gmail Ingestion Works

The ingestion script is intentionally small. It turns the CLI options into a
single Gmail search query and submits every matching message to the selected
graph:

- `--minutes-since 1440` → `after:TIMESTAMP` (emails from the last 24 hours)
- `--email you@example.com` → `to:you@example.com OR from:you@example.com`
  (emails where you are sender or recipient)
- `--include-read` → removes the default `is:unread` filter

For example, running:

```bash
python run_ingest.py --email you@example.com --minutes-since 1440 --include-read
```

creates a Gmail API search query like:

```
(to:you@example.com OR from:you@example.com) after:1745432245
```

Each message returned by that search is fetched in full, normalized, and passed
to the graph as `input={"email_input": {...}}`. `--early` stops after the first
message. `--rerun` and `--skip-filters` are accepted for CLI compatibility but
currently do not change behaviour.

## Important Gmail API Limitations

The Gmail API has several limitations that affect email ingestion:

1. **Search-Based API**: Gmail doesn't provide a direct "get all emails from timeframe" endpoint
   - All email retrieval relies on Gmail's search functionality
   - Search results can be delayed for very recent messages (indexing lag)
   - Search results might not include all messages that technically match criteria

2. **Message-Level Retrieval**:
   - The search returns message IDs, which are then fetched individually
   - The script does not currently rebuild or deduplicate full Gmail threads
   - Previously processed messages can be submitted again unless your graph
     handles idempotency