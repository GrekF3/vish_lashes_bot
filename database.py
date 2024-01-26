import sqlite3

def create_user_table(user_id):
    db_path = 'databases/master_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Создание таблицы для пользователя, если она не существует
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS user_{user_id} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            date TEXT,
            time TEXT
        )
    ''')

    conn.commit()
    conn.close()

def get_clients(user_id):
    db_path = 'databases/master_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Получение данных о клиентах конкретного пользователя
    cursor.execute(f'''
        SELECT id, name, phone, date, time FROM user_{user_id}
    ''')

    clients = [{'id': row[0], 'name': row[1], 'phone': row[2], 'date': row[3], 'time': row[4]} for row in cursor.fetchall()]

    conn.close()
    return clients

def get_client_by_id(user_id, client_id):
    db_path = 'databases/master_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Получение данных о конкретном клиенте пользователя
    cursor.execute(f'''
        SELECT id, name, phone, date, time FROM user_{user_id} WHERE id = ?
    ''', (client_id,))

    client_info = cursor.fetchone()

    conn.close()
    if client_info:
        return {'id': client_info[0], 'name': client_info[1], 'phone': client_info[2], 'date': client_info[3], 'time': client_info[4]}
    else:
        return None

def delete_client(user_id, client_id):
    db_path = 'databases/master_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Удаление клиента из таблицы пользователя
    cursor.execute(f'''
        DELETE FROM user_{user_id} WHERE id = ?
    ''', (client_id,))

    conn.commit()
    conn.close()

def add_client(user_id, data):
    db_path = 'databases/master_database.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Добавление клиента в таблицу пользователя
    cursor.execute(f'''
        INSERT INTO user_{user_id} (name, phone, date, time) VALUES (?, ?, ?, ?)
    ''', (data['name'], data['phone'], data['date'], data['time']))

    conn.commit()
    conn.close()