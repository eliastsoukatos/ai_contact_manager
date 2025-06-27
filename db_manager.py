import os

import sqlite3
import requests

session = requests.Session()

try:
    import psycopg2  # type: ignore
except Exception:  # pragma: no cover - psycopg2 may not be installed
    psycopg2 = None

class DBManager:
    """Manage database connections using SQLite or PostgreSQL."""

    def __init__(self, db_name: str = "contacts.db"):
        self.pg_dsn = os.getenv("POSTGRES_DSN")
        self.use_postgres = bool(self.pg_dsn)

        if self.use_postgres:
            if psycopg2 is None:
                raise RuntimeError(
                    "psycopg2 is required for PostgreSQL support. Please install it."
                )
            self.db_path = None
        else:
            self.db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), db_name
            )

        self.conn = None
        self._table_initialized = False
        self._columns_cache = None

    def connect(self):
        """Create a connection to the configured database."""
        if self.conn is not None:
            return self.conn

        if self.use_postgres:
            self.conn = psycopg2.connect(self.pg_dsn)
        else:
            self.conn = sqlite3.connect(self.db_path)
        return self.conn

    def close(self):
        """Close the database connection if it exists."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_contacts_table(self):
        if self._table_initialized:
            return
        conn = self.connect()
        cur = conn.cursor()
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS contacts (
            profile_id TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            sid TEXT,
            list_name TEXT,
            email TEXT,
            email_quality TEXT,
            lead_source TEXT,
            education TEXT,
            personal_linkedin_url TEXT,
            company_name TEXT,
            company_alias TEXT,
            job_title TEXT,
            country TEXT,
            city TEXT,
            state TEXT,
            mobile TEXT,
            direct TEXT,
            office TEXT,
            hq TEXT,
            website TEXT,
            headcount TEXT,
            industries TEXT,
            department TEXT,
            sic TEXT,
            isic TEXT,
            naics TEXT,
            company_address_line TEXT,
            company_city TEXT,
            company_post_code_zip TEXT,
            company_county_state TEXT,
            company_country TEXT,
            company_hq_address_line TEXT,
            company_hq_city TEXT,
            company_hq_post_code_zip TEXT,
            company_hq_county_state TEXT,
            company_hq_country TEXT,
            company_linkedin_url TEXT,
            company_type TEXT,
            company_description TEXT,
            technologies TEXT,
            financials TEXT,
            company_founded_year TEXT,
            seniority TEXT,
            hiring_title_1 TEXT,
            hiring_url_1 TEXT,
            hiring_location_1 TEXT,
            hiring_date_1 TEXT,
            hiring_title_2 TEXT,
            hiring_url_2 TEXT,
            hiring_location_2 TEXT,
            hiring_date_2 TEXT,
            hiring_title_3 TEXT,
            hiring_url_3 TEXT,
            hiring_location_3 TEXT,
            hiring_date_3 TEXT,
            hiring_title_4 TEXT,
            hiring_url_4 TEXT,
            hiring_location_4 TEXT,
            hiring_date_4 TEXT,
            hiring_title_5 TEXT,
            hiring_url_5 TEXT,
            hiring_location_5 TEXT,
            hiring_date_5 TEXT,
            location_move_from_country TEXT,
            location_move_from_state TEXT,
            location_move_to_country TEXT,
            location_move_to_state TEXT,
            location_move_date TEXT,
            job_change_previous_company TEXT,
            job_change_previous_title TEXT,
            job_change_new_company TEXT,
            job_change_new_title TEXT,
            job_change_date TEXT
        );
        """
        cur.execute(create_table_sql)
        conn.commit()

        # Cache column names for later validation
        if self.use_postgres:
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name='contacts'"
            )
            self._columns_cache = {r[0] for r in cur.fetchall()}
        else:
            self._columns_cache = {
                row[1] for row in cur.execute("PRAGMA table_info(contacts)")
            }

        self._table_initialized = True

        # Parse the CREATE TABLE statement so we can add any missing columns if
        # the table already existed with only a subset of the schema (for
        # example when created by the Go backend). This ensures migrations work
        # even if the contacts table initially only contained the profile_id
        # column.
        base_columns = {}
        for line in create_table_sql.splitlines():
            line = line.strip().rstrip(',')
            if not line or line.startswith('CREATE TABLE') or line == ');':
                continue
            name, col_type = line.split(None, 1)
            base_columns[name.strip('"')] = col_type

        # Ensure additional custom columns exist
        additional_columns = {
            "target_company": "TEXT",
            "contact_icp_status": "TEXT",
            "time_zone_utc": "TEXT",
            "morning_call_time": "TEXT",
            "afternoon_call_time": "TEXT",
            "state": "TEXT",
            "contact_disposition": "TEXT",
            "clients_of_contact": "TEXT",
            "area_of_business": "TEXT",
            "most_relevant_summit": "TEXT",
            "client_icp": "TEXT",
            "company_alias": "TEXT",
            "tags": "TEXT",
            "added_timestamp": "TEXT",
            "status": "TEXT",
        }

        if self.use_postgres:
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name='contacts'"
            )
            existing_columns = {r[0] for r in cur.fetchall()}
        else:
            existing_columns = {row[1] for row in cur.execute("PRAGMA table_info(contacts)")}

        # Add any missing base columns from the CREATE TABLE statement
        for column, col_type in base_columns.items():
            if column not in existing_columns:
                col_def = col_type.replace("PRIMARY KEY", "").strip()
                if self.use_postgres:
                    cur.execute(
                        f'ALTER TABLE contacts ADD COLUMN IF NOT EXISTS "{column}" {col_def}'
                    )
                else:
                    cur.execute(
                        f"ALTER TABLE contacts ADD COLUMN {column} {col_def}"
                    )
                existing_columns.add(column)

        for column, col_type in additional_columns.items():
            if column not in existing_columns:
                if self.use_postgres:
                    cur.execute(
                        f'ALTER TABLE contacts ADD COLUMN IF NOT EXISTS "{column}" {col_type}'
                    )
                else:
                    cur.execute(
                        f"ALTER TABLE contacts ADD COLUMN {column} {col_type}"
                    )

        conn.commit()

    def insert_contact(self, data):
        """Insert a row of contact data into the database."""
        self.create_contacts_table()
        conn = self.connect()

        # Apply defaults and derive status from disposition
        from utils import disposition_to_status

        data = dict(data)
        disposition = data.get("contact_disposition") or "not_defined"
        data["contact_disposition"] = disposition
        data.setdefault("status", disposition_to_status(disposition))

        columns = list(data.keys())
        values = list(data.values())

        if self.use_postgres:
            placeholders = ", ".join(["%s" for _ in columns])
            cols_joined = ", ".join([f'"{c}"' for c in columns])
            sql = (
                f"INSERT INTO contacts ({cols_joined}) VALUES ({placeholders}) "
                "ON CONFLICT (profile_id) DO NOTHING"
            )
        else:
            placeholders = ", ".join(["?" for _ in columns])
            cols_joined = ", ".join([f'"{c}"' for c in columns])
            sql = f"INSERT OR IGNORE INTO contacts ({cols_joined}) VALUES ({placeholders})"
        conn.cursor().execute(sql, values)
        conn.commit()

    def update_contact(self, contact_id, data):
        """Update an existing contact identified by profile_id."""
        if not data:
            return
        self.create_contacts_table()
        conn = self.connect()

        cur = conn.cursor()
        if self._columns_cache is None:
            if self.use_postgres:
                cur.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='contacts'"
                )
                self._columns_cache = {r[0] for r in cur.fetchall()}
            else:
                self._columns_cache = {
                    row[1] for row in cur.execute("PRAGMA table_info(contacts)")
                }
        valid_columns = self._columns_cache
        updates = []
        params = []
        for column, value in data.items():
            if column not in valid_columns:
                raise ValueError(f"Invalid column name: {column}")
            updates.append(f'"{column}" = {"%s" if self.use_postgres else "?"}')
            params.append(value)
        if not updates:
            return

        params.append(contact_id)
        placeholder = "%s" if self.use_postgres else "?"
        sql = f"UPDATE contacts SET {', '.join(updates)} WHERE profile_id = {placeholder}"
        cur.execute(sql, params)
        conn.commit()

    def delete_contact(self, contact_id):
        """Delete a contact from the database by profile_id."""
        self.create_contacts_table()
        conn = self.connect()
        cur = conn.cursor()
        placeholder = "%s" if self.use_postgres else "?"
        cur.execute(
            f"DELETE FROM contacts WHERE profile_id = {placeholder}", (contact_id,)
        )
        conn.commit()

    def fetch_contacts(
        self,
        filters=None,
        search="",
        sort_by="",
        sort_order="asc",
        limit=None,
        offset=None,
    ):
        """Fetch contacts via the Go API backend."""

        # Ensure the contacts table exists with all expected columns before
        # delegating to the Go service. Without this the table may lack newer
        # columns when the backend created it earlier.
        self.create_contacts_table()

        payload = {
            "filters": filters or {},
            "search": search or "",
            "sort_by": sort_by or "",
            "sort_order": sort_order or "asc",
            "limit": limit or 0,
            "offset": offset or 0,
        }

        try:
            resp = session.post("http://localhost:8081/contacts", json=payload, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return data.get("contacts", [])
        except Exception:
            # Fallback to direct DB query if the service is unavailable
            self.create_contacts_table()
            conn = self.connect()
            cursor = conn.cursor()

            sql = "SELECT * FROM contacts"
            params = []
            clauses = []

            if filters:
                if self._columns_cache is None:
                    if self.use_postgres:
                        cursor.execute(
                            "SELECT column_name FROM information_schema.columns WHERE table_name='contacts'"
                        )
                        self._columns_cache = {r[0] for r in cursor.fetchall()}
                    else:
                        self._columns_cache = {
                            row[1] for row in cursor.execute("PRAGMA table_info(contacts)")
                        }
                valid_columns = self._columns_cache

                for column, value in filters.items():
                    if column not in valid_columns:
                        raise ValueError(f"Invalid column name: {column}")
                    ph = "%s" if self.use_postgres else "?"
                    values = value if isinstance(value, (list, tuple, set)) else [value]
                    if not values:
                        continue
                    if column == "tags":
                        tag_clauses = []
                        for tag in values:
                            if not tag:
                                # Use single quotes for an empty string to avoid
                                # generating an invalid identifier in SQL. This
                                # works for both SQLite and PostgreSQL.
                                tag_clauses.append("(\"tags\" = '' OR \"tags\" IS NULL)")
                                continue
                            tag_clauses.append(
                                f'(\"tags\" = {ph} OR \"tags\" LIKE {ph} OR \"tags\" LIKE {ph} OR \"tags\" LIKE {ph})'
                            )
                            params.extend([
                                tag,
                                f"{tag},%",
                                f"%,{tag}",
                                f"%,{tag},%",
                            ])
                        clauses.append("(" + " OR ".join(tag_clauses) + ")")
                    else:
                        if len(values) > 1:
                            ph_list = ",".join([ph] * len(values))
                            clauses.append(f'"{column}" IN ({ph_list})')
                            params.extend(list(values))
                        else:
                            clauses.append(f'"{column}" = {ph}')
                            params.append(values[0])

            if search:
                search_columns = [
                    "first_name",
                    "last_name",
                    "email",
                    "company_name",
                    "company_alias",
                    "job_title",
                    "mobile",
                    "tags",
                ]
                ph = "%s" if self.use_postgres else "?"
                search_clauses = []
                for col in search_columns:
                    search_clauses.append(f'"{col}" LIKE {ph}')
                    params.append(f"%{search}%")
                clauses.append("(" + " OR ".join(search_clauses) + ")")

            if clauses:
                sql += " WHERE " + " AND ".join(clauses)

            if sort_by:
                sql += f' ORDER BY "{sort_by}" {"DESC" if sort_order == "desc" else "ASC"}'

            if limit is not None and limit > 0:
                sql += " LIMIT %s" if self.use_postgres else " LIMIT ?"
                params.append(limit)
                if offset is not None and offset > 0:
                    sql += " OFFSET %s" if self.use_postgres else " OFFSET ?"
                    params.append(offset)
            elif offset is not None and offset > 0:
                if self.use_postgres:
                    sql += " OFFSET %s"
                else:
                    sql += " LIMIT -1 OFFSET ?"
                params.append(offset)

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            return [dict(zip(column_names, row)) for row in rows]

    def add_tag(self, contact_id, tag):
        """Add a tag to a contact if it does not already exist."""
        self.create_contacts_table()
        conn = self.connect()

        cur = conn.cursor()
        placeholder = "%s" if self.use_postgres else "?"
        cur.execute(
            f"SELECT tags FROM contacts WHERE profile_id = {placeholder}",
            (contact_id,),
        )
        row = cur.fetchone()
        if row is None:
            return

        existing = []
        if row[0]:
            existing = [t for t in row[0].split(',') if t]
        if tag in existing:
            return

        existing.append(tag)
        new_tags = ','.join(existing)
        cur.execute(
            f"UPDATE contacts SET tags = {placeholder} WHERE profile_id = {placeholder}",
            (new_tags, contact_id),
        )
        conn.commit()

    def remove_tag(self, contact_id, tag):
        """Remove a tag from a contact."""
        self.create_contacts_table()
        conn = self.connect()

        cur = conn.cursor()
        placeholder = "%s" if self.use_postgres else "?"
        cur.execute(
            f"SELECT tags FROM contacts WHERE profile_id = {placeholder}",
            (contact_id,),
        )
        row = cur.fetchone()
        if row is None or not row[0]:
            return

        tags = [t for t in row[0].split(',') if t]
        if tag not in tags:
            return

        tags = [t for t in tags if t != tag]
        new_tags = ','.join(tags)
        cur.execute(
            f"UPDATE contacts SET tags = {placeholder} WHERE profile_id = {placeholder}",
            (new_tags, contact_id),
        )
        conn.commit()

    def get_contacts_by_tag(self, tag):
        """Return all contacts that have the given tag."""
        self.create_contacts_table()
        conn = self.connect()
        cursor = conn.cursor()

        placeholder = "%s" if self.use_postgres else "?"
        sql = (
            f"SELECT * FROM contacts WHERE tags = {placeholder}"
            f" OR tags LIKE {placeholder} OR tags LIKE {placeholder} OR tags LIKE {placeholder}"
        )
        params = (
            tag,
            f"{tag},%",
            f"%,{tag}",
            f"%,{tag},%",
        )
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        return [dict(zip(column_names, row)) for row in rows]

    def get_distinct_values(self, column):
        """Return sorted distinct values for the given column."""
        self.create_contacts_table()
        conn = self.connect()
        cur = conn.cursor()

        if self._columns_cache is None:
            if self.use_postgres:
                cur.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='contacts'"
                )
                self._columns_cache = {r[0] for r in cur.fetchall()}
            else:
                self._columns_cache = {
                    row[1] for row in cur.execute("PRAGMA table_info(contacts)")
                }
        valid_columns = self._columns_cache

        if column not in valid_columns:
            raise ValueError(f"Invalid column name: {column}")

        cur.execute(f'SELECT DISTINCT "{column}" FROM contacts')
        values = [row[0] for row in cur.fetchall()]

        if column == "tags":
            result = set()
            blank = False
            for val in values:
                if val is None or str(val).strip() == "":
                    blank = True
                    continue
                result.update(t.strip() for t in str(val).split(',') if t.strip())
            if blank:
                result.add("")
            return sorted(result)

        return sorted(str(v) for v in values if v is not None)

    def get_columns(self) -> list[str]:
        """Return a sorted list with all column names in the contacts table."""
        self.create_contacts_table()
        if self._columns_cache is None:
            conn = self.connect()
            cur = conn.cursor()
            if self.use_postgres:
                cur.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='contacts'"
                )
                self._columns_cache = {r[0] for r in cur.fetchall()}
            else:
                self._columns_cache = {
                    row[1] for row in cur.execute("PRAGMA table_info(contacts)")
                }
        return sorted(self._columns_cache)

    def add_column(self, name: str) -> None:
        """Create a new TEXT column in the contacts table."""
        if not name:
            return
        self.create_contacts_table()
        if name in self.get_columns():
            return
        conn = self.connect()
        cur = conn.cursor()
        if self.use_postgres:
            cur.execute(f'ALTER TABLE contacts ADD COLUMN IF NOT EXISTS "{name}" TEXT')
        else:
            cur.execute(f'ALTER TABLE contacts ADD COLUMN "{name}" TEXT')
        conn.commit()
        if self._columns_cache is not None:
            self._columns_cache.add(name)

    def remove_column(self, name: str) -> None:
        """Drop a column from the contacts table."""
        if not name:
            return
        self.create_contacts_table()
        if name not in self.get_columns():
            return
        conn = self.connect()
        cur = conn.cursor()
        if self.use_postgres:
            cur.execute(f'ALTER TABLE contacts DROP COLUMN IF EXISTS "{name}"')
        else:
            cur.execute(f'ALTER TABLE contacts DROP COLUMN IF EXISTS "{name}"')
        conn.commit()
        if self._columns_cache is not None and name in self._columns_cache:
            self._columns_cache.remove(name)
