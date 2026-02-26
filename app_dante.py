# app_dante.py
import os
import json
import psycopg2
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import pandas as pd
from io import BytesIO
import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account

# ========== CONFIGURACIÓN GOOGLE CALENDAR ==========
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'google_calendar_key.json'

def get_calendar_service():
    """Obtener servicio de Google Calendar API"""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        return None

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuración de base de datos - RENDER.COM
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://dantepropiedadesdb_user:wiBPwMvLzG01zHkHKyqEsTfHEhcZzfKi@dpg-d62aqenpm1nc73fqi3m0-a.oregon-postgres.render.com:5432/dantepropiedadesdb')

# Clave de administrador
ADMIN_KEY = os.getenv('ADMIN_KEY', 'dante_admin_2024')

def get_db_connection():
    """Obtener conexión a PostgreSQL en Render"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Error conectando a DB Render: {e}")
        raise

def validar_admin_key(key):
    """Validar clave de administrador"""
    return key == ADMIN_KEY

# ========== RUTAS DE CITAS ==========

@app.route('/api/citas', methods=['GET'])
def obtener_citas():
    """Obtener todas las citas"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener citas de TU tabla 'citas'
        cursor.execute("""
            SELECT 
                id,
                nombre,
                telefono,
                fecha,
                hora,
                propiedad_id,
                propiedad_titulo,
                COALESCE(estado, 'pendiente') as estado,
                notas,
                creacion,
                modificacion
            FROM citas
            ORDER BY fecha DESC, hora DESC
        """)
        
        citas = cursor.fetchall()
        
        # Formatear respuesta para admin.html
        citas_formateadas = []
        for cita in citas:
            citas_formateadas.append({
                "id": cita[0],
                "nombre": cita[1],
                "telefono": cita[2],
                "fecha": cita[3],  # Ya es string
                "hora": cita[4],   # Ya es string
                "propiedad_id": cita[5],
                "propiedad_titulo": cita[6],
                "estado": cita[7],
                "notas": cita[8],
                "fecha_creacion": cita[9].isoformat() if cita[9] else None,
                "ultima_actualizacion": cita[10].isoformat() if cita[10] else None
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(citas_formateadas)
        
    except Exception as e:
        logger.error(f"Error obteniendo citas: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/citas/<string:cita_id>/estado', methods=['PUT'])
def actualizar_estado_cita(cita_id):
    """Actualizar estado de una cita"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    nuevo_estado = request.args.get('estado')
    if not nuevo_estado or nuevo_estado not in ['pendiente', 'confirmada', 'completada', 'cancelada']:
        return jsonify({"error": "Estado inválido"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE citas 
            SET estado = %s, modificacion = NOW()
            WHERE id = %s
            RETURNING id, nombre, estado
        """, (nuevo_estado, cita_id))
        
        updated = cursor.fetchone()
        conn.commit()
        
        cursor.close()
        conn.close()
        
        if updated:
            return jsonify({
                "status": "success",
                "message": f"Estado de cita #{updated[0]} actualizado a {nuevo_estado}",
                "cita": {
                    "id": updated[0],
                    "nombre": updated[1],
                    "estado": updated[2]
                }
            })
        else:
            return jsonify({"error": "Cita no encontrada"}), 404
            
    except Exception as e:
        logger.error(f"Error actualizando estado: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/panel/citas/nueva', methods=['POST'])
def crear_cita():
    """Crear nueva cita desde el panel"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        data = request.json
        
        # Validar datos requeridos
        required_fields = ['nombre', 'telefono', 'fecha', 'hora']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Campo requerido: {field}"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Generar ID único
        from datetime import datetime
        cita_id = f"pg_{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}"
        
        # Insertar nueva cita en TU estructura
        cursor.execute("""
            INSERT INTO citas (
                id,
                nombre,
                telefono,
                fecha,
                hora,
                propiedad_id,
                propiedad_titulo,
                estado,
                notas,
                creacion,
                modificacion
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, (
            cita_id,
            data['nombre'],
            data['telefono'],
            data['fecha'],
            data['hora'],
            data.get('propiedad'),
            data.get('propiedad'),
            'pendiente',
            data.get('notas', '')
        ))
        
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "Cita creada exitosamente",
            "cita_id": cita_id
        })
        
    except Exception as e:
        logger.error(f"Error creando cita: {e}")
        return jsonify({"error": str(e)}), 500

# ========== RUTAS DE LEADS ==========

@app.route('/api/leads', methods=['GET'])
def obtener_leads():
    """Obtener todos los leads de TU tabla 'leads'"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener leads de TU tabla 'leads'
        cursor.execute("""
            SELECT 
                id,
                fecha,
                telefono,
                nombre,
                propiedad_id,
                propiedad_titulo,
                accion,
                detalles
            FROM leads
            WHERE telefono IS NOT NULL 
            AND telefono != ''
            ORDER BY fecha DESC
        """)
        
        leads = cursor.fetchall()
        
        # Formatear respuesta para admin.html
        leads_formateados = []
        for lead in leads:
            leads_formateados.append({
                "id": lead[0],
                "user_id": lead[2],  # telefono como user_id
                "accion": lead[6],
                "detalle": lead[7] or f"Propiedad: {lead[5] or lead[4]}",
                "timestamp": lead[1].isoformat() if lead[1] else None,
                "nombre": lead[3],
                "propiedad_id": lead[4],
                "propiedad_titulo": lead[5]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({"leads": leads_formateados, "total": len(leads_formateados)})
        
    except Exception as e:
        logger.error(f"Error obteniendo leads: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads-file', methods=['GET'])
def descargar_leads_excel():
    """Descargar leads en formato Excel"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        conn = get_db_connection()
        
        # Obtener todos los leads
        query = """
            SELECT 
                fecha,
                telefono,
                nombre,
                propiedad_id,
                propiedad_titulo,
                accion,
                detalles
            FROM leads
            WHERE telefono IS NOT NULL 
            AND telefono != ''
            ORDER BY fecha DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Crear archivo Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Leads', index=False)
        
        output.seek(0)
        
        # Enviar archivo
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'leads_dante_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
        
    except Exception as e:
        logger.error(f"Error generando Excel: {e}")
        return jsonify({"error": str(e)}), 500

# ========== RUTAS DE EXPORTACIÓN ADICIONALES ==========

@app.route('/api/exportar/leads', methods=['GET'])
def exportar_leads_v2():
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "No autorizado"}), 401
    
    try:
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        conn = get_db_connection()
        query = "SELECT fecha, telefono, nombre, propiedad_id, propiedad_titulo, accion, detalles FROM leads WHERE telefono IS NOT NULL"
        params = []
        if desde:
            query += " AND fecha >= %s"
            params.append(desde)
        if hasta:
            query += " AND fecha <= %s"
            params.append(f"{hasta} 23:59:59")
        query += " ORDER BY fecha DESC"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Leads', index=False)
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f'leads_dante_{datetime.now().strftime("%Y%m%d")}.xlsx')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/exportar/citas', methods=['GET'])
def exportar_citas_v2():
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "No autorizado"}), 401
    
    try:
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        conn = get_db_connection()
        query = "SELECT id, nombre, email, telefono, fecha, hora, propiedad_id, propiedad_titulo, estado, notas FROM citas WHERE 1=1"
        params = []
        if desde:
            query += " AND fecha >= %s"
            params.append(desde)
        if hasta:
            query += " AND fecha <= %s"
            params.append(hasta)
        query += " ORDER BY fecha DESC, hora DESC"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Citas', index=False)
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f'citas_dante_{datetime.now().strftime("%Y%m%d")}.xlsx')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========== RUTAS DE CALENDARIO ==========

@app.route('/api/calendar/sync/<string:cita_id>', methods=['POST'])
def sync_calendar_app(cita_id):
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "No autorizado"}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, email, telefono, fecha, hora, propiedad_titulo, notas FROM citas WHERE id = %s", (cita_id,))
        cita = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not cita: return jsonify({"error": "No encontrada"}), 404
        
        service = get_calendar_service()
        if not service: return jsonify({"error": "Configura google_calendar_key.json"}), 500
        
        start_time = f"{cita[4]}T{cita[5]}:00"
        dt_start = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
        end_time = (dt_start + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
        
        event = {
            'summary': f'Cita: {cita[1]}',
            'location': cita[6],
            'description': f'Tel: {cita[3]}\nEmail: {cita[2]}\nNotas: {cita[7]}',
            'start': {'dateTime': start_time, 'timeZone': 'America/Argentina/Buenos_Aires'},
            'end': {'dateTime': end_time, 'timeZone': 'America/Argentina/Buenos_Aires'},
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        return jsonify({"status": "success", "link": event.get('htmlLink')})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========== RUTAS DE ESTADÍSTICAS ==========

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """Obtener estadísticas del sistema"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        hoy = datetime.now().date()
        
        # Total citas
        cursor.execute("SELECT COUNT(*) FROM citas")
        total_citas = cursor.fetchone()[0]
        
        # Citas pendientes
        cursor.execute("SELECT COUNT(*) FROM citas WHERE estado = 'pendiente' OR estado IS NULL")
        citas_pendientes = cursor.fetchone()[0]
        
        # Citas hoy
        cursor.execute("SELECT COUNT(*) FROM citas WHERE fecha = %s", (hoy.strftime('%Y-%m-%d'),))
        citas_hoy = cursor.fetchone()[0]
        
        # Total leads (teléfonos únicos)
        cursor.execute("""
            SELECT COUNT(DISTINCT telefono) 
            FROM leads 
            WHERE telefono IS NOT NULL AND telefono != ''
        """)
        total_leads = cursor.fetchone()[0] or 0
        
        # Leads hoy
        cursor.execute("""
            SELECT COUNT(DISTINCT telefono) 
            FROM leads 
            WHERE DATE(fecha) = %s 
            AND telefono IS NOT NULL AND telefono != ''
        """, (hoy,))
        leads_hoy = cursor.fetchone()[0] or 0
        
        cursor.close()
        conn.close()
        
        # Calcular tasa de conversión
        tasa_conversion = 0
        if total_leads > 0:
            tasa_conversion = (total_citas / total_leads * 100)
        
        return jsonify({
            "total_citas": total_citas,
            "citas_pendientes": citas_pendientes,
            "citas_hoy": citas_hoy,
            "total_leads": total_leads,
            "leads_hoy": leads_hoy,
            "tasa_conversion": round(tasa_conversion, 1)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({"error": str(e)}), 500

# ========== RUTA PARA SERVIR EL PANEL ==========

@app.route('/admin')
def admin_panel():
    """Servir el panel de administración"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return "Acceso no autorizado. Se requiere clave de administrador.", 401
    
    # Servir el archivo HTML
    try:
        with open('admin.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return "Error: admin.html no encontrado", 404

@app.route('/')
def home():
    """Página principal"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dante Propiedades - Panel Admin</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { background: white; padding: 30px; border-radius: 15px; margin: 20px 0; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
            .btn { display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; }
            .btn:hover { background: #2563eb; }
            .stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-top: 20px; }
            .stat { background: #f8fafc; padding: 15px; border-radius: 10px; border-left: 4px solid #3b82f6; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏠 Dante Propiedades - Panel de Administración</h1>
            <p>Gestión completa de leads y citas</p>
            
            <div class="card">
                <h2>📊 Panel Principal</h2>
                <p>Accede al panel completo con todas las funcionalidades:</p>
                <a href="/admin?key=dante_admin_2024" class="btn" target="_blank">
                    🔗 Abrir Panel Admin
                </a>
                
                <div class="stats">
                    <div class="stat">
                        <h3>👥 Leads Totales</h3>
                        <p id="total-leads">Cargando...</p>
                    </div>
                    <div class="stat">
                        <h3>📅 Citas Activas</h3>
                        <p id="total-citas">Cargando...</p>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>🔧 Endpoints API</h2>
                <ul>
                    <li><code>GET /api/citas?key=clave</code> - Todas las citas</li>
                    <li><code>GET /api/leads?key=clave</code> - Todos los leads</li>
                    <li><code>GET /api/estadisticas?key=clave</code> - Estadísticas</li>
                    <li><code>GET /api/leads-file?key=clave</code> - Excel de leads</li>
                    <li><code>POST /api/panel/citas/nueva?key=clave</code> - Nueva cita</li>
                    <li><code>PUT /api/citas/ID/estado?estado=nuevo&key=clave</code> - Cambiar estado</li>
                </ul>
                <p><small>Clave: <code>dante_admin_2024</code></small></p>
            </div>
        </div>
        
        <script>
            // Cargar estadísticas básicas
            fetch('/api/estadisticas?key=dante_admin_2024')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('total-leads').textContent = data.total_leads || 0;
                    document.getElementById('total-citas').textContent = data.total_citas || 0;
                })
                .catch(e => console.error(e));
        </script>
    </body>
    </html>
    """

# ========== EJECUCIÓN ==========

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_ENV') == 'development'
    )