    # 🔥 COMENTAR TEMPORALMENTE PARA PRUEBAS
    # return key == ADMIN_KEY


import os
import json
import psycopg2
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
from dotenv import load_dotenv
import pandas as pd
from io import BytesIO
import logging
import traceback
from googleapiclient.discovery import build
from google.oauth2 import service_account

# ========== CONFIGURACIÓN GOOGLE CALENDAR ==========
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'google_calendar_key.json'
CALENDAR_ID = 'primary' # O el email de la cuenta si se comparte con una personal

def get_calendar_service():
    """Obtener servicio de Google Calendar API"""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        logger.error(f"❌ Archivo de llave Google Calendar no encontrado: {SERVICE_ACCOUNT_FILE}")
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"❌ Error creando servicio Google Calendar: {e}")
        return None

# ========== CONFIGURACIÓN ==========
load_dotenv()
app = Flask(__name__)
CORS(app)

# Configuración de base de datos - RENDER.COM
def get_db_connection(max_retries=3):
    """Obtiene conexión a PostgreSQL con reintentos para manejar errores intermitentes de SSL"""
    import time
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        database_url = "postgresql://dantepropiedadesdb_user:wiBPwMvLzG01zHkHKyqEsTfHEhcZzfKi@dpg-d62aqenpm1nc73fqi3m0-a.oregon-postgres.render.com:5432/dantepropiedadesdb"
    
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(database_url, sslmode='require', connect_timeout=10)
            # Verificar si la conexión es funcional
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return conn
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            if i < max_retries - 1:
                logger.warning(f"⚠️ Error de conexión (Intento {i+1}): {e}. Reintentando...")
                time.sleep(1)
                continue
            logger.error(f"❌ Error final conectando a PostgreSQL: {e}")
            break
        except Exception as e:
            logger.error(f"❌ Error inesperado conectando a PostgreSQL: {e}")
            break
    return None

ADMIN_KEY = os.getenv('ADMIN_KEY', 'dante_admin_2024')

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validar_admin_key(key):
    """Validar clave de administrador"""
    # 🔥 COMENTAR TEMPORALMENTE PARA PRUEBAS
    # return key == ADMIN_KEY
    return True  # Siempre válido para pruebas

def log_event(telefono, accion, detalles="", propiedad_id="", propiedad_titulo=""):
    """Registrar evento en la tabla leads"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO leads (fecha, telefono, accion, detalles, propiedad_id, propiedad_titulo)
            VALUES (NOW(), %s, %s, %s, %s, %s)
        """, (telefono, accion, detalles, propiedad_id, propiedad_titulo))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Evento registrado: {telefono} - {accion}")
        return True
    except Exception as e:
        logger.error(f"Error registrando evento: {e}")
        return False

# ========== FUNCIONES DE INTEGRACIÓN CON main.py ==========

def obtener_leads_desde_json():
    """Obtener leads desde el archivo JSON del bot principal"""
    try:
        leads_file = "leads.json"
        if os.path.exists(leads_file):
            with open(leads_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Error leyendo leads JSON: {e}")
        return []

def sincronizar_leads():
    """Sincronizar leads entre JSON y PostgreSQL"""
    try:
        leads_json = obtener_leads_desde_json()
        
        if not leads_json:
            logger.info("No hay leads en JSON para sincronizar")
            return 0
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        leads_sincronizados = 0
        for lead in leads_json:
            # Verificar si ya existe
            cursor.execute("""
                SELECT id FROM leads 
                WHERE telefono = %s AND propiedad_id = %s AND accion = %s
            """, (lead.get('user_id'), lead.get('propiedad_id'), lead.get('accion')))
            
            if not cursor.fetchone():
                # Insertar nuevo
                cursor.execute("""
                    INSERT INTO leads (fecha, telefono, propiedad_id, accion, detalles)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    lead.get('timestamp'),
                    lead.get('user_id'),
                    lead.get('propiedad_id'),
                    lead.get('accion'),
                    lead.get('detalle', '')
                ))
                leads_sincronizados += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Sincronizados {leads_sincronizados} leads desde JSON")
        return leads_sincronizados
        
    except Exception as e:
        logger.error(f"Error sincronizando leads: {e}")
        return 0

def sincronizar_citas():
    """Sincronizar citas entre JSON y PostgreSQL"""
    try:
        citas_file = "citas.json"
        if not os.path.exists(citas_file):
            return 0
        
        with open(citas_file, 'r', encoding='utf-8') as f:
            citas_json = json.load(f)
        
        if not citas_json:
            return 0
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        citas_sincronizadas = 0
        for cita in citas_json:
            # Extraer el ID numérico si viene como "pg_41"
            cita_id_original = cita.get('id', '')
            cita_id_numerico = None
            
            # Si el ID empieza con "pg_", extraer el número
            if isinstance(cita_id_original, str) and cita_id_original.startswith('pg_'):
                try:
                    cita_id_numerico = int(cita_id_original.replace('pg_', ''))
                except:
                    pass
            
            # Verificar si ya existe por ID numérico o por otros campos
            if cita_id_numerico:
                cursor.execute("SELECT id FROM citas WHERE id = %s", (cita_id_numerico,))
            else:
                # Buscar por combinación de campos
                cursor.execute("""
                    SELECT id FROM citas 
                    WHERE telefono = %s AND fecha_cita = %s AND hora_cita = %s
                """, (cita.get('telefono'), cita.get('fecha'), cita.get('hora')))
            
            if not cursor.fetchone():
                # Insertar nueva cita (dejar que PostgreSQL asigne ID autoincremental)
                cursor.execute("""
                    INSERT INTO citas (
                        nombre, telefono, email, fecha_cita, hora_cita, 
                        propiedad_id, estado, notas, fecha_creacion
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    cita.get('nombre'),
                    cita.get('telefono'),
                    cita.get('email'),
                    cita.get('fecha'),
                    cita.get('hora'),
                    cita.get('propiedad_id'),
                    cita.get('estado', 'pendiente'),
                    cita.get('notas', ''),
                    cita.get('creacion', datetime.now().isoformat())
                ))
                new_id = cursor.fetchone()[0]
                logger.info(f"✅ Cita sincronizada con nuevo ID: {new_id}")
                citas_sincronizadas += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Sincronizadas {citas_sincronizadas} citas desde JSON")
        return citas_sincronizadas
        
    except Exception as e:
        logger.error(f"Error sincronizando citas: {e}")
        import traceback
        traceback.print_exc()
        return 0

# ========== RUTAS DE API (LEADS) ==========

@app.route('/api/leads', methods=['GET'])
def obtener_leads():
    """Obtener todos los leads desde PostgreSQL"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, fecha, telefono, nombre, 
                propiedad_id, propiedad_titulo, accion, detalles
            FROM leads 
            WHERE telefono IS NOT NULL 
            ORDER BY fecha DESC
        """)
        
        leads = cursor.fetchall()
        
        leads_formateados = []
        for lead in leads:
            leads_formateados.append({
                "id": lead[0],
                "timestamp": lead[1].isoformat() if lead[1] else None,
                "user_id": lead[2],
                "nombre": lead[3],
                "propiedad_id": lead[4],
                "propiedad_titulo": lead[5],
                "accion": lead[6],
                "detalle": lead[7] or f"Propiedad: {lead[5] or lead[4]}",
                "fuente": "postgresql"
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({"leads": leads_formateados, "total": len(leads_formateados)})
        
    except Exception as e:
        logger.error(f"Error obteniendo leads: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/unificados', methods=['GET'])
def obtener_leads_unificados():
    """Obtener leads desde PostgreSQL y JSON combinados"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        # 1. Obtener de PostgreSQL
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, fecha, telefono, nombre, propiedad_id, 
                   propiedad_titulo, accion, detalles
            FROM leads 
            ORDER BY fecha DESC
        """)
        
        leads_postgres = []
        for lead in cursor.fetchall():
            leads_postgres.append({
                "id": f"pg_{lead[0]}",
                "timestamp": lead[1].isoformat() if lead[1] else None,
                "user_id": lead[2],
                "nombre": lead[3],
                "propiedad_id": lead[4],
                "propiedad_titulo": lead[5],
                "accion": lead[6],
                "detalle": lead[7],
                "fuente": "postgresql"
            })
        
        cursor.close()
        conn.close()
        
        # 2. Obtener de JSON
        leads_json = obtener_leads_desde_json()
        for i, lead in enumerate(leads_json):
            lead['id'] = f"json_{i}"
            lead['fuente'] = "json"
            if 'timestamp' in lead:
                lead['timestamp'] = lead['timestamp']
        
        # 3. Combinar
        leads_combinados = leads_postgres + leads_json
        leads_combinados.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({
            "leads": leads_combinados,
            "total_postgres": len(leads_postgres),
            "total_json": len(leads_json),
            "total_combinado": len(leads_combinados)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo leads unificados: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/registrar', methods=['POST'])
def registrar_lead():
    """Registrar un nuevo lead (desde el frontend principal)"""
    try:
        data = request.json
        
        telefono = data.get('telefono')
        accion = data.get('accion', 'lead_generico')
        detalles = data.get('detalles', '')
        propiedad_id = data.get('propiedad_id', '')
        propiedad_titulo = data.get('propiedad_titulo', '')
        
        if not telefono:
            return jsonify({"error": "Teléfono requerido"}), 400
        
        success = log_event(telefono, accion, detalles, propiedad_id, propiedad_titulo)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Lead registrado correctamente",
                "telefono": telefono,
                "accion": accion
            })
        else:
            return jsonify({"error": "Error registrando lead"}), 500
            
    except Exception as e:
        logger.error(f"Error registrando lead: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/<string:lead_id>', methods=['DELETE'])
def eliminar_lead(lead_id):
    """Eliminar un lead"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        # Manejar prefijo pg_
        if lead_id.startswith('pg_'):
            internal_id = lead_id[3:]
        else:
            internal_id = lead_id

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM leads WHERE id = %s", (internal_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": f"Lead #{lead_id} eliminado"})
    except Exception as e:
        logger.error(f"Error eliminando lead: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/<string:lead_id>', methods=['PUT'])
def actualizar_lead(lead_id):
    """Actualizar datos de un lead"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        # Manejar prefijo pg_
        if lead_id.startswith('pg_'):
            internal_id = lead_id[3:]
        else:
            internal_id = lead_id

        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE leads 
            SET nombre = %s, detalles = %s
            WHERE id = %s
        """, (data.get('nombre'), data.get('detalles'), internal_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": f"Lead #{lead_id} actualizado"})
    except Exception as e:
        logger.error(f"Error actualizando lead: {e}")
        return jsonify({"error": str(e)}), 500

# ========== RUTAS DE API (CITAS) ==========

@app.route('/api/citas', methods=['GET'])
def obtener_citas():
    """Obtener todas las citas desde PostgreSQL"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, nombre, telefono, fecha_cita, hora_cita,
                propiedad_id, estado, notas, fecha_creacion, email
            FROM citas 
            ORDER BY fecha_cita DESC, hora_cita DESC
        """)
        
        citas = cursor.fetchall()
        
        citas_formateadas = []
        for cita in citas:
            citas_formateadas.append({
                "id": cita[0],
                "nombre": cita[1],
                "telefono": cita[2],
                "fecha": cita[3].strftime('%Y-%m-%d') if hasattr(cita[3], 'strftime') else cita[3],
                "hora": cita[4],
                "propiedad_id": cita[5],
                "propiedad_titulo": "Cita Inmobiliaria",
                "estado": cita[6] or "pendiente",
                "notas": cita[7],
                "fecha_creacion": cita[8].isoformat() if cita[8] else None,
                "ultima_actualizacion": cita[8].isoformat() if cita[8] else None,
                "email": cita[9]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(citas_formateadas)
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo citas: {e}")
        import traceback
        error_trace = traceback.format_exc()
        logger.error(error_trace)
        return jsonify({
            "error": str(e),
            "trace": error_trace
        }), 500

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
            # === SINCRONIZACIÓN CON JSON (Para compatibilidad con Bot) ===
            try:
                if os.path.exists("citas.json"):
                    with open("citas.json", 'r', encoding='utf-8') as f:
                        citas_json = json.load(f)
                    
                    for cita in citas_json:
                        if cita.get('id') == cita_id or cita.get('id') == f"pg_{cita_id}":
                            cita['estado'] = nuevo_estado
                            cita['ultima_actualizacion'] = datetime.now().isoformat()
                            break
                    
                    with open("citas.json", 'w', encoding='utf-8') as f:
                        json.dump(citas_json, f, indent=4, ensure_ascii=False)
                    logger.info(f"✅ Estado de cita #{cita_id} sincronizado en JSON")
            except Exception as json_e:
                logger.warning(f"⚠️ Error sincronizando estado en JSON: {json_e}")

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

@app.route('/api/propiedades', methods=['GET'])
def obtener_propiedades_metadata():
    """Obtener metadatos básicos de propiedades para buscador"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        if os.path.exists("propiedades.json"):
            with open("propiedades.json", 'r', encoding='utf-8') as f:
                propiedades = json.load(f)
            
            # Solo enviar lo necesario para el buscador para ahorrar ancho de banda
            metadata = []
            for p in propiedades:
                metadata.append({
                    "id": p.get("id_temporal"),
                    "titulo": p.get("titulo"),
                    "direccion": p.get("direccion"),
                    "tipo": p.get("tipo"),
                    "operacion": p.get("operacion")
                })
            return jsonify(metadata)
        return jsonify([])
    except Exception as e:
        logger.error(f"Error cargando propiedades: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/panel/citas/nueva', methods=['POST'])
def crear_cita(user_id, nombre, telefono, fecha, hora, propiedad_id, email=None, notas=""):
    """Crea una nueva cita y la guarda en JSON y PostgreSQL"""
    conn = None
    try:
        citas = cargar_citas()
        # Para JSON, mantener IDs legibles
        nueva_cita_json = {
            'id': f"cita_{len(citas)+1:04d}",  # Solo para JSON
            'user_id': user_id,
            'nombre': nombre,
            'email': email,
            'telefono': telefono,
            'fecha': fecha,
            'hora': hora,
            'propiedad_id': propiedad_id,
            'estado': 'pendiente',
            'notas': notas,
            'creacion': datetime.now().isoformat(),
            'ultima_actualizacion': datetime.now().isoformat()
        }
        
        citas.append(nueva_cita_json)
        
        # 1. Guardar en JSON
        if not guardar_citas(citas):
            log("⚠️ Error guardando cita en JSON", "WARNING")
        
        log(f"✅ Cita creada localmente: {nueva_cita_json['id']} para {nombre}")
        
        # 2. Guardar en PostgreSQL (SIN prefijo pg_)
        conn = get_db_connection()
        if conn:
            # Asegurar esquema antes del INSERT
            init_db(conn)
            
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO citas (
                    user_id, nombre, email, telefono, fecha_cita, hora_cita, 
                    propiedad_id, estado, notas,
                    recordatorio_enviado, recordatorio_horario
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id, nombre, email, telefono, fecha, hora, 
                propiedad_id, 'pendiente', notas,
                False, '09:00'
            ))
            
            db_record_id = cursor.fetchone()[0]
            conn.commit()
            log(f"✅ Cita guardada en PostgreSQL - ID DB: {db_record_id}")
            
            # Guardar relación entre ID de JSON y DB para futura referencia
            with open('citas_ids.json', 'a') as f:
                json.dump({
                    'json_id': nueva_cita_json['id'],
                    'db_id': db_record_id,
                    'telefono': telefono,
                    'fecha': fecha
                }, f)
                f.write('\n')
            
            # Registrar también en el log general de leads
            guardar_en_postgresql(
                telefono=telefono,
                nombre=nombre,
                accion="cita_agendada",
                detalles=f"Cita agendada para {fecha} {hora} - Propiedad ID: {propiedad_id} - Email: {email}"
            )
        else:
            log("⚠️ No se pudo conectar a PostgreSQL para guardar la cita", "WARNING")

        # 3. Notificar al admin
        notificar_cita_admin(nueva_cita_json)
        
        return nueva_cita_json
        
    except Exception as e:
        log(f"❌ Error creando cita: {e}", "ERROR")
        if conn:
            conn.rollback()
        import traceback
        log(f"🔍 Detalles error: {traceback.format_exc()}")
        return None
    finally:
        if conn:
            conn.close()

@app.route('/api/citas/<string:cita_id>', methods=['DELETE'])
def eliminar_cita(cita_id):
    """Eliminar una cita"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        # Manejar prefijo pg_
        if cita_id.startswith('pg_'):
            internal_id = cita_id[3:]
        else:
            internal_id = cita_id

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM citas WHERE id = %s", (internal_id,))
        conn.commit()
        cursor.close()
        conn.close()

        # === SINCRONIZACIÓN CON JSON (Para compatibilidad con Bot) ===
        try:
            if os.path.exists("citas.json"):
                with open("citas.json", 'r', encoding='utf-8') as f:
                    citas_json = json.load(f)
                
                # Filtrar la cita eliminada (considerando prefijos pg_ o no)
                citas_json = [c for c in citas_json if c.get('id') != cita_id and c.get('id') != f"pg_{internal_id}"]
                
                with open("citas.json", 'w', encoding='utf-8') as f:
                    json.dump(citas_json, f, indent=4, ensure_ascii=False)
                logger.info(f"✅ Cita #{cita_id} eliminada de citas.json")
        except Exception as json_e:
            logger.warning(f"⚠️ Error eliminando de JSON: {json_e}")

        return jsonify({"status": "success", "message": f"Cita #{cita_id} eliminada"})
    except Exception as e:
        logger.error(f"Error eliminando cita: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/citas/<string:cita_id>', methods=['PUT'])
def actualizar_cita(cita_id):
    """Actualizar datos de una cita"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        # Manejar prefijo pg_
        if cita_id.startswith('pg_'):
            internal_id = cita_id[3:]
        else:
            internal_id = cita_id

        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE citas 
            SET nombre = %s, email = %s, fecha_cita = %s, hora_cita = %s, notas = %s, estado = %s, modificacion = NOW()
            WHERE id = %s
        """, (data.get('nombre'), data.get('email'), data.get('fecha'), data.get('hora'), data.get('notas'), data.get('estado'), internal_id))
        conn.commit()
        cursor.close()
        conn.close()

        # === SINCRONIZACIÓN CON JSON (Para compatibilidad con Bot) ===
        try:
            if os.path.exists("citas.json"):
                with open("citas.json", 'r', encoding='utf-8') as f:
                    citas_json = json.load(f)
                
                for cita in citas_json:
                    if cita.get('id') == cita_id or cita.get('id') == f"pg_{internal_id}":
                        cita['nombre'] = data.get('nombre', cita.get('nombre'))
                        cita['email'] = data.get('email', cita.get('email'))
                        cita['fecha'] = data.get('fecha', cita.get('fecha'))
                        cita['hora'] = data.get('hora', cita.get('hora'))
                        cita['notas'] = data.get('notas', cita.get('notas'))
                        cita['estado'] = data.get('estado', cita.get('estado'))
                        cita['ultima_actualizacion'] = datetime.now().isoformat()
                        break
                
                with open("citas.json", 'w', encoding='utf-8') as f:
                    json.dump(citas_json, f, indent=4, ensure_ascii=False)
                logger.info(f"✅ Cita #{cita_id} actualizada en JSON")
        except Exception as json_e:
            logger.warning(f"⚠️ Error actualizando JSON: {json_e}")

        return jsonify({"status": "success", "message": f"Cita #{cita_id} actualizada"})
    except Exception as e:
        logger.error(f"Error actualizando cita: {e}")
        return jsonify({"error": str(e)}), 500

# ========== RUTAS DE INTEGRACIÓN Y SINCRONIZACIÓN ==========

@app.route('/api/integrar/sincronizar', methods=['POST'])
def sincronizar_datos():
    """Sincronizar datos entre JSON y PostgreSQL"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        leads_sinc = sincronizar_leads()
        citas_sinc = sincronizar_citas()
        
        return jsonify({
            "status": "success",
            "message": "Sincronización completada",
            "leads_sincronizados": leads_sinc,
            "citas_sincronizadas": citas_sinc,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/estado/sistema', methods=['GET'])
def estado_sistema():
    """Obtener estado completo del sistema"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        # Estadísticas de PostgreSQL
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM leads")
        leads_postgres = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM citas")
        citas_postgres = cursor.fetchone()[0] or 0
        
        cursor.close()
        conn.close()
        
        # Estadísticas de JSON
        leads_json = len(obtener_leads_desde_json())
        
        citas_json = 0
        citas_file = "citas.json"
        if os.path.exists(citas_file):
            with open(citas_file, 'r', encoding='utf-8') as f:
                citas_json = len(json.load(f))
        
        # Verificar archivos del bot
        archivos_bot = {
            "main.py": os.path.exists("main.py"),
            "propiedades.json": os.path.exists("propiedades.json"),
            "leads.json": os.path.exists("leads.json"),
            "citas.json": os.path.exists("citas.json")
        }
        
        return jsonify({
            "postgresql": {
                "leads": leads_postgres,
                "citas": citas_postgres,
                "estado": "activo"
            },
            "json_local": {
                "leads": leads_json,
                "citas": citas_json
            },
            "archivos_bot": archivos_bot,
            "timestamp": datetime.now().isoformat(),
            "version": "2.2"
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo estado: {e}")
        return jsonify({"error": str(e)}), 500

# ========== RUTAS DE GOOGLE CALENDAR ==========

@app.route('/api/calendar/sync/<string:cita_id>', methods=['POST'])
def sync_calendar_cita(cita_id):
    """Sincronizar una cita específica con Google Calendar"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener datos de la cita
        cursor.execute("""
            SELECT id, nombre, email, telefono, fecha_cita, hora_cita, 
                   propiedad_id, propiedad_titulo, notas, estado
            FROM citas WHERE id = %s
        """, (cita_id,))
        
        cita = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not cita:
            return jsonify({"error": "Cita no encontrada"}), 404
        
        service = get_calendar_service()
        if not service:
            return jsonify({"error": "Servicio de Google Calendar no configurado. Verifica google_calendar_key.json"}), 500
        
        # Preparar evento
        # cita: (id, nombre, email, telefono, fecha, hora, prop_id, prop_titulo, notas, estado)
        nombre = cita[1]
        fecha = str(cita[4])
        hora = cita[5]
        prop_info = cita[7] or cita[6] or "Propiedad no especificada"
        notas = cita[8] or ""
        telefono = cita[3] or "N/A"
        email_cliente = cita[2]
        
        # Combinar fecha y hora para ISO format
        # Asumiendo hora en formato HH:MM
        try:
            start_time = f"{fecha}T{hora}:00"
            # Duración estimada 1 hora
            dt_start = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
            dt_end = dt_start + timedelta(hours=1)
            end_time = dt_end.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception as e:
            logger.error(f"Error formateando fechas para calendario: {e}")
            return jsonify({"error": f"Formato de fecha/hora inválido: {fecha} {hora}"}), 400

        event = {
            'summary': f'Cita Inmobiliaria: {nombre}',
            'location': prop_info,
            'description': f'Cliente: {nombre}\nTeléfono: {telefono}\nEmail: {email_cliente}\nNotas: {notas}\nPropiedad: {prop_info}',
            'start': {
                'dateTime': start_time,
                'timeZone': 'America/Argentina/Buenos_Aires', # Ajustar según zona horaria
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'America/Argentina/Buenos_Aires',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }

        # Insertar evento
        event = service.events().insert(calendarId='primary', body=event).execute()
        
        logger.info(f"✅ Cita #{cita_id} sincronizada con Google Calendar. ID Evento: {event.get('htmlLink')}")
        
        return jsonify({
            "status": "success", 
            "message": "Sincronizado con Google Calendar",
            "link": event.get('htmlLink')
        })
        
    except Exception as e:
        logger.error(f"Error sincronizando con Google Calendar: {e}")
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
        cursor.execute("SELECT COUNT(*) FROM citas WHERE fecha_cita = %s", (hoy.strftime('%Y-%m-%d'),))
        citas_hoy = cursor.fetchone()[0]
        
        # Total leads (teléfonos únicos)
        cursor.execute("SELECT COUNT(DISTINCT telefono) FROM leads WHERE telefono IS NOT NULL")
        total_leads = cursor.fetchone()[0] or 0
        
        # Leads hoy
        cursor.execute("SELECT COUNT(DISTINCT telefono) FROM leads WHERE DATE(fecha) = %s AND telefono IS NOT NULL", (hoy,))
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

# ========== RUTAS DE EXPORTACIÓN ==========

@app.route('/api/exportar/leads', methods=['GET'])
def exportar_leads():
    """Exportar leads a Excel"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        
        conn = get_db_connection()
        
        query = """
            SELECT 
                fecha, telefono, nombre, 
                propiedad_id, propiedad_titulo, accion, detalles
            FROM leads 
            WHERE telefono IS NOT NULL 
        """
        
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
        
        # Crear archivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Leads', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'leads_dante_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        )
        
    except Exception as e:
        logger.error(f"Error exportando leads: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/exportar/citas', methods=['GET'])
def exportar_citas():
    """Exportar citas a Excel"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        desde = request.args.get('desde')
        hasta = request.args.get('hasta')
        
        conn = get_db_connection()
        
        query = """
            SELECT 
                id, nombre, email, telefono, fecha_cita as fecha, hora_cita as hora,
                propiedad_id, propiedad_titulo, estado, notas,
                fecha_creacion as creacion, modificacion
            FROM citas 
            WHERE 1=1
        """
        
        params = []
        if desde:
            query += " AND fecha_cita >= %s"
            params.append(desde)
        if hasta:
            query += " AND fecha_cita <= %s"
            params.append(hasta)
            
        query += " ORDER BY fecha_cita DESC, hora_cita DESC"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Citas', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'citas_dante_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        )
        
    except Exception as e:
        logger.error(f"Error exportando citas: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/exportar/unificados', methods=['GET'])
def exportar_unificados():
    """Exportar leads unificados a Excel"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        # Obtener datos unificados
        response = obtener_leads_unificados()
        if isinstance(response, tuple):  # Si hay error
            return response
        
        data = response.get_json()
        leads = data.get('leads', [])
        
        # Convertir a DataFrame
        df = pd.DataFrame(leads)
        
        # Crear archivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Leads_Unificados', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'leads_unificados_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
        )
        
    except Exception as e:
        logger.error(f"Error exportando unificados: {e}")
        return jsonify({"error": str(e)}), 500

# ========== RUTAS DE EJECUCIÓN MANUAL DE TAREAS ==========

@app.route('/api/admin/run-daily-tasks', methods=['POST'])
def run_daily_tasks():
    """Ejecutar las tareas diarias manualmente"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        import subprocess
        logger.info("👨‍💻 Administrador inició ejecución manual de tareas diarias")
        
        # Ejecutar el script (usamos un timeout razonable para no bloquear demasiado, 
        # aunque las tareas de envío de mensajes en cron_diario tienen sleep)
        # Si el proceso tarda más de 2 minutos puede dar timeout web, por eso se ejecuta
        # idealmente de forma asíncrona pero Render puede matar el hilo, por lo que bloqueamos o hacemos un proceso hijo simple
        
        # Ejecutar en segundo plano en Windows/Linux fire-and-forget
        if os.name == 'nt':
            # Windows
            subprocess.Popen(['python', 'cron_diario.py'], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            # Linux/Mac
            subprocess.Popen(['python', 'cron_diario.py'], preexec_fn=os.setpgrp)
            
        return jsonify({
            "status": "success", 
            "message": "Las tareas diarias (recordatorios y seguimientos) han comenzado a ejecutarse en segundo plano."
        })
    except Exception as e:
        logger.error(f"Error ejecutando tareas diarias: {e}")
        return jsonify({"error": str(e)}), 500

# ========== RUTAS DE PANEL ADMIN ==========

@app.route('/admin')
def panel_admin():
    """Panel de administración unificado"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return "Acceso no autorizado. Se requiere clave de administrador.", 401
    
    # Leer el archivo admin.html y servirlo
    try:
        with open('admin.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        # Si no existe admin.html, mostrar una versión básica
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dante Propiedades - Admin</title>
            <style>
                body { font-family: Arial; padding: 20px; }
                .card { background: #f5f5f5; padding: 20px; margin: 10px 0; border-radius: 10px; }
                a { color: #0066cc; text-decoration: none; }
                .btn { display: inline-block; background: #3b82f6; color: white; padding: 10px 20px; border-radius: 5px; margin: 5px; text-decoration: none; }
                .btn:hover { background: #2563eb; }
                .btn-sync { background: #8b5cf6; }
                .btn-sync:hover { background: #7c3aed; }
            </style>
        </head>
        <body>
            <h1>🏠 Dante Propiedades - Admin</h1>
            
            <div class="card">
                <h3>🔄 Sincronización</h3>
                <button onclick="sincronizarDatos()" class="btn btn-sync">🔄 Sincronizar con WhatsApp Bot</button>
                <div id="sync-status"></div>
            </div>
            
            <div class="card">
                <h3>📊 API Disponible:</h3>
                <ul>
                    <li><a href="/admin?key={{ key }}">Panel Principal (admin.html)</a></li>
                    <li><a href="/admin/citas?key={{ key }}">Panel de Citas (admin_citas.html)</a></li>
                    <li><a href="/api/citas?key={{ key }}">Citas API (PostgreSQL)</a></li>
                    <li><a href="/api/leads?key={{ key }}">Leads API (PostgreSQL)</a></li>
                </ul>
            </div>
            
            <script>
                function sincronizarDatos() {
                    const statusDiv = document.getElementById('sync-status');
                    statusDiv.innerHTML = '🔄 Sincronizando...';
                    
                    fetch('/api/integrar/sincronizar?key={{ key }}', {
                        method: 'POST'
                    })
                    .then(r => r.json())
                    .then(data => {
                        if (data.status === 'success') {
                            statusDiv.innerHTML = `✅ Sincronización completada<br>
                                Leads: ${data.leads_sincronizados}<br>
                                Citas: ${data.citas_sincronizadas}`;
                        } else {
                            statusDiv.innerHTML = '❌ Error: ' + (data.error || 'Error desconocido');
                        }
                    })
                    .catch(e => {
                        statusDiv.innerHTML = '❌ Error de conexión: ' + e;
                    });
                }
            </script>
        </body>
        </html>
        ''', key=key)

@app.route('/admin/citas')
def panel_admin_citas():
    """Panel de administración de citas (vista simplificada)"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return "Acceso no autorizado. Se requiere clave de administrador.", 401
    
    # Leer el archivo admin_citas.html y servirlo
    try:
        with open('admin_citas.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return "Archivo admin_citas.html no encontrado.", 404

@app.route('/')
def home():
    """Página principal"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Dante Propiedades - Sistema Unificado</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); min-height: 100vh; }
            .container { max-width: 1000px; margin: 0 auto; }
            .header { background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); margin-bottom: 30px; text-align: center; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }
            .stat-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); text-align: center; }
            .stat-number { font-size: 2.5em; font-weight: bold; color: #3b82f6; }
            .btn { display: inline-block; background: #3b82f6; color: white; padding: 12px 25px; border-radius: 8px; text-decoration: none; font-weight: bold; margin: 10px; transition: transform 0.2s; }
            .btn:hover { transform: translateY(-2px); background: #2563eb; }
            .btn-sync { background: #8b5cf6; }
            .btn-sync:hover { background: #7c3aed; }
            .btn-export { background: #10b981; }
            .btn-export:hover { background: #0da271; }
            .api-card { background: white; padding: 25px; border-radius: 10px; margin: 20px 0; }
            code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-family: 'Courier New'; }
            .sync-status { margin: 10px 0; padding: 10px; border-radius: 5px; }
            .sync-success { background: #d1fae5; color: #065f46; }
            .sync-error { background: #fee2e2; color: #991b1b; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0;">🏠 Dante Propiedades</h1>
                <p style="color: #666; margin-top: 10px;">Sistema Unificado de Gestión de Leads y Citas</p>
                
                <div style="margin: 30px 0;">
                    <a href="/admin?key=''' + ADMIN_KEY + '''" class="btn">📊 Panel Principal</a>
                    <a href="/admin/citas?key=''' + ADMIN_KEY + '''" class="btn" style="background: #10b981;">📅 Panel de Citas</a>
                    <button onclick="sincronizarDatos()" class="btn btn-sync">🔄 Sincronizar Datos</button>
                </div>
                
                <div id="sync-status" class="sync-status"></div>
                
                <div id="live-stats" class="stats-grid">
                    <!-- Estadísticas en tiempo real -->
                </div>
            </div>
            
            <div class="api-card">
                <h2>🔄 Sincronización WhatsApp Bot</h2>
                <p>El sistema integra datos del bot de WhatsApp (main.py) con PostgreSQL:</p>
                <ul>
                    <li><strong>Leads:</strong> Se sincronizan desde <code>leads.json</code></li>
                    <li><strong>Citas:</strong> Se sincronizan desde <code>citas.json</code></li>
                    <li><strong>Automatizado:</strong> Se sincroniza al iniciar el sistema</li>
                    <li><strong>Manual:</strong> Usa el botón "Sincronizar Datos" arriba</li>
                </ul>
                <p><button onclick="sincronizarDatos()" class="btn btn-sync">🔄 Ejecutar Sincronización Ahora</button></p>
            </div>
            
            <div class="api-card">
                <h2>🔧 API Endpoints</h2>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div>
                        <h3>📅 Citas</h3>
                        <p><code>GET /api/citas?key=''' + ADMIN_KEY + '''</code></p>
                        <p><code>POST /api/citas/nueva?key=''' + ADMIN_KEY + '''</code></p>
                        <p><code>PUT /api/citas/ID/estado?key=''' + ADMIN_KEY + '''</code></p>
                    </div>
                    <div>
                        <h3>👥 Leads</h3>
                        <p><code>GET /api/leads?key=''' + ADMIN_KEY + '''</code></p>
                        <p><code>GET /api/leads/unificados?key=''' + ADMIN_KEY + '''</code></p>
                        <p><code>POST /api/leads/registrar</code></p>
                    </div>
                    <div>
                        <h3>📊 Sistema</h3>
                        <p><code>GET /api/estadisticas?key=''' + ADMIN_KEY + '''</code></p>
                        <p><code>GET /api/estado/sistema?key=''' + ADMIN_KEY + '''</code></p>
                        <p><code>POST /api/integrar/sincronizar?key=''' + ADMIN_KEY + '''</code></p>
                    </div>
                    <div>
                        <h3>📤 Exportar</h3>
                        <p><code>GET /api/exportar/leads?key=''' + ADMIN_KEY + '''</code></p>
                        <p><code>GET /api/exportar/citas?key=''' + ADMIN_KEY + '''</code></p>
                        <p><code>GET /api/exportar/unificados?key=''' + ADMIN_KEY + '''</code></p>
                    </div>
                </div>
            </div>
            
            <div class="api-card">
                <h2>📋 Resumen del Sistema</h2>
                <p>Este sistema unificado maneja:</p>
                <ul>
                    <li><strong>Integración completa</strong> con el bot de WhatsApp</li>
                    <li><strong>Sincronización automática</strong> de leads y citas</li>
                    <li><strong>Almacenamiento dual</strong> (JSON + PostgreSQL)</li>
                    <li><strong>Panel administrativo</strong> con estadísticas en tiempo real</li>
                    <li><strong>Exportación a Excel</strong> de todos los datos</li>
                    <li><strong>API REST completa</strong> para integraciones</li>
                </ul>
            </div>
        </div>
        
        <script>
            // Función para sincronizar datos
            function sincronizarDatos() {
                const statusDiv = document.getElementById('sync-status');
                statusDiv.innerHTML = '🔄 Sincronizando datos del WhatsApp Bot...';
                statusDiv.className = 'sync-status';
                
                fetch('/api/integrar/sincronizar?key=''' + ADMIN_KEY + ''', {
                    method: 'POST'
                })
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'success') {
                        statusDiv.innerHTML = `<div class="sync-success">
                            ✅ Sincronización completada<br>
                            <strong>Leads:</strong> ${data.leads_sincronizados}<br>
                            <strong>Citas:</strong> ${data.citas_sincronizadas}<br>
                            <small>${new Date().toLocaleTimeString()}</small>
                        </div>`;
                        // Recargar estadísticas
                        cargarEstadisticas();
                    } else {
                        statusDiv.innerHTML = `<div class="sync-error">
                            ❌ Error: ${data.error || 'Error desconocido'}
                        </div>`;
                    }
                })
                .catch(e => {
                    statusDiv.innerHTML = `<div class="sync-error">
                        ❌ Error de conexión: ${e}
                    </div>`;
                });
            }
            
            // Cargar estadísticas en tiempo real
            function cargarEstadisticas() {
                fetch('/api/estadisticas?key=''' + ADMIN_KEY + ''')
                    .then(r => r.json())
                    .then(data => {
                        const statsHTML = `
                            <div class="stat-card">
                                <div class="stat-number">${data.total_leads || 0}</div>
                                <div>Total Leads</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${data.total_citas || 0}</div>
                                <div>Citas Activas</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${data.citas_pendientes || 0}</div>
                                <div>Citas Pendientes</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-number">${data.tasa_conversion || 0}%</div>
                                <div>Tasa Conversión</div>
                            </div>
                        `;
                        document.getElementById('live-stats').innerHTML = statsHTML;
                    })
                    .catch(e => console.error(e));
            }
            
            // Cargar al inicio y cada 30 segundos
            cargarEstadisticas();
            setInterval(cargarEstadisticas, 30000);
            
            // Sincronizar al cargar la página (opcional)
            // setTimeout(sincronizarDatos, 1000);
        </script>
    </body>
    </html>
    '''

# ========== RUTAS DE SALUD ==========

@app.route('/health', methods=['GET'])
def health_check():
    """Verificar salud del sistema"""
    try:
        # Verificar archivos del bot
        archivos_bot = {
            "propiedades.json": os.path.exists("propiedades.json"),
            "leads.json": os.path.exists("leads.json"),
            "citas.json": os.path.exists("citas.json")
        }
        
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat(),
            "version": "2.2",
            "archivos_bot": archivos_bot,
            "sistema": "Dante Propiedades Admin"
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/llave.png')
def serve_llave():
    """Servir el logo de la llave"""
    paths = ['llave.png', 'imgs/llave.png']
    for path in paths:
        if os.path.exists(path):
            return send_file(path)
    return "Logo no encontrado", 404

# ========== RUTAS DE CONFIGURACIÓN DE HORARIOS ==========

HORARIOS_FILE = "dias-horarios-visitas.json"

@app.route('/api/config/horarios', methods=['GET'])
def obtener_config_horarios():
    """Obtener configuración de horarios"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        if os.path.exists(HORARIOS_FILE):
            with open(HORARIOS_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return jsonify(config)
        else:
            # Retornar estructura por defecto si no existe
            default_config = {
                "configuracion_global": {
                    "dias_habiles": [0, 1, 2, 3, 4],
                    "horarios": [
                        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
                        "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
                        "17:00", "17:30", "18:00", "18:30"
                    ]
                },
                "propiedades": {}
            }
            return jsonify(default_config)
            
    except Exception as e:
        logger.error(f"Error obteniendo config horarios: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/config/horarios', methods=['POST'])
def guardar_config_horarios():
    """Guardar configuración de horarios"""
    key = request.args.get('key')
    if not validar_admin_key(key):
        return jsonify({"error": "Acceso no autorizado"}), 401
    
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Datos inválidos"}), 400
            
        with open(HORARIOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        logger.info("✅ Configuración de horarios actualizada")
        return jsonify({"status": "success", "message": "Configuración guardada"})
        
    except Exception as e:
        logger.error(f"Error guardando config horarios: {e}")
        return jsonify({"error": str(e)}), 500

# ========== EJECUCIÓN PRINCIPAL ==========

if __name__ == '__main__':
    # Crear tablas si no existen
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("❌ No se pudo establecer conexión con PostgreSQL. Verifica la variable DATABASE_URL.")
            exit(1)

        cursor = conn.cursor()
        
        # Crear tabla leads si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id SERIAL PRIMARY KEY,
                fecha TIMESTAMP DEFAULT NOW(),
                telefono VARCHAR(20),
                nombre VARCHAR(100),
                propiedad_id VARCHAR(50),
                propiedad_titulo VARCHAR(200),
                accion VARCHAR(50),
                detalles TEXT,
                fuente VARCHAR(20) DEFAULT 'bot'
            )
        """)
        
        # Asegurar columnas necesarias en citas
        cursor.execute("ALTER TABLE citas ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT NOW()")
        cursor.execute("ALTER TABLE citas ADD COLUMN IF NOT EXISTS modificacion TIMESTAMP DEFAULT NOW()")
        cursor.execute("ALTER TABLE citas ADD COLUMN IF NOT EXISTS fecha_cita DATE")
        cursor.execute("ALTER TABLE citas ADD COLUMN IF NOT EXISTS hora_cita VARCHAR(10)")
        cursor.execute("ALTER TABLE citas ADD COLUMN IF NOT EXISTS user_id VARCHAR(50)")
        cursor.execute("ALTER TABLE citas ADD COLUMN IF NOT EXISTS propiedad_titulo VARCHAR(200)")
        cursor.execute("ALTER TABLE citas ADD COLUMN IF NOT EXISTS notas TEXT")
        cursor.execute("ALTER TABLE citas ADD COLUMN IF NOT EXISTS estado VARCHAR(20) DEFAULT 'pendiente'")
        
        # Índices para mejor performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_telefono ON leads(telefono)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_fecha ON leads(fecha DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_citas_fecha ON citas(fecha_cita DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_citas_estado ON citas(estado)")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("✅ Base de datos verificada/creada correctamente")
        
        # Sincronizar datos existentes al iniciar
        logger.info("🔄 Sincronizando datos existentes del WhatsApp Bot...")
        leads_sinc = sincronizar_leads()
        citas_sinc = sincronizar_citas()
        logger.info(f"✅ Sincronizados {leads_sinc} leads y {citas_sinc} citas")
        
    except Exception as e:
        logger.error(f"Error inicializando DB: {e}")
    
    # Iniciar servidor
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"🚀 Iniciando Dante Propiedades Admin en puerto {port}")
    logger.info(f"🔑 Clave admin: {ADMIN_KEY}")
    logger.info(f"📊 Panel admin: http://localhost:{port}/admin?key={ADMIN_KEY}")
    logger.info(f"🔄 Sincronización: POST http://localhost:{port}/api/integrar/sincronizar?key={ADMIN_KEY}")
    logger.info(f"📊 Leads unificados: GET http://localhost:{port}/api/leads/unificados?key={ADMIN_KEY}")
    logger.info(f"📈 Estadísticas: GET http://localhost:{port}/api/estadisticas?key={ADMIN_KEY}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode,
        use_reloader=True
    )