import sqlite3
from datetime import datetime
import os
import json
import pandas as pd

class DBManager:
    """Manager class for database operations"""

    def __init__(self, db_path="data/conversation_database.db"):
        """Initialize with path to SQLite database"""
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        """Ensure the directory for the database exists"""
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)

    def _get_connection(self):
        """Get a connection to the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create base table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            employee_name TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            summary TEXT,
            topic TEXT,
            date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Add conversation_id column if missing
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [row[1] for row in cursor.fetchall()]
        if "conversation_id" not in columns:
            cursor.execute("ALTER TABLE conversations ADD COLUMN conversation_id TEXT")
            print("✅ Added missing column: conversation_id")
        else:
            print("ℹ️ conversation_id column already exists.")

        # Topics table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            count INTEGER DEFAULT 0
        )
        ''')

        conn.commit()
        conn.close()

    def save_conversation(self, employee_id, employee_name, question, answer, summary=None, topic=None, conversation_id=None):
        conn = self._get_connection()
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not conversation_id:
            conversation_id = f"{employee_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        cursor.execute('''
        INSERT INTO conversations 
        (employee_id, employee_name, question, answer, summary, topic, date_time, conversation_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (employee_id, employee_name, question, answer, summary, topic, timestamp, conversation_id))

        if topic:
            cursor.execute('''
            INSERT INTO topics (name, count) VALUES (?, 1)
            ON CONFLICT(name) DO UPDATE SET count = count + 1
            ''', (topic,))

        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    # Other methods unchanged... (get_employee_conversations, get_all_conversations, etc.)

if __name__ == "__main__":
    print("🔧 Running DBManager test setup...")
    db = DBManager()
    print(f"✅ Initialized DB at: {db.db_path}")
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(conversations)")
    columns = [row[1] for row in cursor.fetchall()]
    print("🧱 Columns in 'conversations' table:", columns)
    conn.close()
