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
        # Enable foreign key support
        conn.execute("PRAGMA foreign_keys = ON")
        # Return rows as dictionaries
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database schema if it doesn't exist"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create conversations table with conversation_id field
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            employee_name TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            summary TEXT,
            topic TEXT,
            date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            conversation_id TEXT
        )
        ''')
        
        # Create topics table for faster reporting
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
        """Save a conversation to the database with conversation grouping"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # If no conversation_id provided, create one based on employee_id and timestamp
        if not conversation_id:
            conversation_id = f"{employee_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Insert the conversation
        cursor.execute('''
        INSERT INTO conversations 
        (employee_id, employee_name, question, answer, summary, topic, date_time, conversation_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (employee_id, employee_name, question, answer, summary, topic, timestamp, conversation_id))
        
        # Update topic statistics if topic is provided
        if topic:
            cursor.execute('''
            INSERT INTO topics (name, count) VALUES (?, 1)
            ON CONFLICT(name) DO UPDATE SET count = count + 1
            ''', (topic,))
        
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        
        return last_id
    
    def get_employee_conversations(self, employee_id, limit=50):
        """Get conversations for a specific employee"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM conversations
        WHERE employee_id = ?
        ORDER BY date_time DESC
        LIMIT ?
        ''', (employee_id, limit))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_all_conversations(self, limit=1000):
        """Get all conversations, with optional limit"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM conversations
        ORDER BY date_time DESC
        LIMIT ?
        ''', (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_conversation_by_id(self, conversation_id):
        """Get a specific conversation by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM conversations
        WHERE id = ?
        ''', (conversation_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return dict(result) if result else None
    
    def get_conversation_thread(self, conversation_id):
        """Get all messages in a conversation thread"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM conversations
        WHERE conversation_id = ?
        ORDER BY date_time ASC
        ''', (conversation_id,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_conversation_threads(self, limit=1000):
        """Get conversations grouped by conversation thread"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            MIN(id) as first_id,
            conversation_id,
            employee_id,
            employee_name,
            MIN(date_time) as start_time,
            MAX(date_time) as end_time,
            COUNT(*) as message_count,
            topic
        FROM conversations
        GROUP BY conversation_id
        ORDER BY start_time DESC
        LIMIT ?
        ''', (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
        
    def get_top_topics(self, limit=10):
        """Get most common conversation topics"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT name, count FROM topics
        ORDER BY count DESC
        LIMIT ?
        ''', (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_conversation_counts_by_date(self, days=30):
        """Get conversation counts by date for recent days"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            date(date_time) as day,
            COUNT(*) as count
        FROM conversations
        WHERE date_time >= date('now', ?)
        GROUP BY day
        ORDER BY day
        ''', (f'-{days} days',))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_conversation_counts_by_employee(self, limit=10):
        """Get conversation counts grouped by employee"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            employee_id,
            employee_name,
            COUNT(*) as count
        FROM conversations
        GROUP BY employee_id
        ORDER BY count DESC
        LIMIT ?
        ''', (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_thread_counts_by_employee(self, limit=10):
        """Get conversation thread counts grouped by employee"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            employee_id,
            employee_name,
            COUNT(DISTINCT conversation_id) as thread_count,
            COUNT(*) as message_count
        FROM conversations
        GROUP BY employee_id
        ORDER BY thread_count DESC
        LIMIT ?
        ''', (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def search_conversations(self, search_term, limit=50):
        """Search conversations for a specific term"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Use LIKE for simple text search
        search_pattern = f"%{search_term}%"
        
        cursor.execute('''
        SELECT * FROM conversations
        WHERE 
            question LIKE ? 
            OR answer LIKE ? 
            OR summary LIKE ? 
            OR topic LIKE ?
        ORDER BY date_time DESC
        LIMIT ?
        ''', (search_pattern, search_pattern, search_pattern, search_pattern, limit))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def export_conversations_to_csv(self, file_path, filter_employee=None):
        """Export conversations to CSV file"""
        conn = self._get_connection()
        
        # Build query based on filter
        query = "SELECT * FROM conversations"
        params = []
        
        if filter_employee:
            query += " WHERE employee_id = ?"
            params.append(filter_employee)
        
        query += " ORDER BY date_time DESC"
        
        # Load data into DataFrame
        df = pd.read_sql_query(query, conn, params=params)
        
        # Export to CSV
        df.to_csv(file_path, index=False)
        
        conn.close()
        return file_path
    
    def get_conversation_stats(self):
        """Get overall statistics about conversations"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Total conversations
        cursor.execute("SELECT COUNT(*) as total FROM conversations")
        total = cursor.fetchone()['total']
        
        # Unique employees
        cursor.execute("SELECT COUNT(DISTINCT employee_id) as unique_employees FROM conversations")
        unique_employees = cursor.fetchone()['unique_employees']
        
        # Conversations in the last 7 days
        cursor.execute(
            "SELECT COUNT(*) as recent FROM conversations WHERE date_time >= date('now', '-7 days')"
        )
        recent = cursor.fetchone()['recent']
        
        # Average answer length
        cursor.execute("SELECT AVG(length(answer)) as avg_length FROM conversations")
        avg_answer_length = cursor.fetchone()['avg_length']
        
        # Total conversation threads
        cursor.execute("SELECT COUNT(DISTINCT conversation_id) as thread_count FROM conversations")
        thread_count = cursor.fetchone()['thread_count']
        
        conn.close()
        
        return {
            "total_conversations": total,
            "unique_employees": unique_employees,
            "conversations_last_7_days": recent,
            "avg_answer_length": avg_answer_length,
            "conversation_threads": thread_count
        }
    
    def delete_conversation(self, conversation_id):
        """Delete a specific conversation (admin function)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # First get the topic to update topic counts
        cursor.execute("SELECT topic FROM conversations WHERE id = ?", (conversation_id,))
        result = cursor.fetchone()
        
        if result and result['topic']:
            # Decrement topic count
            cursor.execute(
                "UPDATE topics SET count = count - 1 WHERE name = ? AND count > 0", 
                (result['topic'],)
            )
        
        # Delete the conversation
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_affected > 0
    
    def delete_conversation_thread(self, thread_id):
        """Delete an entire conversation thread (admin function)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get all topics in the thread to update topic counts
        cursor.execute("SELECT DISTINCT topic FROM conversations WHERE conversation_id = ?", (thread_id,))
        topics = cursor.fetchall()
        
        for topic_row in topics:
            if topic_row['topic']:
                # Count how many of this topic are in the thread
                cursor.execute(
                    "SELECT COUNT(*) as count FROM conversations WHERE conversation_id = ? AND topic = ?", 
                    (thread_id, topic_row['topic'])
                )
                count = cursor.fetchone()['count']
                
                # Decrement topic count by the number found
                if count > 0:
                    cursor.execute(
                        "UPDATE topics SET count = count - ? WHERE name = ? AND count >= ?", 
                        (count, topic_row['topic'], count)
                    )
        
        # Delete all conversations in the thread
        cursor.execute("DELETE FROM conversations WHERE conversation_id = ?", (thread_id,))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_affected > 0
    
    def update_conversation_topic(self, conversation_id, new_topic):
        """Update the topic of a conversation"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # First get the old topic to update topic counts
        cursor.execute("SELECT topic FROM conversations WHERE id = ?", (conversation_id,))
        result = cursor.fetchone()
        
        if result:
            old_topic = result['topic']
            
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Decrement old topic count if it exists
            if old_topic:
                cursor.execute(
                    "UPDATE topics SET count = count - 1 WHERE name = ? AND count > 0", 
                    (old_topic,)
                )
            
            # Increment new topic count
            if new_topic:
                cursor.execute('''
                INSERT INTO topics (name, count) VALUES (?, 1)
                ON CONFLICT(name) DO UPDATE SET count = count + 1
                ''', (new_topic,))
            
            # Update the conversation
            cursor.execute(
                "UPDATE conversations SET topic = ? WHERE id = ?", 
                (new_topic, conversation_id)
            )
            
            # Commit transaction
            conn.commit()
            
            success = cursor.rowcount > 0
        else:
            success = False
        
        conn.close()
        return success