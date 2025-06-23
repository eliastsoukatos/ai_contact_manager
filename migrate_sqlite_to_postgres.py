"""Migrate existing contacts.db data to PostgreSQL.

Run this script after setting POSTGRES_DSN and ensuring the contacts table
already exists in PostgreSQL. The script will not delete any SQLite data.
"""

import os
import sqlite3

from db_manager import DBManager

try:
    import psycopg2  # type: ignore
except Exception as exc:
    raise SystemExit("psycopg2 not installed. Run 'pip install psycopg2-binary' and retry") from exc

SRC_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contacts.db")
PG_DSN = os.getenv("POSTGRES_DSN")

if not PG_DSN:
    raise SystemExit(
        "POSTGRES_DSN environment variable not set. "
        "Please configure it to point to your PostgreSQL database."
    )


def migrate():
    """Copy all data from SQLite to PostgreSQL."""
    if not os.path.exists(SRC_DB):
        raise FileNotFoundError(f"SQLite database not found at {SRC_DB}")

    # Ensure the destination table exists with the full schema
    db = DBManager()
    db.create_contacts_table()

    sqlite_conn = sqlite3.connect(SRC_DB)
    try:
        pg_conn = psycopg2.connect(PG_DSN)
    except psycopg2.OperationalError as exc:
        raise SystemExit(f"Failed to connect to PostgreSQL: {exc}") from exc

    sqlite_cur = sqlite_conn.cursor()
    pg_cur = pg_conn.cursor()

    sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in sqlite_cur.fetchall()]

    for table in tables:
        sqlite_cur.execute(f'SELECT * FROM {table}')
        rows = sqlite_cur.fetchall()
        columns = [desc[0] for desc in sqlite_cur.description]
        col_list = ",".join(f'"{c}"' for c in columns)
        placeholders = ",".join(["%s"] * len(columns))
        for row in rows:
            pg_cur.execute(
                f'INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING',
                row,
            )
    pg_conn.commit()
    sqlite_conn.close()
    pg_conn.close()
    db.close()


if __name__ == "__main__":
    print("Migrating data from", SRC_DB, "to", PG_DSN)
    migrate()
    print("Migration complete. Ensure POSTGRES_DSN is set for the application.")
