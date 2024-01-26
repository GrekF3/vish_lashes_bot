import sqlite3

def get_clients():
    conn = sqlite3.connect('clients.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clients')
    clients = [{'id': row[0], 'name': row[1], 'phone': row[2], 'date': row[3], 'time': row[4]} for row in cursor.fetchall()]
    conn.close()
    return clients

def get_client_by_id(client_id):
    conn = sqlite3.connect('clients.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
    client_info = cursor.fetchone()
    conn.close()
    if client_info:
        return {'id': client_info[0], 'name': client_info[1], 'phone': client_info[2], 'date': client_info[3], 'time': client_info[4]}
    else:
        return None

def delete_client(client_id):
    conn = sqlite3.connect('clients.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    conn.commit()
    conn.close()

def add_client(data):
    conn = sqlite3.connect('clients.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO clients (name, phone, date, time) VALUES (?, ?, ?, ?)
    ''', (data['name'], data['phone'], data['date'], data['time']))
    conn.commit()
    conn.close()