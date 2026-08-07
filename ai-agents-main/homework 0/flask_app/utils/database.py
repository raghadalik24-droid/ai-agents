"""
database.py — manages all interactions with the SQLite database.
"""

import sqlite3
import csv
import os

# Path to the SQLite database file
DB_PATH = 'flask_app/database/resume.db'

# Tables must be created in this order because of foreign key relationships.
TABLE_ORDER = ['institutions', 'positions', 'experiences', 'skills', 'llm_roles']


class database:
    """
    Manages all interactions with the SQLite resume database.
    """

    def __init__(self):
        self.db_path = DB_PATH

    # ------------------------------------------------------------------
    # CORE QUERY FUNCTION
    # ------------------------------------------------------------------

    def query(self, sql, params=()):
        connection = sqlite3.connect(self.db_path)
        # Enable Foreign Key restrictions enforcement
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute(sql, params)

        results = []
        if sql.strip().upper().startswith(('SELECT', 'PRAGMA')):
            results = [dict(row) for row in cursor.fetchall()]

        connection.commit()
        connection.close()
        return results

    # ------------------------------------------------------------------
    # HOMEWORK 1 ADDITIONS: LLM ROLES & DYNAMIC INSERTS
    # ------------------------------------------------------------------

    def getLLMRoles(self):
        """Fetch all LLM roles/experts from the llm_roles table as a dictionary."""
        rows = self.query("SELECT * FROM llm_roles")
        return {row['role']: row for row in rows}

    def insertRows(self, table, columns, values):
        """
        Insert one row into `table`. Values starting with '(SELECT' are inlined directly.
        """
        value_sql, bound_params = [], []
        for value in values:
            if isinstance(value, str) and value.strip().startswith("(SELECT"):
                value_sql.append(value)
            else:
                value_sql.append("?")
                bound_params.append(value)
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(value_sql)})"
        self.query(sql, tuple(bound_params))

    # ------------------------------------------------------------------
    # TABLE SETUP
    # ------------------------------------------------------------------

    def createTables(self, purge=False):
        data_folder = 'flask_app/database/'

        if purge:
            for table in reversed(TABLE_ORDER):
                self.query(f"DROP TABLE IF EXISTS {table}")

        for table in TABLE_ORDER:
            self._create_table(data_folder, table)
            self._seed_table(data_folder, table)

    def _create_table(self, data_folder, table):
        sql_file = os.path.join(data_folder, 'create_tables', f'{table}.sql')
        if os.path.exists(sql_file):
            with open(sql_file) as f:
                self.query(f.read())

    def _seed_table(self, data_folder, table):
        csv_file = os.path.join(data_folder, 'initial_data', f'{table}.csv')

        if not os.path.exists(csv_file):
            return

        with open(csv_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return

        columns = list(rows[0].keys())
        placeholders = ', '.join(['?' for _ in columns])
        column_names = ', '.join(columns)
        sql = f"INSERT OR IGNORE INTO {table} ({column_names}) VALUES ({placeholders})"

        values = [
            tuple(None if cell == 'NULL' else cell for cell in row.values())
            for row in rows
        ]

        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.executemany(sql, values)
        connection.commit()
        connection.close()
        print(f"  Loaded data for table: {table}")

    # ------------------------------------------------------------------
    # RESUME DATA
    # ------------------------------------------------------------------

    def getResumeData(self):
        resume = {}

        for institution in self.query("SELECT * FROM institutions"):
            inst_id = institution['inst_id']
            resume[inst_id] = dict(institution)
            resume[inst_id]['positions'] = {}

            positions = self.query(
                "SELECT * FROM positions WHERE inst_id = ? ORDER BY start_date DESC",
                (inst_id,)
            )

            for position in positions:
                pos_id = position['position_id']
                resume[inst_id]['positions'][pos_id] = dict(position)
                resume[inst_id]['positions'][pos_id]['experiences'] = {}

                experiences = self.query(
                    "SELECT * FROM experiences WHERE position_id = ? ORDER BY start_date DESC",
                    (pos_id,)
                )

                for experience in experiences:
                    exp_id = experience['experience_id']
                    resume[inst_id]['positions'][pos_id]['experiences'][exp_id] = dict(experience)
                    resume[inst_id]['positions'][pos_id]['experiences'][exp_id]['skills'] = {}

                    skills = self.query(
                        "SELECT * FROM skills WHERE experience_id = ?",
                        (exp_id,)
                    )

                    for skill in skills:
                        skill_id = skill['skill_id']
                        resume[inst_id]['positions'][pos_id]['experiences'][exp_id]['skills'][skill_id] = dict(skill)

        self._format_dates(resume)
        return resume

    def _format_dates(self, resume):
        for institution in resume.values():
            for position in institution['positions'].values():
                position['start_date'] = self._short_date(position['start_date'])
                position['end_date'] = self._short_date(position['end_date']) or 'Present'

                for experience in position['experiences'].values():
                    experience['start_date'] = self._short_date(experience['start_date'])
                    experience['end_date'] = self._short_date(experience['end_date']) or ''

    def _short_date(self, date_string):
        if date_string:
            return str(date_string)[:7]
        return None

    def getResumeText(self):
        resume = self.getResumeData()
        lines = []

        for institution in resume.values():
            lines.append(f"\nInstitution: {institution['name']} ({institution['type']}) — {institution.get('city', '')}, {institution.get('state', '')}")

            for position in institution['positions'].values():
                lines.append(f"  Position: {position['title']} ({position['start_date']} to {position['end_date']})")
                lines.append(f"  Responsibilities: {position.get('responsibilities', '')}")

                for experience in position['experiences'].values():
                    lines.append(f"    Experience: {experience['name']} — {experience.get('description', '')}")

                    for skill in experience['skills'].values():
                        lines.append(f"      Skill: {skill['name']} (level {skill['skill_level']}/10)")

        return '\n'.join(lines)
    