import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

def check_appointments():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        telefonos = ['5491178877334', '5491166562078']
        print(f"🔍 Buscando citas para los teléfonos: {telefonos}")
        
        cursor.execute("""
            SELECT id, nombre, telefono, fecha_cita, hora_cita, propiedad_id, estado, recordatorio_enviado
            FROM citas 
            WHERE telefono IN %s
            ORDER BY fecha_cita DESC
        """, (tuple(telefonos),))
        
        rows = cursor.fetchall()
        if not rows:
            print("❌ No se encontraron citas para esos números.")
        else:
            for row in rows:
                print(f"\n📌 Cita ID: {row[0]}")
                print(f"   Nombre: {row[1]}")
                print(f"   Teléfono: {row[2]}")
                print(f"   Fecha: {row[3]}")
                print(f"   Hora: {row[4]}")
                print(f"   Propiedad: {row[5]}")
                print(f"   Estado: {row[6]}")
                print(f"   Recordatorio Enviado: {row[7]}")
                
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_appointments()
