import database
conn = database.get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'citas'")
print([row[0] for row in cursor.fetchall()])
