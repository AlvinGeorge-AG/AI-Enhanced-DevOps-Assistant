import sqlite3

DB_NAME = "memory.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS action_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            incident TEXT,
            reasoning TEXT,
            action TEXT,
            status TEXT
        )
        """)
        conn.commit()


def save_log(incident, reasoning, action, status):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO action_logs (incident, reasoning, action, status)
        VALUES (?, ?, ?, ?)
        """, (incident, reasoning, action, status))
        conn.commit()


def get_logs():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM action_logs")
        return cursor.fetchall()