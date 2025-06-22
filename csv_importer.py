import csv
from datetime import datetime
from db_manager import DBManager

class CSVImporter:
    """Importer for Cognism CSV files."""

    def __init__(self, file_path, db_manager=None):
        self.file_path = file_path
        self.db_manager = db_manager or DBManager()

    @staticmethod
    def _map_header(header):
        """Map a Cognism header to lower_snake_case.

        Hyphens and slashes are converted to underscores so the resulting
        column names are valid in SQLite without additional quoting.
        """
        return (
            header.strip()
            .lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("-", "_")
        )

    def import_contacts(self):
        """Read the CSV and insert rows into the contacts table."""
        with open(self.file_path, newline="", encoding="utf-8") as csvfile:
            sample = csvfile.read(1024)
            csvfile.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample)
            except csv.Error:
                dialect = csv.excel
            reader = csv.reader(csvfile, dialect)
            try:
                headers = next(reader)
            except StopIteration:
                return
            mapped_headers = [self._map_header(h) for h in headers]
            for row in reader:
                if not any(cell.strip() for cell in row):
                    continue
                data = dict(zip(mapped_headers, row))
                if not data.get("added_timestamp"):
                    data["added_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.db_manager.insert_contact(data)
