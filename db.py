import sqlite3

def init_db():
    conn = sqlite3.connect('case_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_type TEXT,
            case_number TEXT,
            case_year TEXT,
            captcha_entered TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            result_html TEXT,
            FOREIGN KEY (request_id) REFERENCES requests(id)
        )
    ''')
    conn.commit()
    conn.close()
