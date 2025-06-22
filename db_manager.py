import os
import sqlite3

class DBManager:
    """Simple manager for SQLite database connections."""

    def __init__(self, db_name="contacts.db"):
        # Store absolute path to the database within the project directory
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_name)
        self.conn = None

    def connect(self):
        """Create a connection to the SQLite database if not already connected."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
        return self.conn

    def close(self):
        """Close the database connection if it exists."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_contacts_table(self):
        conn = self.connect()
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS contacts (
            profile_id TEXT,
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
        conn.execute(create_table_sql)
        conn.commit()
