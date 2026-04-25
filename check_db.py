import os
import sys

# Add current dir to path to import local modules
sys.path.append(os.getcwd())

from database import get_db_connection

# Cargar env manualmente
os.environ["DATABASE_URL"] = "postgresql://whatsapp_meta_p0n8_user:e5mxf1VgYEAS1rNx4mVy3Z2q7Wuv6XOo@dpg-d6o6osrh46gs73905on0-a/whatsapp_meta_p0n8"

def check_appointments(phone):
    print(f"Buscando citas para: {phone}")
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, fecha_cita, hora_cita, estado, telefono FROM citas WHERE telefono LIKE %s OR user_id LIKE %s", (f"%{phone}%", f"%{phone}%"))
            rows = cursor.fetchall()
            print(f"Encontradas {len(rows)} citas en DB:")
            for r in rows:
                print(f" - ID: {r[0]}, Fecha: {r[1]}, Hora: {r[2]}, Estado: {r[3]}, Tel: {r[4]}")
            conn.close()
        else:
            print("No se pudo conectar a la DB.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_appointments("51511579") # Usar parte del numero para evitar problemas de formato
