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
    

def get_recent_logs(limit=3):
    """Fetches ONLY the last N actions so we don't blow up the LLM's token limit"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Grab the newest rows first, put them in a clean dictionary
        cursor.execute("""
            SELECT timestamp, action, reasoning, status 
            FROM action_logs 
            ORDER BY id DESC LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        history = []
        for r in rows:
            history.append({
                "time": r[0],
                "action": r[1],
                "reason": r[2],
                "status": r[3]
            })
        return history