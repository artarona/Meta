import os
import psycopg2
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Configuración
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = "dante2026" # Debe coincidir con ADMIN_ACCESS_KEY en main.py
BASE_URL = "http://localhost:10000" # URL local donde corre main.py

def obtener_citas_manana():
    """Consulta la base de datos para obtener citas programadas para mañana"""
    manana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"🔍 Buscando citas para mañana: {manana}")
    
    conn = None
    citas = []
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Consultar citas pendientes para mañana
        cursor.execute("""
            SELECT id, nombre, telefono, fecha_cita, hora_cita, propiedad_id
            FROM citas
            WHERE fecha_cita = %s
            AND estado = 'pendiente'
        """, (manana,))
        
        rows = cursor.fetchall()
        for r in rows:
            citas.append({
                'id': r[0],
                'nombre': r[1],
                'telefono': r[2],
                'fecha': r[3].strftime("%d-%m-%Y"),
                'hora': r[4],
                'propiedad': r[5]
            })
            
        cursor.close()
    except Exception as e:
        print(f"❌ Error consultando base de datos: {e}")
    finally:
        if conn:
            conn.close()
    return citas

def enviar_recordatorio(cita):
    """Llama a la API interna de main.py para enviar el recordatorio"""
    url = f"{BASE_URL}/api/internal/send-reminder?key={API_KEY}"
    payload = {
        "user_id": cita['telefono'],
        "nombre": cita['nombre'],
        "fecha": cita['fecha'],
        "hora": cita['hora'],
        "propiedad": cita['propiedad']
    }
    
    try:
        print(f"📤 Enviando recordatorio a {cita['nombre']} ({cita['telefono']})...")
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Recordatorio enviado exitosamente a {cita['nombre']}")
            return True
        else:
            print(f"⚠️ Error enviando recordatorio: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error de conexión con la API: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando sistema de recordatorios automáticos...")
    citas_manana = obtener_citas_manana()
    
    if not citas_manana:
        print("📭 No hay citas pendientes para mañana.")
    else:
        print(f"📋 Se encontraron {len(citas_manana)} citas.")
        enviados = 0
        for cita in citas_manana:
            if enviar_recordatorio(cita):
                enviados += 1
        
        print(f"🏁 Proceso finalizado. Recordatorios enviados: {enviados}/{len(citas_manana)}")
