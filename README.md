# VibeList

A small demo application for importing Cognism CSV files into a SQLite database and displaying them with a PyQt5 GUI. The project provides:

* **csv_importer.py** – parses a CSV file and stores the contents in the database.
* **db_manager.py** – manages the SQLite connection and schema. Contacts are
  stored with a unique `profile_id` so duplicate rows are ignored on import.
* **ui/contacts_table.py** – contains the contact table widget with inline editing, batch actions and Excel-style column filtering.
* **ui/settings_panel.py** – user interface for editing API keys, prompt templates and time zone options.
* **config/settings.py** – loads and saves persistent configuration in the user's home directory.
* **main.py** – launches the application window and wires up the components. All actions are available from a hamburger menu in the header, including a **Settings** option for configuration.

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

Use only the base model name (e.g. `"gpt-4.1"`) without any date suffixes.

The company alias field is always generated automatically during enrichment.
The application uses a fixed prompt that cannot be customized to produce a
short, conversational version of the company name when the alias field is empty.

## CSV Export

When exporting contacts to CSV, the first column contains phone numbers and is labeled `phone_number` in the header. Remaining fields use snake_case headers derived from the table columns.

## Running the Go Backend

This project includes a small Go service that performs all contact searching and filtering. The Python UI communicates with this service over HTTP.

### Quick start

1. **Install dependencies** – make sure Python 3, PyQt5 and Go are installed on your system.
2. **Build the Go service** – run `go build -o go_backend go_backend/main.go` from the project root. (The `setup_go_backend.py` script does this automatically.)
3. **Start the backend** – execute `python setup_go_backend.py` to launch the API on port `8081`.
4. **Launch the GUI** – in a new terminal run `python main.py`.
5. **Verify** – you should see the contact table populate normally. If no data appears, ensure the Go server is still running.

If you encounter issues, rebuild the Go binary and confirm nothing else is using port `8081`.
