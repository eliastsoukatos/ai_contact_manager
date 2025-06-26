# VibeList

A small demo application for importing Cognism CSV files into a SQLite database and displaying them with a PyQt5 GUI. The project now also supports PostgreSQL for storing and querying contacts. The project provides:

* **csv_importer.py** – parses a CSV file and stores the contents in the database.
* **db_manager.py** – manages the SQLite connection and schema. Contacts are
  stored with a unique `profile_id` so duplicate rows are ignored on import.
* **ui/contacts_table.py** – contains the contact table widget with inline editing, batch actions and Excel-style column filtering.
* **ui/settings_panel.py** – user interface for editing API keys, prompt templates and time zone options.
* **config/settings.py** – loads and saves persistent configuration in the user's home directory.
* **main.py** – launches the application window and wires up the components. All actions are available from a hamburger menu in the header, including a **Settings** option for configuration.
* Supports paginated views with a configurable page size so exports only include the currently visible contacts.

Import contacts by creating a `CSVImporter` instance pointing to your CSV file and calling `import_contacts()` or using the **Import CSV** button in the GUI.

## Using OpenAI

Configure your OpenAI API key and preferred model in the **Settings** dialog. The application uses the official `openai` Python library with the following pattern:

```python
from openai import OpenAI

client = OpenAI()

completion = client.chat.completions.create(
    model="gpt-4.1",
    messages=[{"role": "user", "content": "Write a one-sentence bedtime story about a unicorn."}]
)

print(completion.choices[0].message.content)
```

Available models you can select are:

- `gpt-4.1`
- `gpt-4.1-mini`
- `gpt-4.1-nano`
- `gpt-4o-mini`
- `o3-mini`

## Using Groq

The application can also use Groq's Chat Completions API. Install the
`groq` Python package and enter your Groq API key in the **Settings** dialog.

```python
from groq import Groq

client = Groq()

chat_completion = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Explain the importance of fast language models"}],
)

print(chat_completion.choices[0].message.content)
```

Available Groq models you can select are:

- `gemma2-9b-it`
- `llama-3.1-8b-instant`
- `llama-3.3-70b-versatile`
- `meta-llama/llama-guard-4-12b`

Use only the base model name (e.g. `"gpt-4.1"`) without any date suffixes.

The company alias field is always generated automatically during enrichment.
The application uses a fixed prompt that cannot be customized to produce a
short, conversational version of the company name when the alias field is empty.

Each column filter now includes an **AI Power Up** section. Clicking **Run
Prompt** lets you apply the configured prompt template for that column to either
a specific number of contacts, all contacts in the current view or the entire
database. You can choose to override existing values or only fill missing ones.

## CSV Export

When exporting contacts to CSV, the first column contains phone numbers and is labeled `phone_number` in the header. Remaining fields use snake_case headers derived from the table columns.
Only the contacts visible on the current page are exported when pagination is enabled.

## PostgreSQL Setup

PostgreSQL is now the recommended database backend. Install PostgreSQL from
[the official downloads page](https://www.postgresql.org/download/) or using
your system package manager. After installation create a database and user:

```bash
createdb contacts_db
createuser -P contacts_user
psql -d contacts_db -c "GRANT ALL PRIVILEGES ON DATABASE contacts_db TO contacts_user"
```

Set the connection string in the `POSTGRES_DSN` environment variable, for
example:

```bash
export POSTGRES_DSN="postgresql://contacts_user:password@localhost/contacts_db"
```

Run `python migrate_sqlite_to_postgres.py` to copy existing data from the old
`contacts.db` file into PostgreSQL.

## Updating Call Times

If you change the time zone settings or notice incorrect `morning_call_time`
and `afternoon_call_time` values, run the helper script below to recalculate the
times for all contacts. The application also refreshes these fields automatically
whenever `timezone.utc_offset`, `timezone.morning_call` or `timezone.afternoon_call`
are modified:

```bash
python update_call_times.py
```

Use `--force-lookup` to look up missing UTC offsets via the configured LLM API before
recomputing the call windows.

## Running the Go Backend

This project includes a small Go service that performs all contact searching and filtering. The Python UI communicates with this service over HTTP.

### Quick start

1. **Install dependencies** – make sure Python 3, PyQt5 and Go are installed on your system.
2. **Install PostgreSQL** – ensure a local PostgreSQL instance is running and `POSTGRES_DSN` is set. The `setup_go_backend.py` script attempts to create a `contacts_db` database and `contacts_user` account if missing.
3. **Build the Go service** – run `go build -o go_backend go_backend/main.go` from the project root. (The `setup_go_backend.py` script does this automatically.)
4. **Start the backend** – execute `python setup_go_backend.py` to launch the API on port `8081`. The service now creates the `contacts` table automatically if it is missing.
5. **Launch the GUI** – in a new terminal run `python main.py`.
6. **Verify** – you should see the contact table populate normally. If no data appears, ensure the Go server is still running.

If you encounter issues, rebuild the Go binary and confirm nothing else is using port `8081`.
