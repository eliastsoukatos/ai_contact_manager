# AI Contact Manager

A small demo application for importing Cognism CSV files into a
SQLite database and displaying them with a simple PyQt5 GUI.  The
project provides:

* **csv_importer.py** – parses a CSV file and stores the contents in the
  database.
* **db_manager.py** – manages the SQLite connection and schema.
* **main.py** – minimal PyQt5 window used as a placeholder for a future
  interface.

To import contacts you can create a `CSVImporter` instance pointing to
your Cognism export and call `import_contacts()`.
