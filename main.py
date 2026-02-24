# key = request.args.get('key')
    # if key != ADMIN_ACCESS_KEY:
    #     return jsonify({"error": "Unauthorized"}), 403


from flask import Flask, request, jsonify, send_from_directory, send_file
import requests
import os
import json
import re
from datetime import datetime, timedelta
from collections import deque
import threading
try:
    import psycopg2
except ImportError:
    print("❌ ERROR: No se encontró 'psycopg2'. Asegúrate de que 'psycopg2-binary' esté en requirements.txt")
    # En algunos entornos locales podría ser necesario instalarlo manualmente
    # o usar un fallback si fuera crítico, pero en Render debe venir de requirements.txt
    psycopg2 = None

from functools import lru_cache
import time



def normalizar_numero_argentina(numero):
    """Convierte número argentino al formato que espera la API de WhatsApp (sandbox)"""
    if numero and numero.startswith('549') and len(numero) == 13:
        return '54' + numero[3:]  # 5491151511579 → 5411515151579
    return numero

app = Flask(__name__)

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
# 🔥 CAMBIO IMPORTANTE: Usar variable de entorno para el token


ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN", "EAAJYsGl5pHgBQ6CHu6Ec6uTQ5kgr9ZCxINfwxeGAxjen0eTqndTv6XQZAADKLWF3liBvRLF7Y7XulIcboHL0KpmyWyJd1eGAu4Awx4HB05DgcZCuYIfZC15GsZCPBbTR9TZBVl1umkBhFzpzTXLuYbZA4R0UDLpJfPWiPX4YhSTJc5xUGIj5iEfPiGwDwZBSkUwgem1hvTth1bZCnoYolabNp6oBZBxsfHOPUpgWFcUiNkPQZCAkA6oAR6LaZBf0diODHebChumT6CXDtb9GelHpDZCkotKh988CPitcZALAZDZD")




PHONE_NUMBER_ID = "1000705633118215"
ADMIN_NUMBER = "541151511579"
LEADS_FILE = "leads.json"
# ADMIN_ACCESS_KEY = "dante2026"
ADMIN_ACCESS_KEY = os.getenv('ADMIN_KEY', 'dante2026')
CITAS_FILE = "citas.json"
HORARIOS_FILE = "dias-horarios-visitas.json"

# ========== CONFIGURACIÓN DE CITAS ==========
CITAS_DISPONIBLES = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
    "17:00", "17:30", "18:00", "18:30"
]

# ========== GESTIÓN DE ESTADO DE USUARIOS ==========
estados_usuarios = {}
processed_message_ids = deque(maxlen=1000)  # Aumentado para manejar más mensajes

# ========== CONEXIÓN A POSTGRESQL (Render) ==========
def get_db_connection():
    """Obtiene conexión a PostgreSQL forzando SSL correctamente"""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            # Fallback solo si no hay variable de entorno
            database_url = "postgresql://dantepropiedadesdb_user:wiBPwMvLzG01zHkHKyqEsTfHEhcZzfKi@dpg-d62aqenpm1nc73fqi3m0-a.oregon-postgres.render.com:5432/dantepropiedadesdb"
        
        # Forzar SSL y agregar parámetros de conexión
        conn = psycopg2.connect(
            database_url,
            sslmode='require',
            connect_timeout=10,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
            options='-c statement_timeout=30000'  # Timeout de 30 segundos
        )
        
        log("✅ Conectado a PostgreSQL con SSL correctamente")
        return conn
        
    except Exception as e:
        log(f"❌ Error conectando a PostgreSQL: {e}", "ERROR")
        
        # Intento de último recurso (solo para diagnóstico)
        try:
            log("⚠️ Intentando conexión sin SSL (solo diagnóstico)...")
            conn = psycopg2.connect(database_url, connect_timeout=5)
            log("⚠️ Conexión sin SSL exitosa (esto no debería pasar)")
            return conn
        except:
            pass
        
        return None

def analizar_hora(texto):
    """
    Parsea horarios en lenguaje natural.
    Retorna HH:MM o None.
    """
    texto = texto.lower().replace('.', ':').strip()
    
    # 1. Formatos explícitos: 10:00, 17:30
    match_hora = re.search(r'(\d{1,2})[:](\d{2})', texto)
    if match_hora:
        h, m = map(int, match_hora.groups())
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"
    
    # 2. Formatos con "hs", "h", "horas" (ej: 10hs, 10 h)
    match_hs = re.search(r'(\d{1,2})\s*(?:hs|h|hrs|horas)', texto)
    if match_hs:
        h = int(match_hs.group(1))
        if 0 <= h <= 23:
            return f"{h:02d}:00"
            
    # 3. Formatos AM/PM (ej: 5 pm, 10 am)
    match_ampm = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', texto)
    if match_ampm:
        h = int(match_ampm.group(1))
        m = int(match_ampm.group(2) or 0)
        periodo = match_ampm.group(3)
        
        if periodo == 'pm' and h < 12:
            h += 12
        if periodo == 'am' and h == 12:
            h = 0
            
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"

    # 4. Formatos informales "tipo 6", "a las 10"
    match_simple = re.search(r'(?:tipo|a las|alas)\s*(\d{1,2})', texto)
    if match_simple:
        h = int(match_simple.group(1))
        if h < 8: # Asumir PM si es muy temprano (contexto inmobiliaria)
            h += 12
        if 0 <= h <= 23:
            return f"{h:02d}:00"
    
    return None

def analizar_fecha(texto):
    """Parsea fecha en formatos naturales (hoy, mañana, lunes) o DD-MM-AAAA"""
    texto = texto.lower().strip()
    ahora = datetime.now()
    
    # 1. Fechas relativas
    if "pasado mañana" in texto or "pasado manana" in texto:
        return ahora + timedelta(days=2)
    if "mañana" in texto or "manana" in texto:
        # Asegurarse que no sea "pasado mañana" (ya cubierto arriba pero por si acaso el orden importa)
        if "pasado" not in texto:
            return ahora + timedelta(days=1)
    if "hoy" in texto:
        return ahora
    
    # 2. Días de la semana
    dias = {
        "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
        "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6
    }
    
    # Buscar nombres de días en el texto
    for nombre_dia, num_dia in dias.items():
        if nombre_dia in texto:
            target_weekday = num_dia
            days_ahead = target_weekday - ahora.weekday()
            if days_ahead <= 0: # Si ya pasó, asumimos la próxima semana
                days_ahead += 7
            return ahora + timedelta(days=days_ahead)
    
    # 3. Formatos numéricos
    # Extraer tokens que parezcan fechas
    tokens = texto.split()
    formatos = [
        "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d",
        "%d-%m-%y", "%d/%m/%y"
    ]
    
    for token in tokens:
        # Limpiar puntuación
        token_limpio = token.strip('.,')
        for fmt in formatos:
            try:
                return datetime.strptime(token_limpio, fmt)
            except ValueError:
                continue
            
    return None

def init_db(conn):
    """Inicializa y migra el esquema de la base de datos"""
    try:
        cursor = conn.cursor()
        log("🔄 Verificando esquema de base de datos...")
        
        # 0. REPARACIÓN: Detectar tablas con IDs incompatibles (ej: id de tipo texto)
        cursor.execute("""
            DO $$ 
            DECLARE 
                id_type text;
            BEGIN 
                -- Verificar citas
                SELECT data_type INTO id_type FROM information_schema.columns 
                WHERE table_name = 'citas' AND column_name = 'id';
                IF id_type IS NOT NULL AND id_type != 'integer' THEN
                    EXECUTE 'ALTER TABLE citas RENAME TO citas_old_' || to_char(now(), 'YYYYMMDD_HH24MISS');
                END IF;

                -- Verificar leads
                SELECT data_type INTO id_type FROM information_schema.columns 
                WHERE table_name = 'leads' AND column_name = 'id';
                IF id_type IS NOT NULL AND id_type != 'integer' THEN
                    EXECUTE 'ALTER TABLE leads RENAME TO leads_old_' || to_char(now(), 'YYYYMMDD_HH24MISS');
                END IF;
            END $$;
        """)
        conn.commit()

        # 1. Crear tablas si no existen (con esquema correcto)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id SERIAL PRIMARY KEY,
                fecha TIMESTAMP DEFAULT NOW(),
                telefono VARCHAR(20),
                nombre VARCHAR(100),
                accion VARCHAR(50),
                detalles TEXT
            );
            
            CREATE TABLE IF NOT EXISTS citas (
                id SERIAL PRIMARY KEY,
                fecha_creacion TIMESTAMP DEFAULT NOW(),
                user_id VARCHAR(50),
                nombre VARCHAR(100),
                email VARCHAR(100),
                telefono VARCHAR(20),
                fecha_cita DATE,
                hora_cita VARCHAR(10),
                propiedad_id VARCHAR(50),
                estado VARCHAR(20) DEFAULT 'pendiente',
                notas TEXT,
                
                -- Nuevas columnas para recordatorios
                recordatorio_enviado BOOLEAN DEFAULT FALSE,
                recordatorio_enviado_en TIMESTAMP,
                recordatorio_horario VARCHAR(5) DEFAULT '09:00',
                recordatorio_respuesta TEXT,
                recordatorio_fecha_respuesta TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_states (
                user_id VARCHAR(50) PRIMARY KEY,
                paso VARCHAR(50),
                operacion_seleccionada VARCHAR(50),
                propiedades_filtradas TEXT,
                ultimo_indice_preguntado INTEGER,
                nombre_cliente VARCHAR(100),
                email_cliente VARCHAR(100),
                fecha_cita DATE,
                hora_cita VARCHAR(10),
                horarios_disponibles TEXT,
                data TEXT,
                timestamp TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS recordatorios_log (
                id SERIAL PRIMARY KEY,
                fecha DATE,
                total INTEGER,
                exitosos INTEGER,
                fallidos INTEGER,
                detalles TEXT,
                tiempo_segundos FLOAT,
                timestamp TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # 2. Asegurar columnas adicionales
        cursor.execute("""
        ALTER TABLE leads ADD COLUMN IF NOT EXISTS propiedad_id VARCHAR(50);
        ALTER TABLE leads ADD COLUMN IF NOT EXISTS propiedad_titulo VARCHAR(200);
        
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS user_id VARCHAR(50);
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS nombre VARCHAR(100);
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS email VARCHAR(100);
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS telefono VARCHAR(20);
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS fecha_cita DATE;
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS hora_cita VARCHAR(10);
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS propiedad_id VARCHAR(50);
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS estado VARCHAR(20);
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS notas TEXT;
        
        -- Nuevas columnas para recordatorios
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS recordatorio_enviado BOOLEAN DEFAULT FALSE;
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS recordatorio_enviado_en TIMESTAMP;
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS recordatorio_horario VARCHAR(5) DEFAULT '09:00';
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS recordatorio_respuesta TEXT;
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS recordatorio_fecha_respuesta TIMESTAMP;
    """)
        
        # 3. Asegurar secuencias para tablas existentes
        cursor.execute("""
            DO $$ 
            BEGIN 
                -- Secuencias para leads
                IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'leads_id_seq') THEN
                    CREATE SEQUENCE leads_id_seq;
                    ALTER TABLE leads ALTER COLUMN id SET DEFAULT nextval('leads_id_seq');
                    ALTER SEQUENCE leads_id_seq OWNED BY leads.id;
                END IF;
                
                -- Secuencias para citas
                IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'citas_id_seq') THEN
                    CREATE SEQUENCE citas_id_seq;
                    ALTER TABLE citas ALTER COLUMN id SET DEFAULT nextval('citas_id_seq');
                    ALTER SEQUENCE citas_id_seq OWNED BY citas.id;
                END IF;

                -- Secuencias para user_states (no necesita seq porque user_id es PK)
                
                -- Sincronizar secuencias (Usamos EXECUTE para evitar errores de compilación)
                EXECUTE 'SELECT setval(''leads_id_seq'', COALESCE((SELECT MAX(id) FROM leads), 0) + 1, false)';
                EXECUTE 'SELECT setval(''citas_id_seq'', COALESCE((SELECT MAX(id) FROM citas), 0) + 1, false)';
            END $$;
        """)
        
        conn.commit()
        log("✅ Esquema de base de datos verificado y actualizado (incluye tabla user_states)")
        return True
    except Exception as e:
        log(f"❌ Error inicializando base de datos: {e}", "ERROR")
        if conn:
            conn.rollback()
        return False
    
    
    
def guardar_en_postgresql(telefono, nombre, accion, detalles=""):
    """Guardar lead/cita en PostgreSQL de Render"""
    conn = None
    try:
        log(f"🔄 Iniciando guardado en DB: Tel: {telefono}, Acción: {accion}")
        conn = get_db_connection()
        if not conn:
            return None
            
        # Asegurar esquema
        init_db(conn)
        
        cursor = conn.cursor()
        
        # Insertar en leads (log general de actividad)
        cursor.execute("""
            INSERT INTO leads (telefono, nombre, accion, detalles)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (telefono, nombre, accion, detalles))
        
        lead_id = cursor.fetchone()[0]
        conn.commit()
        
        log(f"✅ Guardado en PostgreSQL exitoso - ID: {lead_id}")
        return lead_id
        
    except Exception as e:
        log(f"❌ ERROR en guardar_en_postgresql: {e}", "ERROR")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()
    
# ========== FUNCIONES MEJORADAS CON CACHÉ ==========
@lru_cache(maxsize=128)
def cargar_propiedades_cached():
    """Carga propiedades con caché para mejor rendimiento"""
    return cargar_propiedades()

def obtener_estado_usuario(user_id):
    """Obtiene o crea el estado de un usuario (Cache + PostgreSQL)"""
    # 1. Intentar desde caché en memoria
    if user_id in estados_usuarios:
        return estados_usuarios[user_id]
        
    # 2. Intentar desde PostgreSQL
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT paso, operacion_seleccionada, propiedades_filtradas, ultimo_indice_preguntado, nombre_cliente, email_cliente, fecha_cita, hora_cita, horarios_disponibles, data FROM user_states WHERE user_id = %s", (user_id,))
            res = cursor.fetchone()
            if res:
                estado = {
                    'paso': res[0],
                    'operacion_seleccionada': res[1],
                    'propiedades_filtradas': res[2] or [],
                    'ultimo_indice_preguntado': res[3],
                    'nombre_cliente': res[4],
                    'email_cliente': res[5],
                    'fecha_cita': res[6],
                    'hora_cita': res[7],
                    'horarios_disponibles': res[8] or [],
                    'data': res[9] or {},
                    'timestamp': datetime.now().isoformat()
                }
                estados_usuarios[user_id] = estado
                return estado
    except Exception as e:
        log(f"⚠️ Error recuperando estado de DB: {e}")
    finally:
        if conn: conn.close()
        
    # 3. Si no existe, crear nuevo
    estado_nuevo = {
        'paso': 'menu_principal',
        'operacion_seleccionada': None,
        'propiedades_filtradas': [],
        'ultimo_indice_preguntado': None,
        'timestamp': datetime.now().isoformat(),
        'data': {}
    }
    estados_usuarios[user_id] = estado_nuevo
    return estado_nuevo

def actualizar_estado_usuario(user_id, nuevo_estado):
    """Actualiza el estado de un usuario en caché y PostgreSQL"""
    nuevo_estado['timestamp'] = datetime.now().isoformat()
    estados_usuarios[user_id] = nuevo_estado
    
    # Sincronizar con PostgreSQL
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_states (
                    user_id, paso, operacion_seleccionada, propiedades_filtradas, 
                    ultimo_indice_preguntado, nombre_cliente, email_cliente, 
                    fecha_cita, hora_cita, horarios_disponibles, data, timestamp
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    paso = EXCLUDED.paso,
                    operacion_seleccionada = EXCLUDED.operacion_seleccionada,
                    propiedades_filtradas = EXCLUDED.propiedades_filtradas,
                    ultimo_indice_preguntado = EXCLUDED.ultimo_indice_preguntado,
                    nombre_cliente = EXCLUDED.nombre_cliente,
                    email_cliente = EXCLUDED.email_cliente,
                    fecha_cita = EXCLUDED.fecha_cita,
                    hora_cita = EXCLUDED.hora_cita,
                    horarios_disponibles = EXCLUDED.horarios_disponibles,
                    data = EXCLUDED.data,
                    timestamp = EXCLUDED.timestamp
            """, (
                user_id, 
                nuevo_estado.get('paso'),
                nuevo_estado.get('operacion_seleccionada'),
                json.dumps(nuevo_estado.get('propiedades_filtradas', [])),
                nuevo_estado.get('ultimo_indice_preguntado'),
                nuevo_estado.get('nombre_cliente'),
                nuevo_estado.get('email_cliente'),
                nuevo_estado.get('fecha_cita'),
                nuevo_estado.get('hora_cita'),
                json.dumps(nuevo_estado.get('horarios_disponibles', [])),
                json.dumps(nuevo_estado.get('data', {})),
                nuevo_estado.get('timestamp')
            ))
            conn.commit()
    except Exception as e:
        log(f"⚠️ Error persistiendo estado en DB: {e}")
    finally:
        if conn:
            conn.close()
            
            
# ========== GESTIÓN DE LEADS MEJORADA ==========

def registrar_lead(user_id, propiedad_id, accion, detalle=""):
    """Registra una interacción de lead en archivo JSON y PostgreSQL - VERSIÓN FIX"""
    try:
        log(f"📝 INICIANDO registrar_lead: {user_id}, {propiedad_id}, {accion}")
        
        # Obtener nombre de propiedad
        nombre_propiedad = "Propiedad desconocida"
        propiedades = cargar_propiedades_cached()
        propiedad = next((p for p in propiedades if p.get('id_temporal') == propiedad_id), None)
        if propiedad:
            nombre_propiedad = propiedad.get('titulo', 'Propiedad sin título')
        
        # 1. Guardar en archivo JSON local
        leads = []
        if os.path.exists(LEADS_FILE):
            with open(LEADS_FILE, 'r', encoding='utf-8') as f:
                leads = json.load(f)
        
        nuevo_lead = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'propiedad_id': propiedad_id,
            'accion': accion,
            'detalle': detalle,
            'propiedad_nombre': nombre_propiedad
        }
        leads.append(nuevo_lead)
        
        with open(LEADS_FILE, 'w', encoding='utf-8') as f:
            json.dump(leads, f, indent=4, ensure_ascii=False)
        
        log(f"✅ Lead registrado en JSON: {user_id} - {accion}")
        
        # 2. GUARDAR EN POSTGRESQL - FIX CRÍTICO
        log("🔄 INICIANDO GUARDADO EN POSTGRESQL...")
        
        # Extraer nombre del cliente si está en el detalle
        nombre_cliente = "Cliente WhatsApp"
        if "Nombre:" in detalle:
            try:
                nombre_partes = detalle.split("Nombre:")[1].strip()
                if " - " in nombre_partes:
                    nombre_cliente = nombre_partes.split(" - ")[0]
                else:
                    nombre_cliente = nombre_partes
            except:
                nombre_cliente = "Cliente"
        
        detalles_completos = f"{detalle} | Propiedad: {nombre_propiedad} (ID: {propiedad_id})"
        
        # Llamar a guardar_en_postgresql DIRECTAMENTE
        log(f"📤 Enviando a PostgreSQL: {user_id}, {nombre_cliente}, {accion}")
        
        lead_id_pg = guardar_en_postgresql(
            telefono=user_id,
            nombre=nombre_cliente,
            accion=accion,
            detalles=detalles_completos
        )
        
        if lead_id_pg:
            log(f"✅ ✅ ✅ LEAD GUARDADO EN POSTGRESQL: ID {lead_id_pg}")
        else:
            log("⚠️ Lead NO guardado en PostgreSQL (pero sí en JSON)")
            
    except Exception as e:
        log(f"🔥 ERROR CRÍTICO en registrar_lead: {e}")
        import traceback
        log(f"🔍 TRACEBACK COMPLETO:\n{traceback.format_exc()}")
        # NO fallar completamente, solo loguear error

# ========== CARGAR PROPIEDADES CON VALIDACIÓN ==========
PROPIEDADES_FILE = "propiedades.json"

def cargar_propiedades():
    """Carga las propiedades desde el archivo JSON con validación"""
    try:
        if not os.path.exists(PROPIEDADES_FILE):
            log(f"❌ Archivo {PROPIEDADES_FILE} no encontrado")
            return []
            
        with open(PROPIEDADES_FILE, 'r', encoding='utf-8') as f:
            propiedades = json.load(f)
        
        # Validar estructura de propiedades
        propiedades_validadas = []
        for prop in propiedades:
            # Asegurar campos mínimos
            if 'id_temporal' not in prop:
                prop['id_temporal'] = f"prop_{len(propiedades_validadas)+1:04d}"
            if 'titulo' not in prop:
                prop['titulo'] = 'Propiedad sin título'
            if 'precio' not in prop:
                prop['precio'] = 0
            if 'moneda_precio' not in prop:
                prop['moneda_precio'] = 'USD'
            
            propiedades_validadas.append(prop)
        
        log(f"✅ Cargadas {len(propiedades_validadas)} propiedades desde {PROPIEDADES_FILE}")
        return propiedades_validadas
        
    except json.JSONDecodeError as e:
        log(f"❌ Error al leer JSON: {e}")
        return []
    except Exception as e:
        log(f"❌ Error inesperado cargando propiedades: {e}")
        return []

# ========== LOGGING MEJORADO ==========
def log(message, level="INFO"):
    """Función para logging con niveles"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    level_icons = {
        "INFO": "ℹ️",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "SUCCESS": "✅",
        "DEBUG": "🐛"
    }
    icon = level_icons.get(level, "📝")
    print(f"{timestamp} {icon} {message}", flush=True)

# ========== FUNCIONES PARA PROPIEDADES OPTIMIZADAS ==========
def numero_a_emoji(n):
    """Convierte un número a su emoji correspondiente"""
    emojis = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    return emojis[n] if 0 <= n <= 10 else str(n)

def filtrar_propiedades_por_operacion(operacion):
    """Filtra propiedades por tipo de operación con caché"""
    propiedades = cargar_propiedades_cached()
    if not propiedades:
        return []
    
    return [p for p in propiedades if p.get('operacion', '').lower() == operacion.lower()]

def generar_listado_propiedades(propiedades):
    """Genera un listado formateado de propiedades para WhatsApp"""
    if not propiedades:
        return "📭 No hay propiedades disponibles en este momento."
    
    listado = "📋 *LISTADO DE PROPIEDADES*\n\n"
    
    for i, prop in enumerate(propiedades[:10], 1):
        operacion = prop.get('operacion', '').upper()
        listado += f"{numero_a_emoji(i)} {prop.get('titulo', 'Sin título')} -- {operacion} --\n"
        listado += f"   📍 {prop.get('barrio', 'N/A')} | "
        
        precio = prop.get('precio', 0)
        moneda = prop.get('moneda_precio', 'USD')
        if moneda == 'USD':
            listado += f"💰 USD ${precio:,.0f}\n"
        else:
            listado += f"💰 $ {precio:,.0f} ARS\n"
        
        listado += f"   🛏️ {prop.get('ambientes', 0)} amb. | "
        listado += f"📐 {prop.get('metros_cuadrados', 0)} m²\n"
        
        if prop.get('operacion') == 'venta':
            estado = prop.get('estado', 'N/A')
            listado += f"   🏗️ Estado: {estado.capitalize()}\n"
        
        listado += "─" * 20 + "\n"
    
    if len(propiedades) > 10:
        listado += f"\n📊 ...y {len(propiedades) - 10} propiedades más.\n"
    
    listado += "\nPara ver detalles, responde con el número (ej: 1️⃣)\n"
    listado += f"{numero_a_emoji(0)} *❌ SALIR*"
    
    return listado

def formatear_detalle_propiedad(propiedad):
    """Formatea el detalle completo de una propiedad"""
    detalle = f"🏠 *{propiedad.get('titulo', 'Sin título')}*\n\n"
    
    detalle += f"📍 *Ubicación:* {propiedad.get('direccion', 'Sin dirección')}, {propiedad.get('barrio', '')}\n"
    
    precio = propiedad.get('precio', 0)
    moneda = propiedad.get('moneda_precio', 'USD')
    if moneda == 'USD':
        detalle += f"💰 *Precio:* USD ${precio:,.0f}\n"
    else:
        detalle += f"💰 *Precio:* $ {precio:,.0f} ARS\n"
    
    detalle += f"🛏️ *Ambientes:* {propiedad.get('ambientes', 0)}\n"
    detalle += f"📐 *Metros cuadrados:* {propiedad.get('metros_cuadrados', 0)} m²\n"
    detalle += f"📋 *Tipo:* {propiedad.get('tipo', '').capitalize()}\n"
    detalle += f"🏗️ *Estado:* {propiedad.get('estado', 'N/A').capitalize()}\n"
    
    expensas = propiedad.get('expensas', 0)
    if expensas > 0:
        moneda_exp = propiedad.get('moneda_expensas', 'ARS')
        if moneda_exp == 'USD':
            detalle += f"🏢 *Expensas:* USD ${expensas:,.0f}\n"
        else:
            detalle += f"🏢 *Expensas:* $ {expensas:,.0f} ARS\n"
    
    # Amenities con validación
    amenities = []
    if str(propiedad.get('cochera', 'No')).lower() in ['si', 'sí', '1', 'true', 'x']:
        amenities.append("🚗 Cochera")
    if str(propiedad.get('balcon', 'No')).lower() in ['si', 'sí', '1', 'true', 'x']:
        amenities.append("🌆 Balcón")
    if str(propiedad.get('pileta', 'No')).lower() in ['si', 'sí', '1', 'true']:
        amenities.append("🏊 Pileta")
    if str(propiedad.get('aire_acondicionado', 'No')).lower() in ['si', 'sí', '1', 'true']:
        amenities.append("❄️ Aire acondicionado")
    if str(propiedad.get('acepta_mascotas', 'No')).lower() in ['si', 'sí', '1', 'true']:
        amenities.append("🐕 Acepta mascotas")
    
    if amenities:
        detalle += "*Amenities:* " + " | ".join(amenities) + "\n"
    
    detalle += f"\n📝 *Descripción:*\n{propiedad.get('descripcion', 'Sin descripción')[:500]}...\n\n"
    detalle += "────────────────────\n"
    detalle += "📷 *FOTOS* (Escribe 'F') | 8️⃣ *ME INTERESA*\n"
    detalle += "1️⃣ *VOLVER* | 0️⃣ *❌ SALIR*"
    
    return detalle

# ========== BOT OPTIMIZADO ==========
def get_bot_response(text, user_id):
    """Responde con un mensaje simple, manteniendo estado de usuario"""
    try:
        start_time = time.time()
        text_lower = text.lower().strip()
        
        estado_usuario = obtener_estado_usuario(user_id)
        log(f"👤 Usuario {user_id}: {estado_usuario['paso']}")
        
        # 1. COMANDOS UNIVERSALES
        if text_lower in ["9", "menu", "principal", "inicio"]:
            estado_usuario.update({
                'paso': 'menu_principal',
                'operacion_seleccionada': None,
                'propiedades_filtradas': [],
                'ultimo_indice_preguntado': None,
                'timestamp': datetime.now().isoformat()
            })
            actualizar_estado_usuario(user_id, estado_usuario)
            return "WELCOME_FLOW_TRIGGER"
        
        if text_lower in ["0", "salir", "exit"]:
            estado_usuario.update({
                'paso': 'menu_principal',
                'operacion_seleccionada': None,
                'propiedades_filtradas': []
            })
            actualizar_estado_usuario(user_id, estado_usuario)
            return "Gracias por contactarte con Dante Propiedades. ¡Que tengas un excelente día! 🏠🗝️"

        # Comandos de compatibilidad
        if text_lower in ["hola", "hi", "hello", "volver", "atras"]:
            estado_usuario.update({
                'paso': 'menu_principal',
                'operacion_seleccionada': None,
                'propiedades_filtradas': [],
                'ultimo_indice_preguntado': None,
                'timestamp': datetime.now().isoformat()
            })
            actualizar_estado_usuario(user_id, estado_usuario)
            return "WELCOME_FLOW_TRIGGER"
        
        # 2. ACCIONES ESPECIALES
        if text_lower == "8":
            indice = estado_usuario.get('ultimo_indice_preguntado')
            propiedades = estado_usuario.get('propiedades_filtradas', [])
            
            if indice and 1 <= indice <= len(propiedades):
                propiedad = propiedades[indice - 1]
                log(f"🎯 ACCIÓN: Me interesa (Prop ID: {propiedad.get('id_temporal')})")
                estado_usuario['paso'] = 'esperando_nombre_lead'
                actualizar_estado_usuario(user_id, estado_usuario)
                
                # REGISTRAR LEAD INMEDIATAMENTE - FIX PostgreSQL
                try:
                    registrar_lead(user_id, propiedad.get('id_temporal'), 'click_me_interesa', f"Interés expresado en Propiedad: {propiedad.get('titulo')}")
                except Exception as e:
                    log(f"⚠️ Error registrando lead inicial: {e}")
                    
                return f"✅ ¡Genial! Me interesa la propiedad: *{propiedad.get('titulo')}*.\n\nPor favor, decime tu *Nombre y Apellido* para que un asesor te contacte."
            else:
                return "⚠️ Por favor, primero selecciona una propiedad del listado."

        if text_lower == "f":
            indice = estado_usuario.get('ultimo_indice_preguntado')
            propiedades = estado_usuario.get('propiedades_filtradas', [])
            if indice and 1 <= indice <= len(propiedades):
                propiedad = propiedades[indice - 1]
                return f"PHOTOS_TRIGGER|{propiedad.get('id_temporal')}"
            else:
                return "⚠️ Por favor, primero selecciona una propiedad del listado para ver las fotos."
        
        # 3. LÓGICA POR ESTADO
        paso = estado_usuario['paso']
        
        if paso == 'submenu_consultar':
            return manejar_submenu_consultar(text_lower, estado_usuario, user_id)
            
        elif paso == 'submenu_visita':
            return manejar_submenu_visita(text_lower, estado_usuario, user_id)
            
        elif paso == 'submenu_asesor':
            return manejar_submenu_asesor(text_lower, estado_usuario, user_id)

        elif paso == 'listado_propiedades':
            return manejar_listado_propiedades(text_lower, estado_usuario, user_id)
        
        elif paso == 'detalle_propiedad':
            return manejar_detalle_propiedad(text_lower, estado_usuario, user_id)
        
        elif paso == 'esperando_nombre_lead':
            return manejar_nombre_lead(text, estado_usuario, user_id)
        
        elif paso == 'ofrecer_cita':
            return manejar_ofrecer_cita(text_lower, estado_usuario, user_id)
        
        elif paso == 'solicitar_fecha_cita':
            return manejar_solicitar_fecha_cita(text_lower, estado_usuario, user_id)
        
        elif paso == 'seleccionar_hora_cita':
            return manejar_seleccionar_hora_cita(text, estado_usuario, user_id)
            
        elif paso == 'confirmar_cita':
            return manejar_confirmar_cita(text_lower, estado_usuario, user_id)
        
        elif paso == 'esperando_email_cita':
            return manejar_email_cita(text, estado_usuario, user_id)
        
        elif paso == 'esperando_confirmacion_recordatorio':
            return manejar_confirmacion_recordatorio(text, estado_usuario, user_id)
        
        elif paso == 'vista_fotos':
            return "Para ver fotos, envía 'F' cuando estés en el detalle de una propiedad."

        # 4. BUSCADOR POR TEXTO (Nuevo) - SOLAMENTE SI NO HAY ESTADO ACTIVO PRIORITARIO
        # Y si el paso es menu_principal o resultado_busqueda
        if text_lower.startswith("buscar ") or (len(text_lower) > 3 and paso == 'menu_principal' and not text_lower.isdigit()):
            # DETECTAR SI ES UNA FECHA PERO SE PERDIÓ EL CONTEXTO
            fecha_detectada = analizar_fecha(text_lower)
            if fecha_detectada and len(text_lower.split()) <= 3: # Si es una fecha corta
                return """⚠️ *Sesión expirada o contexto perdido*
                
Parece que querías agendar una fecha, pero no tengo seleccionada ninguna propiedad en este momento.

Por favor:
1. Envía 'Hola' para ver el menú
2. Busca la propiedad nuevamente
3. Selecciona 'Agendar Cita'"""

            termino = text_lower.replace("buscar ", "").strip()
            return manejar_busqueda_keywords(termino, estado_usuario, user_id)

        # 5. OPCIONES DEL MENÚ PRINCIPAL
        if paso == 'menu_principal':
            return manejar_menu_principal(text_lower, estado_usuario, user_id)
        
        # Respuesta por defecto
        return """No pude identificar esa opción. Por favor elegí un número del menú.

9️⃣ *Volver al menú principal*
0️⃣ *Salir del chat*"""

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        log(f"🔥 ERROR EN get_bot_response: {e}\n{error_trace}")
        return "❌ *Lo siento, ocurrió un error interno.*\n\nPor favor, intenta de nuevo enviando 'Hola' o contacta al administrador."

# ========== MANEJADORES DE ESTADO ==========
def manejar_menu_principal(text_lower, estado_usuario, user_id):
    """Maneja las opciones del menú principal"""
    if text_lower == "1":
        # INMUEBLES EN VENTA
        return procesar_opcion_venta(estado_usuario, user_id)
        
    elif text_lower == "2":
        # INMUEBLES EN ALQUILER
        return procesar_opcion_alquiler(estado_usuario, user_id)
        
    elif text_lower == "3":
        # Visitar sitio web
        return "🌐 *Visita nuestra web oficial:*\n\n👉 https://www.dantepropiedades.com.ar\n\nEnvía 'Hola' para volver al menú.\n0️⃣ *❌ SALIR*"

    elif text_lower == "4":
        # Ver mis citas
        return procesar_opcion_mis_citas(user_id)

    elif text_lower == "5":
        # Hablar con asesor
        estado_usuario['paso'] = 'submenu_asesor'
        actualizar_estado_usuario(user_id, estado_usuario)
        return """👤 *HABLAR CON UN ASESOR*

1️⃣ Enviar mensaje al asesor
2️⃣ Solicitar llamada

9️⃣ Volver al menú principal
0️⃣ Salir"""

    elif text_lower == "9":
        # Volver al menú
        return "WELCOME_FLOW_TRIGGER"
        
    elif text_lower == "0":
        # Salir
        return "Gracias por contactarte con Dante Propiedades. ¡Que tengas un excelente día! 🏠🗝️"

    elif text_lower == "8" and user_id == ADMIN_NUMBER.lstrip('549'):
        # Panel admin (solo para número autorizado)
        return mostrar_panel_admin()
    
    else:
        return """No pude identificar esa opción. Por favor elegí un número del menú.

1️⃣ *Inmuebles en Venta* 🏠
2️⃣ *Inmuebles en Alquiler* 🔑
3️⃣ *Visitar nuestro sitio web* 🌐
4️⃣ *Ver mis citas programadas* 📋
5️⃣ *Hablar con un asesor* 👤

9️⃣ *Volver al menú principal*
0️⃣ *Salir del chat*"""

# ========== MANEJADORES DE SUBMENÚS ==========

def manejar_submenu_consultar(text_lower, estado_usuario, user_id):
    """Maneja las opciones del submenú de consulta"""
    if text_lower == "1":
        return "🔎 *Búsqueda por código*\n\nPor favor, enviá el código de la propiedad (ej: UF002).\n\n9️⃣ Volver al menú principal\n0️⃣ Salir"
    elif text_lower == "2":
        return "📍 *Búsqueda por zona*\n\n¿En qué zona estás buscando? (ej: Palermo, Belgrano, Tigre...)\n\n9️⃣ Volver al menú principal\n0️⃣ Salir"
    elif text_lower == "3":
        return procesar_opcion_todas(estado_usuario, user_id)
    else:
        return """No pude identificar esa opción. Por favor elegí un número del menú.

9️⃣ *Volver al menú principal*
0️⃣ *Salir del chat*"""

def manejar_submenu_visita(text_lower, estado_usuario, user_id):
    """Maneja las opciones del submenú de visitas"""
    if text_lower == "1":
        return procesar_opcion_todas(estado_usuario, user_id)
    elif text_lower == "2":
        return "📅 *Días y horarios disponibles*\n\nNuestros horarios generales son de Lunes a Viernes de 9 a 18:30 hs.\n\n9️⃣ Volver al menú principal\n0️⃣ Salir"
    elif text_lower == "3":
        return "✅ *Confirmar visita*\n\nPara confirmar una visita, primero debemos seleccionar una propiedad. \n\n1️⃣ Ver propiedades\n9️⃣ Volver al menú principal\n0️⃣ Salir"
    else:
        return """No pude identificar esa opción. Por favor elegí un número del menú.

9️⃣ *Volver al menú principal*
0️⃣ *Salir del chat*"""

def manejar_submenu_asesor(text_lower, estado_usuario, user_id):
    """Maneja las opciones del submenú de asesor"""
    if text_lower == "1":
        notificar_agente(f"👤 *SOLICITUD DE ASESOR*\n📞 Tel: +{user_id}\n📝 El cliente desea enviar un mensaje.")
        return "✅ *Mensaje enviado!*\n\nUn asesor se pondrá en contacto con vos a la brevedad.\n\n9️⃣ Volver al menú principal\n0️⃣ Salir"
    elif text_lower == "2":
        notificar_agente(f"📞 *SOLICITUD DE LLAMADA*\n📞 Tel: +{user_id}\n📝 El cliente solicita ser llamado.")
        return "✅ *Solicitud registrada!*\n\nTe llamaremos en el horario más conveniente.\n\n9️⃣ Volver al menú principal\n0️⃣ Salir"
    else:
        return """No pude identificar esa opción. Por favor elegí un número del menú.

9️⃣ *Volver al menú principal*
0️⃣ *Salir del chat*"""

def procesar_opcion_venta(estado_usuario, user_id):
    """Procesa la opción de venta"""
    estado_usuario.update({
        'paso': 'listado_propiedades',
        'operacion_seleccionada': 'venta',
        'propiedades_filtradas': filtrar_propiedades_por_operacion('venta')
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    
    propiedades = estado_usuario['propiedades_filtradas']
    if not propiedades:
        return "📭 No hay propiedades en venta por ahora.\n\n1️⃣ *VOLVER AL MENÚ* 🏠\n0️⃣ *❌ SALIR*"
    
    return f"💰 *PROPIEDADES EN VENTA*\nEncontramos *{len(propiedades)}* disponibles:\n\n" + generar_listado_propiedades(propiedades)

def procesar_opcion_alquiler(estado_usuario, user_id):
    """Procesa la opción de alquiler"""
    estado_usuario.update({
        'paso': 'listado_propiedades',
        'operacion_seleccionada': 'alquiler',
        'propiedades_filtradas': filtrar_propiedades_por_operacion('alquiler')
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    
    propiedades = estado_usuario['propiedades_filtradas']
    if not propiedades:
        return "📭 No hay propiedades en alquiler por ahora.\n\n1️⃣ *VOLVER AL MENÚ* 🏠\n0️⃣ *❌ SALIR*"
    
    return f"🔑 *PROPIEDADES EN ALQUILER*\nEncontramos *{len(propiedades)}* disponibles:\n\n" + generar_listado_propiedades(propiedades)

def procesar_opcion_todas(estado_usuario, user_id):
    """Procesa la opción de ver todas las propiedades"""
    estado_usuario.update({
        'paso': 'listado_propiedades',
        'operacion_seleccionada': 'todas',
        'propiedades_filtradas': cargar_propiedades_cached()
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    return "📋 *TODAS LAS PROPIEDADES*\n\n" + generar_listado_propiedades(estado_usuario['propiedades_filtradas'])

def procesar_opcion_mis_citas(user_id):
    """Procesa la opción de ver mis citas"""
    citas = cargar_citas()
    citas_usuario = [c for c in citas if c['telefono'] == user_id and c['estado'] != 'cancelada']
    
    if not citas_usuario:
        return "📅 *No tienes citas agendadas*\n\nPara agendar una cita, primero selecciona una propiedad y haz clic en 'Me interesa' (8).\n\n1️⃣ *VOLVER AL MENÚ* 🏠\n0️⃣ *❌ SALIR*"
    
    mensaje = f"📅 *TUS CITAS AGENDADAS*\n\nTienes *{len(citas_usuario)}* cita(s) activa(s):\n\n"
    
    for i, cita in enumerate(citas_usuario, 1):
        fecha_obj = datetime.strptime(cita['fecha'], "%Y-%m-%d")
        fecha_formateada = fecha_obj.strftime("%d/%m/%Y")
        
        mensaje += f"{i}. *{cita['propiedad_id']}*\n"
        mensaje += f"   📅 {fecha_formateada} - ⏰ {cita['hora']}\n"
        mensaje += f"   📍 Estado: {cita['estado'].upper()}\n"
        
        if cita.get('notas') and cita['notas'] != 'Sin notas adicionales':
            mensaje += f"   📝 Notas: {cita['notas'][:50]}...\n"
        
        mensaje += "   ───────────────\n"
    
    mensaje += f"\nPara consultar o modificar una cita, contacta al administrador.\n\n"
    mensaje += f"Envía 'Hola' para volver al menú.\n0️⃣ *❌ SALIR*"
    
    return mensaje

def mostrar_panel_admin():
    """Muestra el panel administrativo para Dante"""
    return f"""🔐 *PANEL ADMINISTRATIVO*

Hola Dante 👋

Opciones disponibles:

📊 *1. Ver dashboard principal*
📅 *2. Gestionar citas*
👥 *3. Ver leads*
🏠 *4. Gestionar propiedades*
📈 *5. Ver estadísticas*

📱 *0. Volver al menú principal*"""

def manejar_listado_propiedades(text_lower, estado_usuario, user_id):
    """Maneja la selección de propiedades del listado"""
    if not text_lower.isdigit():
        return "Por favor, elegí un número del listado o enviá 'Hola' para volver.\n0️⃣ *❌ SALIR*"
    
    indice = int(text_lower)
    propiedades = estado_usuario.get('propiedades_filtradas', [])
    
    if not propiedades:
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "⚠️ No hay propiedades para mostrar. Envía 'Hola' para volver al menú.\n0️⃣ *❌ SALIR*"
    
    if indice == 0:
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['operacion_seleccionada'] = None
        estado_usuario['propiedades_filtradas'] = []
        estado_usuario['ultimo_indice_preguntado'] = None
        actualizar_estado_usuario(user_id, estado_usuario)
        return "WELCOME_FLOW_TRIGGER"
    
    if 1 <= indice <= len(propiedades):
        propiedad = propiedades[indice - 1]
        estado_usuario.update({
            'paso': 'detalle_propiedad',
            'ultimo_indice_preguntado': indice
        })
        actualizar_estado_usuario(user_id, estado_usuario)
        
        registrar_lead(user_id, propiedad.get('id_temporal', 'N/A'), "ver_detalle", f"Título: {propiedad.get('titulo')}")
        
        operacion = propiedad.get('operacion', '')
        titulo_op = "💰 VENTA" if operacion == 'venta' else "🔑 ALQUILER" if operacion == 'alquiler' else "🏠 PROPIEDAD"
        return f"{titulo_op}\n" + "─" * 30 + "\n" + formatear_detalle_propiedad(propiedad)
    else:
        return f"❌ El número {indice} está fuera de rango (1-{len(propiedades)}). Elige uno o envía 9 para volver.\n0️⃣ *Salir*"

def manejar_detalle_propiedad(text_lower, estado_usuario, user_id):
    """Maneja las opciones en el detalle de propiedad"""
    if text_lower == "1":
        estado_usuario.update({
            'paso': 'menu_principal',
            'operacion_seleccionada': None,
            'propiedades_filtradas': [],
            'ultimo_indice_preguntado': None
        })
        actualizar_estado_usuario(user_id, estado_usuario)
        return "WELCOME_FLOW_TRIGGER"
    
    if text_lower.isdigit():
        indice = int(text_lower)
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        if 1 <= indice <= len(propiedades):
            propiedad = propiedades[indice - 1]
            estado_usuario['ultimo_indice_preguntado'] = indice
            actualizar_estado_usuario(user_id, estado_usuario)
            
            registrar_lead(user_id, propiedad.get('id_temporal', 'N/A'), "ver_detalle", f"Título: {propiedad.get('titulo')}")
            
            operacion = propiedad.get('operacion', '')
            titulo_op = "💰 VENTA" if operacion == 'venta' else "🔑 ALQUILER" if operacion == 'alquiler' else "🏠 PROPIEDAD"
            return f"{titulo_op}\n" + "─" * 30 + "\n" + formatear_detalle_propiedad(propiedad)
    
    return "📷 'F' Fotos | 8️⃣ '8' Me interesa\n9️⃣ Volver al menú | 0️⃣ *Salir*"

def manejar_nombre_lead(text, estado_usuario, user_id):
    """Maneja la captura del nombre del lead"""
    nombre_cliente = text.strip()
    
    if len(nombre_cliente) < 2:
        return "❌ Por favor, ingresa tu nombre completo (mínimo 2 caracteres).\n\n9️⃣ *Volver al menú principal*\n0️⃣ *Salir*"
    
    estado_usuario['nombre_cliente'] = nombre_cliente
    
    indice = estado_usuario.get('ultimo_indice_preguntado')
    propiedades = estado_usuario.get('propiedades_filtradas', [])
    
    if indice and 1 <= indice <= len(propiedades):
        propiedad = propiedades[indice - 1]
        propiedad_id = propiedad.get('id_temporal', 'N/A')
        propiedad_titulo = propiedad.get('titulo', 'Propiedad sin título')
        
        registrar_lead(user_id, propiedad_id, "lead_completo", f"Nombre: {nombre_cliente}")
        
        notificar_agente(f"🔥 *NUEVO INTERESADO*\n👤 Cliente: {nombre_cliente}\n📞 Tel: +{user_id}\n🏠 Propiedad: {propiedad_titulo}")
        
        estado_usuario['paso'] = 'ofrecer_cita'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        return f"""✅ *¡Perfecto {nombre_cliente}!*

Hemos registrado tu interés en:
🏠 *{propiedad_titulo}*

📅 *¿Te gustaría agendar una cita para visitar la propiedad?*

1️⃣ *SÍ, AGENDAR CITA* 📅 (Recomendado)
2️⃣ *No por ahora, solo información* 📋
3️⃣ *Ya la vi, quiero ofertar* 💰
9️⃣ *Volver al menú principal*
0️⃣ *Salir del chat* ❌"""
    else:
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "❌ Hubo un error al procesar tu interés. Por favor, volvé a buscar la propiedad.\n\n9️⃣ Volver al menú principal\n0️⃣ *Salir*"

def manejar_ofrecer_cita(text_lower, estado_usuario, user_id):
    """Maneja la oferta de cita"""
    if text_lower in ["1", "si", "sí", "agendar", "cita", "visita"]:
        estado_usuario['paso'] = 'solicitar_fecha_cita'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        hoy = datetime.now()
        mañana = hoy + timedelta(days=1)
        ejemplo_fecha = mañana.strftime("%d-%m-%Y")
        
        # Obtener propiedad actual para mostrar días específicos
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades_lista = estado_usuario.get('propiedades_filtradas', [])
        propiedad_id = None
        if indice and 1 <= indice <= len(propiedades_lista):
            propiedad_id = propiedades_lista[indice - 1].get('id_temporal')
            
        texto_dias = obtener_texto_dias_habiles(propiedad_id)
        texto_horarios = obtener_texto_horarios(propiedad_id)
        
        return f"""📅 *EXCELENTE {estado_usuario.get('nombre_cliente', 'Cliente')}!*

Vamos a agendar tu visita.

📋 *Formato de fecha:* **DD-MM-AAAA**
📅 *Ejemplo para mañana:* **{ejemplo_fecha}**

📍 *Recomendaciones:*
• **Días de visita:** {texto_dias}
• Agendar con 24-48hs de anticipación
• Horarios {texto_horarios}

📅 *Envía la fecha que prefieras (ej: {ejemplo_fecha}, hoy, mañana, lunes) o 'Ver fechas' para ver disponibilidad:*"""
    
    elif text_lower in ["2", "no", "solo info", "informacion", "información"]:
        nombre_cliente = estado_usuario.get('nombre_cliente', 'Cliente')
        
        notificar_agente(f"📋 *LEAD SIN CITA - SOLO INFO*\n👤 {nombre_cliente}\n📞 +{user_id}\n📝 Solo solicitó información")
        
        estado_usuario.update({
            'paso': 'menu_principal',
            'nombre_cliente': None
        })
        actualizar_estado_usuario(user_id, estado_usuario)
        
        return f"""✅ *Entendido {nombre_cliente}!*

Un asesor se contactará contigo para brindarte toda la información.

1️⃣ *VOLVER AL MENÚ* 🏠
0️⃣ *❌ SALIR*"""
    
    elif text_lower in ["3", "ofertar", "oferta", "comprar", "alquilar ya"]:
        nombre_cliente = estado_usuario.get('nombre_cliente', 'Cliente')
        
        notificar_agente(f"🔥🔥 *LEAD CALIENTE - QUIERE OFERTAR!* 🔥🔥\n👤 {nombre_cliente}\n📞 +{user_id}\n💸 LISTO PARA OPERAR")
        
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        if indice and 1 <= indice <= len(propiedades):
            propiedad = propiedades[indice - 1]
            registrar_lead(user_id, propiedad.get('id_temporal', 'N/A'), "lead_caliente_oferta", f"Nombre: {nombre_cliente} - QUIERE OFERTAR")
        
        estado_usuario.update({
            'paso': 'menu_principal',
            'nombre_cliente': None
        })
        actualizar_estado_usuario(user_id, estado_usuario)
        
        return f"""🎯 *¡EXCELENTE {nombre_cliente}!*

🔥 *PRIORIDAD MÁXIMA*
Un asesor te contactará en los próximos **15 minutos** para gestionar tu oferta.

📞 *Teléfono de contacto:* +{user_id}

⏰ *Horario de contacto:* Inmediato

¡Gracias por tu interés! 🏠💸

1️⃣ *VOLVER AL MENÚ* 🏠
0️⃣ *❌ SALIR*"""
    
    elif text_lower in ["0", "salir", "chau", "adiós"]:
        estado_usuario.update({
            'paso': 'menu_principal',
            'nombre_cliente': None
        })
        actualizar_estado_usuario(user_id, estado_usuario)
        return "👋 ¡Gracias por contactarnos! Para volver al menú, envía 'Hola'. Dante Propiedades! 🏠🗝️"
    
    else:
        return """❌ Opción no válida. Por favor selecciona:

1️⃣ *SÍ, AGENDAR CITA* 📅
2️⃣ *No por ahora, solo información* 📋
3️⃣ *Ya la vi, quiero ofertar* 💰
0️⃣ *❌ SALIR*"""

def manejar_solicitar_fecha_cita(text_lower, estado_usuario, user_id):
    """Maneja la solicitud de fecha para la cita"""
    if text_lower in ["ver fechas", "disponibles", "fechas"]:
        return mostrar_fechas_disponibles(estado_usuario)
    
    # 1. Analizar Fecha
    fecha_ingresada = analizar_fecha(text_lower)
    
    if not fecha_ingresada:
        return """❌ *No entendí la fecha*
Por favor, probá con:
✅ "Mañana a las 10"
✅ "El jueves por la tarde"
✅ "25-10-2026"

1️⃣ *Ver fechas* (Ver disponibilidad)
0️⃣ *Volver* (Ir al menú)"""

    # Validaciones de fecha
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if fecha_ingresada < hoy and fecha_ingresada.date() != hoy.date():
         return "❌ *Fecha pasada*\nPor favor elige una fecha futura."
    
    # 2. Analizar Hora (si el usuario la incluyó)
    hora_ingresada = analizar_hora(text_lower)
    
    fecha_str = fecha_ingresada.strftime("%Y-%m-%d")
    fecha_display = fecha_ingresada.strftime("%d-%m-%Y")
    
    # Obtener propiedad actual
    indice = estado_usuario.get('ultimo_indice_preguntado')
    propiedades_lista = estado_usuario.get('propiedades_filtradas', [])
    propiedad_id = None
    if indice and 1 <= indice <= len(propiedades_lista):
        propiedad_id = propiedades_lista[indice - 1].get('id_temporal')
        
    horarios_disponibles = obtener_horarios_disponibles(fecha_str, propiedad_id)
    
    if not horarios_disponibles:
         return f"""❌ *Sin disponibilidad*
No hay horarios para el {fecha_display}.

1️⃣ *Ver fechas* (Elegir otro día)
0️⃣ *Volver* (Ir al menú)"""

    estado_usuario['fecha_cita'] = fecha_str
    
    # CASO A: Usuario indicó fecha Y hora ("mañana a las 10")
    if hora_ingresada:
        if hora_ingresada in horarios_disponibles:
            # Hora válida -> Ir a confirmación
            estado_usuario['hora_cita'] = hora_ingresada
            estado_usuario['paso'] = 'esperando_email_cita'
            actualizar_estado_usuario(user_id, estado_usuario)
            
            return f"""📅 *FECHA SELECCIONADA:* {fecha_display} a las {hora_ingresada} hs.

📧 *¿Te gustaría dejarnos tu correo electrónico?* (Opcional)
Esto nos permite enviarte recordatorios y más detalles de la propiedad.

1️⃣ *Escribí tu email*
2️⃣ *No, saltar este paso* ⏭️"""
        else:
            # Hora inválida o ocupada
            return f"""❌ *Horario no disponible*
El horario {hora_ingresada} no está disponible para el {fecha_display}.

⏰ *Horarios libres:*
{", ".join(horarios_disponibles)}

Por favor, escribí uno de los horarios disponibles:

0️⃣ *❌ SALIR*"""

    # CASO B: Solicitó solo fecha -> Pedir hora
    estado_usuario['paso'] = 'seleccionar_hora_cita'
    estado_usuario['horarios_disponibles'] = horarios_disponibles
    actualizar_estado_usuario(user_id, estado_usuario)
    
    return mostrar_seleccion_horarios(fecha_display, horarios_disponibles)

def manejar_seleccionar_hora_cita(text, estado_usuario, user_id):
    """Maneja la selección de hora"""
    text_lower = text.lower()
    
    if text_lower in ["0", "salir", "cancelar"]:
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "❌ Operación cancelada.\n\n1️⃣ *VOLVER AL MENÚ* 🏠\n0️⃣ *❌ SALIR*"
    
    if text_lower in ["ver fechas", "cambiar fecha", "atrás", "atras"]:
        estado_usuario['paso'] = 'solicitar_fecha_cita'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "📅 Escribí la nueva fecha (ej: 'mañana', 'jueves'):"

    hora_elegida = analizar_hora(text)
    horarios_disponibles = estado_usuario.get('horarios_disponibles', [])
    
    # Si el usuario escribió algo que no parece hora, o la hora no está en la lista
    if not hora_elegida or hora_elegida not in horarios_disponibles:
        # Intento de matcheo flexible (si escribió "10" y está "10:00")
        if text.strip() in horarios_disponibles: 
             hora_elegida = text.strip()
        else:
            return f"""❌ *Horario no válido*
Por favor elegí uno de la lista:
{", ".join(horarios_disponibles)}

1️⃣ *Cambiar fecha* (Elegir otro día)
0️⃣ *Volver* (Ir al menú)"""
            
    # Hora válida
    estado_usuario['hora_cita'] = hora_elegida
    estado_usuario['paso'] = 'esperando_email_cita' 
    actualizar_estado_usuario(user_id, estado_usuario)
    
    return f"""📅 *HORARIO SELECCIONADO:* {hora_elegida} hs.

📧 *¿Te gustaría dejarnos tu correo electrónico?* (Opcional)
Esto nos permite enviarte recordatorios y más detalles de la propiedad.

1️⃣ *Escribí tu email*
2️⃣ *No, saltar este paso* ⏭️"""

def manejar_email_cita(text, estado_usuario, user_id):
    """Maneja la captura del email (opcional)"""
    text_lower = text.lower().strip()
    
    if text_lower in ["2", "no", "saltar", "skip", "n", "noup"]:
        estado_usuario['email_cliente'] = None
    else:
        # Validación básica de email
        if "@" in text and "." in text and len(text) > 5:
            estado_usuario['email_cliente'] = text
        else:
            # Si no parece un email y no quiso saltar, le avisamos pero permitimos saltar
            if text_lower == "1":
                return "📧 Por favor, escribí tu correo electrónico o enviá *'2'* para saltar."
            
            return f"⚠️ *{text}* no parece un correo válido.\n\nPor favor, escribí un email válido o enviá *'2'* para saltar este paso."

    estado_usuario['paso'] = 'confirmar_cita'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    fecha_display = datetime.strptime(estado_usuario['fecha_cita'], "%Y-%m-%d").strftime("%d-%m-%Y")
    hora = estado_usuario['hora_cita']
    email = estado_usuario.get('email_cliente', 'No proporcionado')
    
    return f"""📅 *RESUMEN DE TU VISITA*
            
📅 Fecha: *{fecha_display}*
⏰ Hora: *{hora} hs*
📧 Email: *{email}*

¿Confirmas la cita?
1️⃣ *SÍ, Confirmar* ✅
2️⃣ *Cambiar fecha/hora* 🔄
0️⃣ *Cancelar* ❌"""

def manejar_confirmar_cita(text_lower, estado_usuario, user_id):
    """Paso final de confirmación explícita"""
    if text_lower in ["1", "si", "sí", "confirmar", "ok", "dale"]:
        # Guardar cita
        fecha = estado_usuario.get('fecha_cita')
        hora = estado_usuario.get('hora_cita')
        nombre = estado_usuario.get('nombre_cliente', 'Cliente')
        email = estado_usuario.get('email_cliente')
        
        # Obtener propiedad
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades_lista = estado_usuario.get('propiedades_filtradas', [])
        propiedad_id = "N/A"
        propiedad_titulo = "Propiedad"
        
        # Verificar que propiedades_lista sea una lista y tenga elementos
        if propiedades_lista and isinstance(propiedades_lista, list) and indice and 1 <= indice <= len(propiedades_lista):
            propiedad = propiedades_lista[indice - 1]
            # Verificar que propiedad sea un diccionario
            if isinstance(propiedad, dict):
                propiedad_id = propiedad.get('id_temporal', 'N/A')
                propiedad_titulo = propiedad.get('titulo', 'Propiedad')
            else:
                # Si es un string, usarlo directamente
                propiedad_id = str(propiedad)
                propiedad_titulo = str(propiedad)

        # LLAMAR a la función crear_cita
        crear_cita(
            user_id=user_id,
            nombre=nombre,
            telefono=user_id,
            fecha=fecha,
            hora=hora,
            propiedad_id=propiedad_id,
            email=email,
            notas="Agendado vía Bot"
        )
        
        # Resetear estado
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['fecha_cita'] = None
        estado_usuario['hora_cita'] = None
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Mensaje de confirmación
        return f"""✅ *¡VISITA AGENDADA!*
        
Hemos confirmado tu visita para:
📅 *{datetime.strptime(fecha, "%Y-%m-%d").strftime("%d-%m-%Y")}*
⏰ *{hora} hs*
🏠 {propiedad_titulo}

Te esperamos. Si necesitas cancelar, por favor avísanos.
👋 ¡Gracias!"""

    elif text_lower in ["2", "cambiar", "no"]:
        estado_usuario['paso'] = 'solicitar_fecha_cita'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "🔄 Ok, cambiemos la fecha. ¿Cuándo te gustaría venir? (ej: 'mañana 10am')"
        
    else:
        # Cancelar
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "❌ Operación cancelada.\n\n1️⃣ *VOLVER AL MENÚ* 🏠\n0️⃣ *❌ SALIR*"

def crear_cita(user_id, nombre, telefono, fecha, hora, propiedad_id, email=None, notas=""):
    """Crea una nueva cita y la guarda en JSON y PostgreSQL"""
    conn = None
    try:
        citas = cargar_citas()
        nueva_cita = {
            'id': f"cita_{len(citas)+1:04d}",
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
        
        citas.append(nueva_cita)
        
        # 1. Guardar en JSON
        if not guardar_citas(citas):
            log("⚠️ Error guardando cita en JSON", "WARNING")
        
        log(f"✅ Cita creada localmente: {nueva_cita['id']} para {nombre}")
        
        # 2. Guardar en PostgreSQL (con nuevas columnas)
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
                False, '09:00'  # Valores por defecto para recordatorios
            ))
            
            db_record_id = cursor.fetchone()[0]
            conn.commit()
            log(f"✅ Cita guardada en PostgreSQL - ID DB: {db_record_id}")
            
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
        notificar_cita_admin(nueva_cita)
        
        return nueva_cita
        
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

# Helper para mostrar horarios (extraído para reusar)
def mostrar_seleccion_horarios(fecha_display, horarios):
    mensaje = f"📅 *Fecha:* **{fecha_display}**\n\n"
    mensaje += "⏰ *HORARIOS DISPONIBLES:*\n"
    mensaje += ", ".join(horarios)
    mensaje += "\n\n⏳ *Escribí el horario* (ej: '10:00' o '10 am')"
    return mensaje

def mostrar_fechas_disponibles(estado_usuario):
    # Lógica auxiliar para mostrar fechas (simplificada del código anterior)
    # ... (Se mantiene lógica de iterar y mostrar calendario)
    return "📅 (Calendario simplificado) Escribí una fecha..."

def manejar_busqueda_keywords(termino, estado_usuario, user_id):
    """Busca propiedades por palabras clave y actualiza el estado"""
    global propiedades
    propiedades = cargar_propiedades_cached()
        
    terminos = termino.lower().split()
    resultados = []
    
    for p in propiedades:
        match_score = 0
        texto_busqueda = f"{p.get('titulo', '')} {p.get('descripcion', '')} {p.get('barrio', '')} {p.get('tipo', '')}".lower()
        
        for t in terminos:
            if t in texto_busqueda:
                match_score += 1
        
        if match_score >= len(terminos): # Deben coincidir todas las palabras clave
            resultados.append(p)
            
    if not resultados:
        return f"🔍 No encontré propiedades que coincidan con *'{termino}*. \n\nIntentá con otras palabras (ej: 'casa parque') o enviá 'Hola' para ver todo.\n0️⃣ *❌ SALIR*"
        
    estado_usuario.update({
        'paso': 'listado_propiedades',
        'propiedades_filtradas': resultados,
        'operacion_seleccionada': 'busqueda'
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    
    mensaje = f"🔎 *Resultados para: {termino}* ({len(resultados)})\n\n"
    for i, p in enumerate(resultados[:5]):
        mensaje += f"*{i+1}️⃣ {p.get('titulo')}*\n📍 {p.get('barrio', 'S/D')} - ${p.get('precio', 'S/D')}\n\n"
    
    if len(resultados) > 5:
        mensaje += "📝 _Mostrando los primeros 5 resultados..._\n"
        
    mensaje += "\n👉 *Respondé con el número* (1, 2, 3...) para ver más detalle.\n"
    mensaje += "0️⃣ *❌ SALIR*"
    return mensaje


# ========== FUNCIONES DE WHATSAPP API MEJORADAS ==========
# def check_token_validity():
#     """Verifica si el token de acceso es válido"""
#     try:
#         url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}"
#         headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
#         response = requests.get(url, headers=headers, timeout=10)
        
#         if response.status_code == 200:
#             data = response.json()
#             log(f"✅ Token válido: {data.get('verified_name', 'N/A')}")
#             return True, data
#         else:
#             error_data = response.json() if response.content else {}
#             log(f"❌ Token inválido: Status {response.status_code}")
#             return False, error_data
            
#     except Exception as e:
#         log(f"🔥 Error verificando token: {e}")
#         return False, {"error": str(e)}


def check_token_validity():
    """Verifica si el token de acceso es válido"""
    try:
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}?fields=verified_name"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            log(f"✅ Token válido. Verified name: {data.get('verified_name', 'N/A')}")
            return True, data

        else:
            error_data = response.json() if response.content else {}
            log(f"❌ Token inválido o sin permisos. Status {response.status_code}")
            log(f"Detalles: {error_data}")
            return False, error_data

    except Exception as e:
        log(f"🔥 Error verificando token: {e}")
        return False, {"error": str(e)}
    
    
    

def send_whatsapp_message(to_number, message_text):
    """Envía un mensaje de WhatsApp usando texto directo"""
    log(f"🔍 Usando token: {ACCESS_TOKEN[:50]}...")  # Muestra los primeros 50 caracteres
    try:
        token_valid, token_info = check_token_validity()
        if not token_valid:
            log("❌ Token inválido - No se puede enviar mensaje")
            return {
                "status": "error",
                "error_code": "invalid_token",
                "error_message": "Token de acceso expirado o inválido"
            }
        
        # 🔥 FUNCIÓN DE TRANSFORMACIÓN DE NÚMEROS MEJORADA
        def transform_number(number):
            # Para números argentinos en formato 5491151511579 (el que envía Meta)
            if number and number.startswith("549") and len(number) == 13:
                # Formato para sandbox: 54111551511579
                # Quitamos el 9 y agregamos 15
                country = number[:2]  # 54
                area = number[3:5]    # 11
                rest = number[5:]     # 51511579
                transformed = f"{country}{area}15{rest}"  # 54111551511579
                log(f"🔄 Transformando número: {number} -> {transformed}")
                return transformed
            # Si ya está en formato correcto, devolver igual
            return number
        
        log(f"🔍 Número original: {to_number}")
        transformed_number = transform_number(to_number)
        log(f"🔍 Número transformado: {transformed_number}")
        
        # Aplicar también la normalización por si acaso
        transformed_number = normalizar_numero_argentina(transformed_number)
        log(f"🔍 Número final para API: {transformed_number}")
        
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": transformed_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_text
            }
        }
        
        log(f"📤 Enviando mensaje a: {to_number}")

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            message_id = result.get('messages', [{}])[0].get('id', 'N/A')
            log(f"✅ Mensaje enviado exitosamente - ID: {message_id}")
            return {
                "status": "success",
                "message_id": message_id,
                "details": "Mensaje de texto directo enviado"
            }
        else:
            error_data = response.json() if response.content else {}
            error_code = error_data.get('error', {}).get('code', 'N/A')
            error_message = error_data.get('error', {}).get('message', 'Error desconocido')
            
            log(f"❌ Error API: {error_code} - {error_message}")
            
            if error_code == 190:
                return {
                    "status": "error",
                    "error_code": error_code,
                    "error_message": "Token expirado. Renueva el token en Meta Developers."
                }
            elif error_code == 10:
                return {
                    "status": "error",
                    "error_code": error_code,
                    "error_message": "El token no tiene permisos suficientes."
                }
            
            return {
                "status": "error",
                "error_code": error_code,
                "error_message": error_message
            }
            
    except Exception as e:
        log(f"🔥 Error inesperado: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

def notificar_agente(mensaje):
    """Envía una notificación al número de Dante (ADMIN_NUMBER)"""
    log(f"📢 Notificando al agente: {mensaje[:50]}...")
    return send_whatsapp_message(ADMIN_NUMBER, f"🔔 *ALERTA DANTE-INSIGHTS*\n{mensaje}")

def send_photos_async(user_id, propiedad_id, base_url):
    """Tarea ejecutada en hilo secundario para enviar fotos"""
    try:
        propiedades = cargar_propiedades_cached()
        propiedad = next((p for p in propiedades if p.get('id_temporal') == propiedad_id), None)
        
        if not propiedad:
            log(f"❌ No se encontró propiedad {propiedad_id}")
            return

        fotos = propiedad.get('fotos', [])
        if not fotos:
            send_whatsapp_message(user_id, "⚠️ No hay fotos disponibles para esta propiedad.")
            return

        send_whatsapp_message(user_id, f"📸 *Enviando {len(fotos)} fotos...*")

        for foto_path in fotos:
            img_url = f"{base_url}/{foto_path.lstrip('/')}"
            send_whatsapp_image(user_id, img_url)
            
        notificar_agente(f"👤 Cliente {user_id} está viendo fotos de: {propiedad.get('titulo')}")
        registrar_lead(user_id, propiedad.get('id_temporal', 'N/A'), "ver_fotos")
        
        send_whatsapp_message(user_id, "✅ *¡Fotos enviadas!*\n\n1️⃣ *VOLVER AL MENÚ* 🏠\n0️⃣ *❌ SALIR*")
        
        log(f"✅ Envío de fotos completado para {user_id}")
    except Exception as e:
        log(f"🔥 Error en hilo de fotos: {e}")

def send_whatsapp_image(to_number, image_url, caption=""):
    """Envía una imagen por WhatsApp"""
    try:
        token_valid, _ = check_token_validity()
        if not token_valid:
            return False
        
        # 🔥 MISMA TRANSFORMACIÓN PARA IMÁGENES
        def transform_number(number):
            if number.startswith("549") and len(number) == 13:
                country = number[:2]
                area = number[3:5]
                rest = number[5:]
                return f"{country}{area}15{rest}"
            return number
        
        transformed_number = transform_number(to_number)
        
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": transformed_number,
            "type": "image",
            "image": {
                "link": image_url,
                "caption": caption[:1024]
            }
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            log(f"✅ Imagen enviada: {image_url}")
            return True
        else:
            log(f"❌ Error enviando imagen")
            return False
            
    except Exception as e:
        log(f"🔥 Error enviando imagen: {str(e)}")
        return False

def send_welcome_flow(user_id):
    """Envía el flujo completo de bienvenida"""
    welcome_message = """🏠🗝️ *DANTE PROPIEDADES*

¡Hola! Soy el asistente inmobiliario de Dante Propiedades.

*¿Cómo podemos ayudarte hoy?*
Elegí el número de tu opción:

1️⃣ *INMUEBLES EN VENTA* 🏠
2️⃣ *INMUEBLES EN ALQUILER* 🔑
3️⃣ *Visitar nuestro sitio web* 🌐
4️⃣ *Ver mis citas programadas* 📋
5️⃣ *Hablar con un asesor* 👤

9️⃣ *Volver al menú principal*
0️⃣ *Salir del chat*

Para seleccionar, solo enviá el número."""
    
    return send_whatsapp_message(user_id, welcome_message)

# ========== RUTAS PRINCIPALES ==========
@app.route("/")
def home():
    """Página principal"""
    propiedades = cargar_propiedades_cached()
    ventas = len([p for p in propiedades if p.get('operacion') == 'venta'])
    alquileres = len([p for p in propiedades if p.get('operacion') == 'alquiler'])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🏠 WhatsApp Bot - Dante Propiedades</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .status {{ padding: 10px; border-radius: 5px; margin: 10px 0; }}
            .success {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .error {{ background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            .test-btn {{ background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }}
            .test-btn:hover {{ background-color: #0056b3; }}
            .info-box {{ background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            .prop-stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
            .stat-box {{ background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; flex: 1; margin: 0 10px; }}
        </style>
    </head>
    <body>
        <h1>🏠 WhatsApp Bot - Dante Propiedades</h1>
        
        <div class="info-box">
            <h3>🤖 Información del Bot Inmobiliario</h3>
            <p><strong>📞 Número Sandbox:</strong> +1 555 149 2382</p>
            <p><strong>📊 Propiedades cargadas:</strong> {len(propiedades)} propiedades disponibles</p>
            <p><strong>🚀 Instrucciones:</strong> Envía "Hola" al número de WhatsApp para comenzar</p>
        </div>
        
        <div class="prop-stats">
            <div class="stat-box">
                <h3>💰 VENTA</h3>
                <p style="font-size: 24px; font-weight: bold; color: #28a745;">{ventas}</p>
                <p>propiedades</p>
            </div>
            <div class="stat-box">
                <h3>🔑 ALQUILER</h3>
                <p style="font-size: 24px; font-weight: bold; color: #17a2b8;">{alquileres}</p>
                <p>propiedades</p>
            </div>
            <div class="stat-box">
                <h3>📋 TOTAL</h3>
                <p style="font-size: 24px; font-weight: bold; color: #6f42c1;">{len(propiedades)}</p>
                <p>propiedades</p>
            </div>
        </div>
        
        <h2>🔧 Pruebas del Sistema</h2>
        <button class="test-btn" onclick="testSend()">Probar envío manual</button>
        <button class="test-btn" onclick="testMenu()">Probar flujo de propiedades</button>
        <div id="testResult" style="margin-top: 10px;"></div>
        
        <h2>🔑 Estado del Token</h2>
        <div id="tokenStatus" class="status">Verificando token...</div>
        <p><a href="/token-help" target="_blank">📖 Instrucciones para renovar token</a></p>
        
        <h2>📊 Sistema y Propiedades</h2>
        <p>
            <a href="/health">Ver estado del sistema</a> | 
            <a href="/webhook" target="_blank">Verificar webhook</a> | 
            <a href="/propiedades-info">Ver propiedades cargadas</a>
        </p>
        
        <script>
            function checkToken() {{
                fetch('/token-status')
                    .then(r => r.json())
                    .then(data => {{
                        const tokenDiv = document.getElementById('tokenStatus');
                        if (data.valid) {{
                            tokenDiv.className = 'status success';
                            tokenDiv.innerHTML = '<strong>✅ TOKEN VÁLIDO:</strong> Conectado a Meta API<br>' +
                                                 '<strong>Nombre:</strong> ' + (data.name || 'N/A') + '<br>' +
                                                 '<strong>Número:</strong> ' + (data.number || 'N/A');
                        }} else {{
                            tokenDiv.className = 'status error';
                            tokenDiv.innerHTML = '<strong>❌ TOKEN INVÁLIDO:</strong> ' + (data.error || 'Error desconocido') +
                                                 '<br><strong>⚠️ El bot NO puede enviar mensajes</strong>';
                        }}
                    }});
            }}
            
            function testSend() {{
                const btn = event.target;
                const resultDiv = document.getElementById('testResult');
                
                btn.disabled = true;
                btn.textContent = 'Enviando...';
                resultDiv.innerHTML = '<div class="status">Enviando prueba...</div>';
                
                fetch('/test')
                    .then(r => r.json())
                    .then(data => {{
                        if (data.result.status === 'success') {{
                            resultDiv.innerHTML = '<div class="status success">✅ Prueba enviada exitosamente</div>';
                        }} else {{
                            resultDiv.innerHTML = '<div class="status error">❌ Error en prueba: ' + (data.result.error_message || data.result.error || 'Error desconocido') + '</div>';
                        }}
                        btn.disabled = false;
                        btn.textContent = 'Probar envío manual';
                        checkToken();
                    }})
                    .catch(error => {{
                        resultDiv.innerHTML = '<div class="status error">❌ Error de conexión: ' + error + '</div>';
                        btn.disabled = false;
                        btn.textContent = 'Probar envío manual';
                    }});
            }}
            
            function testMenu() {{
                const resultDiv = document.getElementById('testResult');
                resultDiv.innerHTML = '<div class="status">Probando flujo de propiedades...</div>';
                
                fetch('/test-propiedades')
                    .then(r => r.json())
                    .then(data => {{
                        let html = '<h3>✅ Prueba de propiedades completada:</h3>';
                        html += '<div class="status success">';
                        html += '<strong>Propiedades cargadas:</strong> ' + data.total_propiedades + '<br>';
                        html += '<strong>En venta:</strong> ' + data.venta_count + '<br>';
                        html += '<strong>En alquiler:</strong> ' + data.alquiler_count + '<br>';
                        html += '<strong>Archivo:</strong> ' + data.archivo;
                        html += '</div>';
                        resultDiv.innerHTML = html;
                    }})
                    .catch(error => {{
                        resultDiv.innerHTML = '<div class="status error">❌ Error: ' + error + '</div>';
                    }});
            }}
            
            checkToken();
        </script>
    </body>
    </html>
    """
    return html, 200



@app.route("/debug/postgresql", methods=["GET"])
def debug_pg():
    """Depurar conexión a PostgreSQL"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"conexion": "fallida", "error": "No se pudo conectar"}), 500
            
        cursor = conn.cursor()
        
        # 2. Ver tablas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tablas = [t[0] for t in cursor.fetchall()]
        
        # 3. Ver estructura de leads si existe
        estructura_leads = []
        if 'leads' in tablas:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'leads'
                ORDER BY ordinal_position
            """)
            estructura_leads = cursor.fetchall()
        
        # 4. Contar registros
        total_leads = 0
        if 'leads' in tablas:
            cursor.execute("SELECT COUNT(*) FROM leads")
            total_leads = cursor.fetchone()[0]
        
        # 5. Probar inserción de prueba
        test_insert = False
        test_id = None
        try:
            cursor.execute("""
                INSERT INTO leads (telefono, nombre, accion, detalles)
                VALUES ('test_5491151511579', 'TEST DEBUG', 'debug_test', 'Prueba desde /debug/postgresql')
                RETURNING id
            """)
            test_id = cursor.fetchone()[0]
            conn.commit()
            test_insert = True
        except Exception as e:
            conn.rollback()
            test_error = str(e)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "conexion": "exitosa",
            "tablas": tablas,
            "estructura_leads": estructura_leads,
            "total_leads": total_leads,
            "test_insert": test_insert,
            "test_id": test_id if test_insert else None,
            "test_error": test_error if not test_insert else None,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "conexion": "fallida",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500
        
@app.route("/debug/save-test", methods=["GET"])
def debug_save_test():
    """Probar guardado manual en PostgreSQL"""
    try:
        result = guardar_en_postgresql(
            telefono="5491151511579",
            nombre="TEST MANUAL",
            accion="test_manual",
            detalles="Prueba manual desde /debug/save-test"
        )
        
        if result:
            return jsonify({
                "status": "success",
                "message": "Lead guardado manualmente en PostgreSQL",
                "lead_id": result,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "No se pudo guardar en PostgreSQL",
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    """Webhook para recibir mensajes de WhatsApp"""
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        log("🔍 Solicitud GET al webhook")
        log(f"   Mode: {mode}, Token: {token}")
        
        if mode and token:
            if mode == "subscribe" and token == VERIFY_TOKEN:
                log("✅ Webhook verificado exitosamente")
                return challenge, 200
            else:
                log("❌ Verificación fallida - Token incorrecto")
                return "Verification failed", 403
        
        return "Webhook endpoint", 200
    
    elif request.method == "POST":
        log("📨 Nuevo webhook POST recibido")
        
        try:
            data = request.get_json()
            
            if not data:
                log("❌ Datos JSON vacíos")
                return jsonify({"status": "no_data"}), 200
            
            if data.get("object") != "whatsapp_business_account":
                log("❌ No es un webhook de WhatsApp Business")
                return jsonify({"status": "not_whatsapp"}), 200
            
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    if "messages" in value:
                        messages = value["messages"]
                        
                        for message in messages:
                            if message.get("type") == "text":
                                message_id = message.get("id")
                                
                                if message_id in processed_message_ids:
                                    log(f"🛑 Mensaje duplicado ignorado: {message_id}")
                                    continue
                                    
                                processed_message_ids.append(message_id)
                                
                                from_number = message.get("from")
                                message_text = message.get("text", {}).get("body", "")
                                
                                if from_number and message_text:
                                    log(f"👤 Usuario: {from_number}, Texto: {message_text}")
                                    
                                    response_text = get_bot_response(message_text, from_number)
                                    
                                    if response_text == "WELCOME_FLOW_TRIGGER":
                                        log("🎯 Enviando flujo de bienvenida")
                                        result = send_welcome_flow(from_number)
                                    elif response_text.startswith("PHOTOS_TRIGGER|"):
                                        prop_id = response_text.split("|")[1]
                                        base_url = request.host_url.rstrip('/')
                                        if "onrender.com" in base_url and not base_url.startswith("https"):
                                            base_url = base_url.replace("http://", "https://")
                                        
                                        log(f"🚀 Iniciando hilo de fotos para propiedad {prop_id}")
                                        thread = threading.Thread(target=send_photos_async, args=(from_number, prop_id, base_url))
                                        thread.start()
                                        
                                        confirmacion = "📸 *Enviando fotos...* Esto puede tardar unos segundos.\n\nEnvía 'Hola' para volver al menú."
                                        result = send_whatsapp_message(from_number, confirmacion)
                                    elif response_text:
                                        result = send_whatsapp_message(from_number, response_text)
                                    else:
                                        result = {"status": "skipped", "reason": "empty_response"}
                                    
                                    log(f"📊 Resultado: {result.get('status')}")
                                    return jsonify({
                                        "status": "processed",
                                        "user": from_number,
                                        "result": result
                                    }), 200
                    
                    elif "statuses" in value:
                        for status in value["statuses"]:
                            log(f"📊 Estado de mensaje: {status.get('status')} para ID: {status.get('id')}")
                        return jsonify({"status": "status_update"}), 200
            
            log("ℹ️ Webhook sin mensajes de texto para procesar")
            return jsonify({"status": "no_text_messages"}), 200
            
        except Exception as e:
            log(f"❌ Error procesando webhook: {str(e)}")
            return jsonify({"status": "error", "error": str(e)}), 500

# ========== GESTIÓN DE CITAS ==========
def cargar_citas():
    """Carga las citas existentes desde el archivo JSON"""
    try:
        if os.path.exists(CITAS_FILE):
            with open(CITAS_FILE, 'r', encoding='utf-8') as f:
                citas = json.load(f)
                for cita in citas:
                    if 'telefono' not in cita and 'user_id' in cita:
                        cita['telefono'] = cita['user_id']
                    if 'notas' not in cita:
                        cita['notas'] = 'Sin notas'
                return citas
        return []
    except Exception as e:
        log(f"❌ Error cargando citas: {e}")
        return []

def guardar_citas(citas):
    """Guarda las citas en el archivo JSON"""
    try:
        with open(CITAS_FILE, 'w', encoding='utf-8') as f:
            json.dump(citas, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        log(f"❌ Error guardando citas: {e}")
        return False


def buscar_cita_activa_usuario(user_id):
    """Busca la cita más próxima y activa de un usuario"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor()
        
        # Buscar cita pendiente para mañana o hoy
        cursor.execute("""
            SELECT id, nombre, fecha_cita, hora_cita, propiedad_id, estado, notas, telefono
            FROM citas
            WHERE (telefono = %s OR user_id = %s)
            AND estado = 'pendiente'
            AND fecha_cita >= CURRENT_DATE
            ORDER BY fecha_cita ASC, hora_cita ASC
            LIMIT 1
        """, (user_id, user_id))
        
        res = cursor.fetchone()
        if res:
            return {
                'id': res[0],
                'nombre': res[1],
                'fecha': res[2].strftime("%Y-%m-%d"),
                'hora': res[3],
                'propiedad_id': res[4],
                'estado': res[5],
                'notas': res[6],
                'telefono': res[7]
            }
        return None
    except Exception as e:
        log(f"❌ Error buscando cita activa: {e}", "ERROR")
        return None
    finally:
        if conn: conn.close()

def actualizar_cita_db(cita_id, nuevo_estado=None, nuevas_notas=None):
    """Actualiza estado y/o notas de una cita en PostgreSQL y JSON"""
    conn = None
    try:
        # 1. Actualizar PostgreSQL
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            if nuevo_estado and nuevas_notas:
                cursor.execute("UPDATE citas SET estado = %s, notas = %s WHERE id = %s", (nuevo_estado, nuevas_notas, cita_id))
            elif nuevo_estado:
                cursor.execute("UPDATE citas SET estado = %s WHERE id = %s", (nuevo_estado, cita_id))
            elif nuevas_notas:
                cursor.execute("UPDATE citas SET notas = %s WHERE id = %s", (nuevas_notas, cita_id))
            conn.commit()
            log(f"✅ Cita {cita_id} actualizada en PostgreSQL")
        
        # 2. Actualizar JSON (para mantener sincronía)
        citas = cargar_citas()
        for c in citas:
            # Los IDs en JSON son strings como cita_0001, en DB son seriales
            # Hacemos una comparación flexible o buscamos por otros campos
            # Por ahora, si el ID coincide (convertido a string)
            if str(c.get('id')) == str(cita_id) or c.get('id') == cita_id:
                if nuevo_estado: c['estado'] = nuevo_estado
                if nuevas_notas: c['notas'] = nuevas_notas
                c['ultima_actualizacion'] = datetime.now().isoformat()
                break
        guardar_citas(citas)
        return True
    except Exception as e:
        log(f"❌ Error actualizando cita: {e}", "ERROR")
        return False
    finally:
        if conn: conn.close()

def manejar_confirmacion_recordatorio(text, estado_usuario, user_id):
    """Maneja la respuesta del usuario al recordatorio de cita"""
    text = text.strip()
    
    # Intentar extraer ID de la cita del mensaje
    import re
    match = re.search(r'(CONFIRMAR|CANCELAR|REPROGRAMAR)[-\s]*(\d+)', text.upper())
    
    if match:
        comando = match.group(1)
        cita_id = int(match.group(2))
        log(f"🔍 Respuesta con ID específico: {comando} para cita {cita_id}")
        cita = buscar_cita_por_id(cita_id)
    else:
        # Tipeo simple: CONFIRMAR, CANCELAR, REPROGRAMAR
        text_upper = text.upper()
        if text_upper in ["CONFIRMAR", "CANCELAR", "REPROGRAMAR"]:
            comando = text_upper
            # Prioridad: usar el ID guardado en el estado al enviar el recordatorio
            cita_id = estado_usuario.get('ultimo_recordatorio_cita_id')
            if cita_id:
                log(f"🔍 Tipeo simple '{comando}', usando ID del estado: {cita_id}")
                cita = buscar_cita_por_id(cita_id)
            else:
                log(f"⚠️ Tipeo simple '{comando}' sin ID en estado, buscando cita activa...")
                cita = buscar_cita_activa_usuario(user_id)
        else:
            # Fallback total: palabras clave sueltas
            log("⚠️ Respuesta no estructurada, buscando cita activa por keywords...")
            cita = buscar_cita_activa_usuario(user_id)
            if cita:
                if any(word in text.lower() for word in ["confirm", "si", "sí", "voy", "dale", "ok"]):
                    comando = "CONFIRMAR"
                elif any(word in text.lower() for word in ["cancel", "no voy", "baja"]):
                    comando = "CANCELAR"
                elif any(word in text.lower() for word in ["reprogramar", "cambiar", "otro dia"]):
                    comando = "REPROGRAMAR"
                else:
                    comando = "DESCONOCIDO"
            else:
                comando = "DESCONOCIDO"
    
    if cita:
        cita_id = cita['id']
    
    if not cita:
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "No encontré una cita pendiente para vos. ¿En qué puedo ayudarte? Envía 'Hola' para ver el menú."

    # Procesar según el comando
    if comando == "CONFIRMAR":
        actualizar_cita_db(cita_id, nuevo_estado='confirmada', nuevas_notas="Usuario confirmó la visita")
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        notificar_agente(f"✅ *CITA CONFIRMADA*\n👤 {cita['nombre']}\n📅 {cita['fecha']} {cita['hora']}")
        
        return f"✅ ¡Muchas gracias, *{cita['nombre']}*! Hemos registrado tu confirmación. Nos vemos el {datetime.strptime(cita['fecha'], '%Y-%m-%d').strftime('%d/%m')} a las {cita['hora']} hs. 👋"

    elif comando == "CANCELAR":
        actualizar_cita_db(cita_id, nuevo_estado='cancelada', nuevas_notas="Usuario canceló la visita")
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        notificar_agente(f"❌ *CITA CANCELADA*\n👤 {cita['nombre']}\n📅 {cita['fecha']} {cita['hora']}")
        
        return "Entiendo. Hemos cancelado la visita. Si en otro momento deseas agendar nuevamente, no dudes en avisarnos. ¡Que tengas un buen día! 🏠"

    elif comando == "REPROGRAMAR":
        estado_usuario['paso'] = 'solicitar_fecha_cita'
        estado_usuario['cita_reprogramando_id'] = cita_id  # Guardar qué cita se reprograma
        props = cargar_propiedades_cached()
        for i, p in enumerate(props, 1):
            if p.get('id_temporal') == cita['propiedad_id']:
                estado_usuario['ultimo_indice_preguntado'] = i
                estado_usuario['propiedades_filtradas'] = props
                break
        
        actualizar_cita_db(cita_id, nuevas_notas=f"Usuario solicitó reprogramar")
        actualizar_estado_usuario(user_id, estado_usuario)
        
        notificar_agente(f"🔄 *SOLICITUD DE REPROGRAMACIÓN*\n👤 {cita['nombre']}\n📅 Original: {cita['fecha']} {cita['hora']}")
        
        return "No hay problema, podemos reprogramarla. 😊 ¿Para qué día y horario te quedaría mejor? (ej: 'El jueves a las 11')"

    else:
        return "Por favor, respondé con *CONFIRMAR*, *CANCELAR* o *REPROGRAMAR* para gestionar tu cita."

def buscar_cita_por_id(cita_id):
    """Busca una cita específica por su ID"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, fecha_cita, hora_cita, propiedad_id, estado, notas, telefono
            FROM citas
            WHERE id = %s
        """, (cita_id,))
        
        res = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if res:
            return {
                'id': res[0],
                'nombre': res[1],
                'fecha': res[2].strftime('%Y-%m-%d') if hasattr(res[2], 'strftime') else res[2],
                'hora': res[3],
                'propiedad_id': res[4],
                'estado': res[5],
                'notas': res[6],
                'telefono': res[7]
            }
        return None
        
    except Exception as e:
        log(f"❌ Error buscando cita por ID {cita_id}: {e}")
        return None


def notificar_cita_admin(cita):
    """Envía notificación de nueva cita al admin"""
    try:
        # Formatear fecha para el mensaje (DD-MM-AAAA)
        fecha_obj = datetime.strptime(cita['fecha'], "%Y-%m-%d")
        fecha_msg = fecha_obj.strftime("%d-%m-%Y")
        
        mensaje = f"📅 *NUEVA CITA AGENDADA*\n\n"
        mensaje += f"👤 *Cliente:* {cita['nombre']}\n"
        mensaje += f"📞 *Teléfono:* +{cita['telefono']}\n"
        mensaje += f"📅 *Fecha:* {fecha_msg}\n"
        mensaje += f"⏰ *Hora:* {cita['hora']}\n"
        mensaje += f"🏠 *Propiedad ID:* {cita['propiedad_id']}\n"
        mensaje += f"🆔 *ID Cita:* {cita['id']}\n"
        mensaje += f"📝 *Notas:* {cita.get('notas', 'Sin notas')}\n\n"
        mensaje += f"📍 *Estado:* {cita['estado'].upper()}"
        
        return send_whatsapp_message(ADMIN_NUMBER, mensaje)
    except Exception as e:
        log(f"❌ Error notificando cita al admin: {e}")
        return False

def cargar_configuracion_horarios():
    """Carga la configuración de días y horarios"""
    try:
        if os.path.exists(HORARIOS_FILE):
            with open(HORARIOS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        log(f"❌ Error cargando {HORARIOS_FILE}: {e}")
    
    # Configuración por defecto si falla la carga
    return {
        "configuracion_global": {
            "dias_habiles": [0, 1, 2, 3, 4], # Lunes a Viernes
            "horarios": CITAS_DISPONIBLES
        },
        "propiedades": {}
    }

def obtener_horarios_disponibles(fecha_str, propiedad_id=None):
    """Obtiene horarios disponibles para una fecha específica y propiedad"""
    try:
        fecha_deseada = datetime.strptime(fecha_str, "%Y-%m-%d")
        dia_semana = fecha_deseada.weekday() # 0=Lunes, 6=Domingo
        
        # 1. Cargar configuración
        config = cargar_configuracion_horarios()
        global_config = config.get("configuracion_global", {})
        propiedades_config = config.get("propiedades", {})
        
        # 2. Determinar configuración a usar (Específica > Global)
        horarios_base = global_config.get("horarios", CITAS_DISPONIBLES)
        dias_habiles = global_config.get("dias_habiles", [0, 1, 2, 3, 4])
        
        if propiedad_id and propiedad_id in propiedades_config:
            prop_config = propiedades_config[propiedad_id]
            if "horarios" in prop_config:
                horarios_base = prop_config["horarios"]
            if "dias_habiles" in prop_config:
                dias_habiles = prop_config["dias_habiles"]
            log(f"📅 Usando configuración específica para propiedad {propiedad_id}")
        
        # 3. Verificar si el día es válido
        if dia_semana not in dias_habiles:
            log(f"📅 El día {fecha_str} (weekday {dia_semana}) no es hábil para esta propiedad.")
            return []
            
        # 4. Filtrar horarios ocupados
        citas = cargar_citas()
        horarios_ocupados = []
        
        for cita in citas:
            # Chequear fecha
            if cita['fecha'] == fecha_str and cita['estado'] in ['pendiente', 'confirmada']:
                # Si es para la MISMA propiedad, bloquea el horario
                # O si es el MISMO agente (asumiendo 1 agente global por ahora), bloquea el horario
                # Por ahora bloqueamos globalmente para evitar doble booking del agente
                horarios_ocupados.append(cita['hora'])
        
        horarios_disponibles = [hora for hora in horarios_base if hora not in horarios_ocupados]
        
        log(f"📅 Horarios disponibles para {fecha_str} (Prop: {propiedad_id}): {len(horarios_disponibles)}/{len(horarios_base)}")
        return horarios_disponibles
    except Exception as e:
        log(f"❌ Error obteniendo horarios disponibles: {e}")
        return CITAS_DISPONIBLES

def obtener_texto_horarios(propiedad_id=None):
    """Obtiene un texto descriptivo del rango de horarios para una propiedad"""
    try:
        config = cargar_configuracion_horarios()
        global_config = config.get("configuracion_global", {})
        propiedades_config = config.get("propiedades", {})
        
        horarios = global_config.get("horarios", CITAS_DISPONIBLES)
        
        if propiedad_id and propiedad_id in propiedades_config:
            prop_config = propiedades_config[propiedad_id]
            if "horarios" in prop_config:
                horarios = prop_config["horarios"]
        
        if not horarios:
            return "Consultar disponibilidad"
            
        horarios_ordenados = sorted(horarios)
        
        # Si son pocos horarios, listarlos explícitamente para mayor claridad
        # Ejemplo: "09:00 y 17:00" en lugar de "de 09:00 a 17:00"
        if len(horarios_ordenados) <= 4:
            if len(horarios_ordenados) == 1:
                return f"a las {horarios_ordenados[0]}"
            elif len(horarios_ordenados) == 2:
                return f"{horarios_ordenados[0]} y {horarios_ordenados[1]}"
            else:
                return ", ".join(horarios_ordenados[:-1]) + " y " + horarios_ordenados[-1]
        
        # Si son muchos (rango continuo o extenso), usar formato "de X a Y"
        inicio = horarios_ordenados[0]
        fin = horarios_ordenados[-1]
        
        return f"de {inicio} a {fin}"
            
    except Exception as e:
        log(f"❌ Error obteniendo texto horarios: {e}")
        return "de 9:00 a 18:30"

def obtener_texto_dias_habiles(propiedad_id=None):
    """Obtiene un texto descriptivo de los días hábiles para una propiedad"""
    try:
        config = cargar_configuracion_horarios()
        global_config = config.get("configuracion_global", {})
        propiedades_config = config.get("propiedades", {})
        
        dias_habiles = global_config.get("dias_habiles", [0, 1, 2, 3, 4])
        
        if propiedad_id and propiedad_id in propiedades_config:
            prop_config = propiedades_config[propiedad_id]
            if "dias_habiles" in prop_config:
                dias_habiles = prop_config["dias_habiles"]
        
        nombres_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dias_texto = [nombres_dias[d] for d in sorted(dias_habiles)]
        
        if len(dias_texto) == 5 and dias_habiles == [0, 1, 2, 3, 4]:
            return "Lunes a Viernes"
        elif len(dias_texto) == 7:
            return "Todos los días"
        else:
            return ", ".join(dias_texto)
            
    except Exception as e:
        log(f"❌ Error obteniendo texto días hábiles: {e}")
        return "Lunes a Viernes"

# ========== RUTAS API ==========

@app.route("/api/enviar-recordatorios-manual", methods=["POST"])
def enviar_recordatorios_manual():
    """Endpoint para activar manualmente el envío de recordatorios"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        # Ejecutar script de recordatorios en segundo plano para evitar timeout
        import subprocess
        subprocess.Popen(['python', 'recordatorio_citas.py'])
        
        return jsonify({
            "status": "success",
            "message": "Proceso de recordatorios iniciado en segundo plano."
        })
        
    except Exception as e:
        log(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500
    
    
def actualizar_ids_json():  # ← ELIMINADO 'async'
    """Actualiza el archivo JSON con los IDs reales de PostgreSQL"""
    try:
        conn = get_db_connection()
        if not conn:
            log("⚠️ No se pudo conectar a PostgreSQL")
            return
            
        cursor = conn.cursor()
        
        # Obtener todas las citas de PostgreSQL
        cursor.execute("SELECT id, telefono, fecha_cita, hora_cita FROM citas")
        citas_db = cursor.fetchall()
        
        # Cargar JSON actual
        if not os.path.exists('citas.json'):
            log("⚠️ citas.json no encontrado")
            cursor.close()
            conn.close()
            return
            
        with open('citas.json', 'r', encoding='utf-8') as f:
            citas_json = json.load(f)
        
        # Actualizar IDs
        actualizadas = 0
        for cita_json in citas_json:
            for cita_db in citas_db:
                if (cita_json.get('telefono') == cita_db[1] and 
                    cita_json.get('fecha') == cita_db[2].strftime('%Y-%m-%d') and 
                    cita_json.get('hora') == cita_db[3]):
                    cita_json['id'] = f"pg_{cita_db[0]}"
                    actualizadas += 1
                    break
        
        # Guardar JSON actualizado
        with open('citas.json', 'w', encoding='utf-8') as f:
            json.dump(citas_json, f, indent=4, ensure_ascii=False)
            
        cursor.close()
        conn.close()
        log(f"✅ IDs de PostgreSQL actualizados en citas.json ({actualizadas} citas)")
        
    except Exception as e:
        log(f"⚠️ Error actualizando IDs en JSON: {e}")

@app.route("/api/sincronizar/citas", methods=["POST"])
def sincronizar_citas_manual():
    """Sincroniza citas entre JSON y PostgreSQL"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "No se pudo conectar a PostgreSQL"}), 500
        
        cursor = conn.cursor()
        
        # Verificar si existe citas.json
        if not os.path.exists('citas.json'):
            return jsonify({"error": "Archivo citas.json no encontrado"}), 404
            
        with open('citas.json', 'r', encoding='utf-8') as f:
            citas_json = json.load(f)
        
        if not citas_json:
            return jsonify({"message": "No hay citas en JSON", "creadas": 0, "actualizadas": 0})
        
        sincronizadas = 0
        creadas = 0
        errores = []
        
        for cita in citas_json:
            try:
                # Verificar si ya existe
                cursor.execute("""
                    SELECT id FROM citas 
                    WHERE telefono = %s AND fecha_cita = %s AND hora_cita = %s
                """, (
                    cita.get('telefono'), 
                    cita.get('fecha'), 
                    cita.get('hora')
                ))
                
                if not cursor.fetchone():
                    # Insertar nueva
                    cursor.execute("""
                        INSERT INTO citas (
                            nombre, telefono, email, fecha_cita, hora_cita,
                            propiedad_id, estado, notas, fecha_creacion
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        cita.get('nombre', 'Cliente'),
                        cita.get('telefono'),
                        cita.get('email', ''),
                        cita.get('fecha'),
                        cita.get('hora'),
                        cita.get('propiedad_id', ''),
                        cita.get('estado', 'pendiente'),
                        cita.get('notas', ''),
                        cita.get('creacion', datetime.now().isoformat())
                    ))
                    creadas += 1
                else:
                    # Actualizar existente
                    cursor.execute("""
                        UPDATE citas SET 
                            estado = %s, 
                            notas = %s,
                            email = %s
                        WHERE telefono = %s AND fecha_cita = %s AND hora_cita = %s
                    """, (
                        cita.get('estado', 'pendiente'),
                        cita.get('notas', ''),
                        cita.get('email', ''),
                        cita.get('telefono'),
                        cita.get('fecha'),
                        cita.get('hora')
                    ))
                    sincronizadas += 1
                    
            except Exception as e:
                errores.append(f"Error con cita {cita.get('id', 'desconocida')}: {str(e)}")
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "Sincronización completada",
            "creadas": creadas,
            "actualizadas": sincronizadas,
            "errores": errores if errores else None
        })
        
    except Exception as e:
        log(f"❌ Error en sincronización: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500
    

@app.route("/api/citas/<int:cita_id>", methods=["DELETE"])
def eliminar_cita(cita_id):
    """Elimina una cita permanentemente"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Error conectando a la base de datos"}), 500
        
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM citas WHERE id = %s RETURNING id", (cita_id,))
        deleted = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if not deleted:
            return jsonify({"error": "Cita no encontrada"}), 404
        
        # También eliminar de JSON
        try:
            if os.path.exists('citas.json'):
                with open('citas.json', 'r', encoding='utf-8') as f:
                    citas_json = json.load(f)
                
                citas_json = [c for c in citas_json 
                             if c.get('id') != cita_id 
                             and c.get('id') != f"cita_{cita_id:04d}"
                             and c.get('id') != f"pg_{cita_id}"]
                
                with open('citas.json', 'w', encoding='utf-8') as f:
                    json.dump(citas_json, f, indent=4, ensure_ascii=False)
        except Exception as json_e:
            log(f"⚠️ Error eliminando de JSON: {json_e}")
        
        log(f"✅ Cita {cita_id} eliminada")
        return jsonify({"status": "success", "message": "Cita eliminada"})
        
    except Exception as e:
        log(f"❌ Error eliminando cita {cita_id}: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500



@app.route("/api/citas/<int:cita_id>", methods=["GET"])
def obtener_cita_por_id(cita_id):
    """Obtiene los datos de una cita específica por su ID"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Error conectando a la base de datos"}), 500
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, nombre, telefono, email, fecha_cita, hora_cita,
                propiedad_id, estado, notas
            FROM citas 
            WHERE id = %s
        """, (cita_id,))
        
        cita = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not cita:
            return jsonify({"error": "Cita no encontrada"}), 404
        
        # Formatear respuesta
        return jsonify({
            "id": cita[0],
            "nombre": cita[1],
            "telefono": cita[2],
            "email": cita[3] or "",
            "fecha": cita[4].strftime('%Y-%m-%d') if cita[4] else None,
            "hora": cita[5],
            "propiedad_id": cita[6] or "",
            "estado": cita[7] or "pendiente",
            "notas": cita[8] or ""
        })
        
    except Exception as e:
        log(f"❌ Error obteniendo cita {cita_id}: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route("/api/citas/<int:cita_id>", methods=["PUT"])
def actualizar_cita(cita_id):
    """Actualiza los datos de una cita"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Error conectando a la base de datos"}), 500
        
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE citas 
            SET nombre = %s, email = %s, fecha_cita = %s, 
                hora_cita = %s, notas = %s, estado = %s
            WHERE id = %s
        """, (
            data.get('nombre'),
            data.get('email'),
            data.get('fecha'),
            data.get('hora'),
            data.get('notas'),
            data.get('estado', 'pendiente'),
            cita_id
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Cita actualizada"})
        
    except Exception as e:
        log(f"❌ Error actualizando cita {cita_id}: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route("/api/citas/<int:cita_id>/estado", methods=["PUT"])
def cambiar_estado_cita(cita_id):
    """Cambia el estado de una cita (pendiente, confirmada, cancelada, completada)"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    nuevo_estado = request.args.get('estado')
    if not nuevo_estado or nuevo_estado not in ['pendiente', 'confirmada', 'completada', 'cancelada']:
        return jsonify({"error": "Estado inválido"}), 400
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Error conectando a la base de datos"}), 500
        
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE citas 
            SET estado = %s
            WHERE id = %s
            RETURNING id, nombre, estado
        """, (nuevo_estado, cita_id))
        
        updated = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if not updated:
            return jsonify({"error": "Cita no encontrada"}), 404
        
        # También actualizar en JSON si existe
        try:
            if os.path.exists('citas.json'):
                with open('citas.json', 'r', encoding='utf-8') as f:
                    citas_json = json.load(f)
                
                for c in citas_json:
                    if c.get('id') == cita_id or c.get('id') == f"cita_{cita_id:04d}" or c.get('id') == f"pg_{cita_id}":
                        c['estado'] = nuevo_estado
                        c['ultima_actualizacion'] = datetime.now().isoformat()
                        break
                
                with open('citas.json', 'w', encoding='utf-8') as f:
                    json.dump(citas_json, f, indent=4, ensure_ascii=False)
        except Exception as json_e:
            log(f"⚠️ Error actualizando JSON: {json_e}")
        
        log(f"✅ Estado de cita {cita_id} cambiado a {nuevo_estado}")
        
        return jsonify({
            "status": "success",
            "message": f"Estado cambiado a {nuevo_estado}",
            "cita": {
                "id": updated[0],
                "nombre": updated[1],
                "estado": updated[2]
            }
        })
        
    except Exception as e:
        log(f"❌ Error cambiando estado de cita {cita_id}: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route("/admin")
def admin_panel():
    """Sirve el panel de administración con mejor manejo de errores"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return "⚠️ Acceso No Autorizado. Por favor usa el enlace seguro.", 403
    
    # Intentar diferentes rutas posibles
    possible_paths = [
        'admin.html',
        './admin.html',
        '/opt/render/project/src/admin.html',
        os.path.join(os.getcwd(), 'admin.html')
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                return send_file(path)
            except Exception as e:
                log(f"❌ Error enviando archivo {path}: {e}")
                continue
    
    # Si no se encuentra, mostrar información de debug
    import glob
    all_html = glob.glob('*.html')
    
    return jsonify({
        "error": "Archivo admin.html no encontrado",
        "current_directory": os.getcwd(),
        "files_in_directory": os.listdir('.'),
        "html_files_found": all_html,
        "possible_paths_tried": possible_paths
    }), 404

@app.route("/api/leads", methods=["GET"])
def api_leads():
    """Retorna todos los leads desde PostgreSQL"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, fecha, telefono, nombre, propiedad_id, propiedad_titulo, accion, detalles
            FROM leads 
            ORDER BY fecha DESC
            LIMIT 1000
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
                "detalle": lead[7]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({"leads": leads_formateados})
        
    except Exception as e:
        log(f"❌ Error en api_leads: {e}", "ERROR")
        return jsonify({"error": str(e), "leads": []}), 500



@app.route("/imgs/<path:filename>")
def serve_image(filename):
    """Sirve imágenes desde la carpeta imgs"""
    try:
        return send_from_directory('imgs', filename)
    except Exception as e:
        log(f"🔥 Error sirviendo imagen {filename}: {e}")
        return "Imagen no encontrada", 404

# ========== RUTAS DE PRUEBA ==========
@app.route("/test", methods=["GET"])
def test_send():
    """Endpoint de prueba manual"""
    test_number = "5491151511579"
    test_message = "✅ ¡Hola! Este es un mensaje de prueba desde el bot inmobiliario."
    
    result = send_whatsapp_message(test_number, test_message)
    
    return jsonify({
        "test": "completed",
        "timestamp": datetime.now().isoformat(),
        "number": test_number,
        "message": test_message,
        "result": result
    })

@app.route("/test-propiedades", methods=["GET"])
def test_propiedades():
    """Prueba la carga de propiedades"""
    propiedades = cargar_propiedades_cached()
    
    venta_count = len([p for p in propiedades if p.get('operacion') == 'venta'])
    alquiler_count = len([p for p in propiedades if p.get('operacion') == 'alquiler'])
    
    return jsonify({
        "test": "propiedades_loaded",
        "total_propiedades": len(propiedades),
        "venta_count": venta_count,
        "alquiler_count": alquiler_count,
        "archivo": PROPIEDADES_FILE,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de salud"""
    token_valid, _ = check_token_validity()
    propiedades = cargar_propiedades_cached()
    
    return jsonify({
        "status": "healthy" if token_valid else "unhealthy_token",
        "service": "whatsapp-bot-inmobiliario",
        "version": "2.2",
        "timestamp": datetime.now().isoformat(),
        "token_valid": token_valid,
        "propiedades_cargadas": len(propiedades),
        "venta_count": len([p for p in propiedades if p.get('operacion') == 'venta']),
        "alquiler_count": len([p for p in propiedades if p.get('operacion') == 'alquiler'])
    })


def debug_postgresql():
    """Debug detallado de PostgreSQL"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        log("🔍 DEBUG: Conectado a PostgreSQL...")
        cursor = conn.cursor()
        
        # Verificar tablas
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        tablas = cursor.fetchall()
        log(f"📊 DEBUG: Tablas en PostgreSQL: {[t[0] for t in tablas]}")
        
        # Verificar estructura de tabla leads
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'leads'
        """)
        
        columnas = cursor.fetchall()
        log(f"📊 DEBUG: Columnas en tabla 'leads': {columnas}")
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM leads")
        total = cursor.fetchone()[0]
        log(f"📊 DEBUG: Total leads en PostgreSQL: {total}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        log(f"❌ DEBUG ERROR PostgreSQL: {e}")
        import traceback
        log(f"🔍 DEBUG TRACEBACK: {traceback.format_exc()}")
        return False





def probar_conexion_postgresql():
    """Probar conexión a PostgreSQL"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
            
        # Asegurar esquema al inicio
        init_db(conn)
        
        cursor = conn.cursor()
        
        # Verificar si la tabla leads existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'leads'
            )
        """)
        
        tabla_existe = cursor.fetchone()[0]
        
        if tabla_existe:
            cursor.execute("SELECT COUNT(*) FROM leads")
            total_leads = cursor.fetchone()[0]
            log(f"✅ PostgreSQL: Tabla 'leads' existe con {total_leads} registros")
        else:
            log("⚠️ PostgreSQL: Tabla 'leads' NO existe")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        log(f"❌ Error conectando a PostgreSQL: {e}")
        return False


@app.route("/test-pg-now", methods=["GET"])
def test_pg_now():
    """Probar PostgreSQL inmediatamente"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"status": "error", "message": "No se pudo conectar"}), 500
            
        cursor = conn.cursor()
        
        # Insertar registro de prueba
        cursor.execute("""
            INSERT INTO leads (telefono, nombre, accion, detalles)
            VALUES ('test_5491151511579', 'TEST INMEDIATO', 'test_inmediato', 'Prueba desde endpoint /test-pg-now')
            RETURNING id, fecha
        """)
        
        result = cursor.fetchone()
        lead_id = result[0]
        fecha = result[1]
        
        conn.commit()
        
        # Contar total
        cursor.execute("SELECT COUNT(*) FROM leads")
        total = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "✅ PostgreSQL funcionando correctamente",
            "lead_id": lead_id,
            "fecha": fecha.isoformat(),
            "total_leads": total,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ PostgreSQL error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route("/debug/leads", methods=["GET"])
def debug_leads():
    """Depurar leads"""
    leads_json = []
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, 'r', encoding='utf-8') as f:
            leads_json = json.load(f)
    
    # Probar conexión PostgreSQL
    try:
        conn = get_db_connection()
        if not conn:
            total_pg = "Error de conexión"
        else:
            cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM leads")
        total_pg = cursor.fetchone()[0]
        cursor.close()
        conn.close()
    except Exception as e:
        total_pg = f"Error: {str(e)}"
    
    return jsonify({
        "leads_json": len(leads_json),
        "leads_postgresql": total_pg,
        "ultimo_lead": leads_json[-1] if leads_json else None,
        "archivo": os.path.exists(LEADS_FILE)
    })


@app.route("/api/internal/send-reminder", methods=["POST"])
@app.route("/api/internal/send-reminder", methods=["POST"])
def send_appointment_reminder():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        user_id = data.get('user_id')
        nombre = data.get('nombre', 'Cliente')
        fecha = data.get('fecha')
        hora = data.get('hora')
        propiedad = data.get('propiedad', 'la propiedad')
        cita_id = data.get('cita_id')  # ← NUEVO: recibir el ID de la cita
        
        # Validar campos
        missing = []
        if not user_id:
            missing.append('user_id')
        if not fecha:
            missing.append('fecha')
        if not hora:
            missing.append('hora')
        if not cita_id:
            missing.append('cita_id')  # ← NUEVO: validar ID
            
        if missing:
            return jsonify({"error": "Missing fields", "missing": missing}), 400
        
        # Formatear mensaje con el ID de la cita
        mensaje = f"""🔔 *RECORDATORIO DANTE PROPIEDADES*

Hola *{nombre}*! 😊

Te escribo para recordarte tu cita de mañana:

📅 *Fecha:* {fecha}
⏰ *Hora:* {hora} hs
🏠 *Propiedad:* {propiedad}

📍 Te esperamos. Para responder, escribí:

✅ *CONFIRMAR* para confirmar
❌ *CANCELAR* si no podrás asistir
🔄 *REPROGRAMAR* para cambiar fecha/hora

¡Gracias por confiar en Dante Propiedades! 🏠🗝️"""
        
        # Enviar mensaje
        result = send_whatsapp_message(user_id, mensaje)
        
        # Setear estado
        estado = obtener_estado_usuario(user_id)
        estado['paso'] = 'esperando_confirmacion_recordatorio'
        estado['ultimo_recordatorio_cita_id'] = cita_id  # ← NUEVO: guardar el ID
        actualizar_estado_usuario(user_id, estado)
        
        log(f"🔔 Recordatorio enviado a {user_id} ({nombre}) para cita {cita_id}")
        return jsonify({
            "status": "success",
            "whatsapp_id": result.get('message_id')
        }), 200
        
    except Exception as e:
        log(f"❌ Error inesperado: {e}")
        return jsonify({"error": str(e)}), 500
    
    

# 🔥 NUEVOS ENDPOINTS PARA DIAGNÓSTICO
@app.route("/version-actual", methods=["GET"])
def version_actual():
    """Muestra la versión actual del bot"""
    return """
    <h1>✅ VERSIÓN CORRECTA - BOT INMOBILIARIO COMPLETO</h1>
    <p>Este es el código completo con sistema de citas, propiedades y PostgreSQL</p>
    <p><a href="/">Volver al inicio</a></p>
    <p><a href="/token-status">Verificar token</a></p>
    <p><a href="/debug-token-env">Debug variables</a></p>
    """

@app.route("/token-status", methods=["GET"])
def token_status():
    """Verifica el estado del token"""
    token_valid, token_info = check_token_validity()
    
    if token_valid:
        return jsonify({
            "valid": True,
            "status": 200,
            "name": token_info.get('verified_name', 'N/A'),
            "number": token_info.get('display_phone_number', 'N/A')
        })
    else:
        return jsonify({
            "valid": False,
            "error": "Token inválido o expirado",
            "details": token_info
        }), 401

@app.route("/debug-token-env", methods=["GET"])
def debug_token_env():
    """Muestra información de la variable de entorno del token"""
    token_from_env = os.environ.get("WHATSAPP_TOKEN", "NO_ENV_VAR")
    token_from_code = ACCESS_TOKEN
    
    return jsonify({
        "env_var_exists": "WHATSAPP_TOKEN" in os.environ,
        "token_from_env_preview": token_from_env[:20] + "..." if len(token_from_env) > 20 else token_from_env,
        "token_from_code_preview": token_from_code[:20] + "...",
        "tokens_match": token_from_env == token_from_code if token_from_env != "NO_ENV_VAR" else False,
        "environment_keys": list(os.environ.keys())
    })

@app.route("/check-code", methods=["GET"])
def check_code():
    """Verifica que el código es la versión correcta"""
    return "✅ CÓDIGO CORRECTO - Versión completa con sistema de citas"

@app.route("/test-envio", methods=["GET"])
def test_envio_simple():
    """Endpoint ultra simple para probar envío directo"""
    try:
        numero = "5411515151579"  # Formato directo sin 9
        mensaje = "🔔 PRUEBA DIRECTA - BOT INMOBILIARIO COMPLETO"
        
        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "text",
            "text": {"body": mensaje}
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        return jsonify({
            "status_code": response.status_code,
            "respuesta": response.json(),
            "token_usado": ACCESS_TOKEN[:30] + "..."
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# MAIN

@app.route("/debug-version", methods=["GET"])
def debug_version():
    """Muestra información de la versión del código"""
    import hashlib
    import os
    
    # Hash del archivo actual
    with open(__file__, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()[:8]
    
    # Verificar si existen los endpoints
    endpoints = {
        "version-actual": "version_actual" in dir(),
        "token-status": "token_status" in dir(),
        "debug-token-env": "debug_token_env" in dir(),
        "test-envio": "test_envio_simple" in dir()
    }
    
    # Última modificación del archivo
    mod_time = os.path.getmtime(__file__)
    mod_date = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        "status": "debug",
        "file_hash": file_hash,
        "last_modified": mod_date,
        "endpoints_presentes": endpoints,
        "python_version": os.environ.get('PYTHON_VERSION', 'unknown'),
        "render_deploy": os.environ.get('RENDER_DEPLOY', 'unknown')
    })

@app.route("/debug-python", methods=["GET"])
def debug_python():
    """Muestra la versión de Python que está usando Render"""
    import sys
    import platform
    
    return jsonify({
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "python_compiler": platform.python_compiler(),
        "runtime_txt_content": open('runtime.txt').read().strip() if os.path.exists('runtime.txt') else 'No existe',
        "timestamp": datetime.now().isoformat()
    })

@app.route("/debug-db", methods=["GET"])
def debug_db():
    """Diagnóstico detallado de la conexión a PostgreSQL"""
    import psycopg2
    import os
    
    resultados = {
        "variable_db_url": "NO CONFIGURADA",
        "intento_conexion": False,
        "error_detalle": None,
        "timestamp": datetime.now().isoformat()
    }
    
    # 1. Verificar variable de entorno
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        resultados["variable_db_url"] = "CONFIGURADA (oculta)"
        # Mostrar solo los primeros caracteres por seguridad
        resultados["db_url_preview"] = db_url[:30] + "..." + db_url[-10:]
    else:
        resultados["variable_db_url"] = "NO EXISTE"
        return jsonify(resultados)
    
    # 2. Intentar conexión
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Probar consulta simple
        cursor.execute("SELECT 1")
        resultado = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        resultados["intento_conexion"] = True
        resultados["consulta_prueba"] = resultado[0] == 1
        resultados["mensaje"] = "✅ Conexión exitosa"
        
    except Exception as e:
        resultados["intento_conexion"] = False
        resultados["error_detalle"] = str(e)
        resultados["tipo_error"] = type(e).__name__
    
    return jsonify(resultados)




@app.route("/api/citas", methods=["GET"])
def api_citas():
    """Retorna todas las citas desde PostgreSQL"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "No se pudo conectar a la base de datos", "citas": []}), 500
        
        cursor = conn.cursor()
        
        # Verificar si la tabla citas existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'citas'
            )
        """)
        tabla_existe = cursor.fetchone()[0]
        
        if not tabla_existe:
            cursor.close()
            conn.close()
            return jsonify({"error": "La tabla 'citas' no existe", "citas": []}), 200
        
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
            try:
                fecha_str = cita[3].strftime('%Y-%m-%d') if cita[3] else None
            except:
                fecha_str = str(cita[3]) if cita[3] else None
                
            citas_formateadas.append({
                "id": cita[0],
                "nombre": cita[1] or "Sin nombre",
                "telefono": cita[2] or "",
                "fecha": fecha_str,
                "hora": cita[4] or "",
                "propiedad_id": cita[5] or "",
                "propiedad_titulo": "Propiedad",
                "estado": cita[6] or "pendiente",
                "notas": cita[7] or "",
                "fecha_creacion": cita[8].isoformat() if cita[8] else None,
                "email": cita[9] or ""
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(citas_formateadas)
        
    except Exception as e:
        log(f"❌ Error en api_citas: {e}", "ERROR")
        return jsonify({"error": str(e), "citas": []}), 500
    
    
    
@app.route("/api/db-status", methods=["GET"])
def db_status():
    """Verifica el estado de la conexión a PostgreSQL"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    status = {
        "database_url_configured": bool(os.getenv("DATABASE_URL")),
        "connection_test": False,
        "tables": {},
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        conn = get_db_connection()
        if conn:
            status["connection_test"] = True
            cursor = conn.cursor()
            
            # Verificar tablas
            cursor.execute("""
                SELECT table_name, 
                       (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            for table in cursor.fetchall():
                # Contar registros
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                status["tables"][table[0]] = {
                    "columns": table[1],
                    "rows": count
                }
            
            cursor.close()
            conn.close()
            status["message"] = "✅ Conexión exitosa"
        else:
            status["message"] = "❌ No se pudo conectar"
            
    except Exception as e:
        status["error"] = str(e)
        status["message"] = "❌ Error en la conexión"
    
    return jsonify(status)


@app.route("/api/propiedades", methods=["GET"])
def api_propiedades():
    """Retorna la lista de propiedades para el buscador del panel admin"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        if os.path.exists("propiedades.json"):
            with open("propiedades.json", 'r', encoding='utf-8') as f:
                propiedades = json.load(f)
            
            # Solo enviar los campos necesarios para el buscador
            propiedades_simplificadas = []
            for p in propiedades:
                propiedades_simplificadas.append({
                    "id": p.get("id_temporal"),
                    "titulo": p.get("titulo"),
                    "direccion": p.get("direccion"),
                    "tipo": p.get("tipo"),
                    "operacion": p.get("operacion")
                })
            
            return jsonify(propiedades_simplificadas)
        else:
            return jsonify([])
            
    except Exception as e:
        log(f"❌ Error en api_propiedades: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500

@app.route("/api/config/horarios", methods=["GET"])
def api_config_horarios():
    """Obtiene la configuración de horarios"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        if os.path.exists("dias-horarios-visitas.json"):
            with open("dias-horarios-visitas.json", 'r', encoding='utf-8') as f:
                config = json.load(f)
            return jsonify(config)
        else:
            # Configuración por defecto
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
        log(f"❌ Error en api_config_horarios: {e}", "ERROR")
        return jsonify({"error": str(e)}), 500


@app.route("/api/diagnostico-citas", methods=["GET"])
def diagnostico_citas():
    """Endpoint para diagnosticar citas para mañana"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        manana = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT 
                id, nombre, telefono, fecha_cita, hora_cita,
                estado, recordatorio_enviado, recordatorio_enviado_en
            FROM citas 
            WHERE fecha_cita = %s
            ORDER BY id
        """, (manana,))
        
        citas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({
            "fecha": manana,
            "total_citas": len(citas),
            "citas": [{
                "id": c[0],
                "nombre": c[1],
                "telefono": c[2],
                "fecha": str(c[3]),
                "hora": c[4],
                "estado": c[5],
                "recordatorio_enviado": c[6],
                "recordatorio_enviado_en": str(c[7]) if c[7] else None
            } for c in citas]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/db-check", methods=["GET"])
def db_check():
    """Verificación rápida de la base de datos"""
    key = request.args.get('key')
    if key != ADMIN_ACCESS_KEY:
        return jsonify({"error": "Unauthorized"}), 403
    
    results = {}
    
    # Verificar variables de entorno
    results["database_url_exists"] = bool(os.getenv("DATABASE_URL"))
    
    # Intentar conexión
    try:
        conn = get_db_connection()
        results["connection_success"] = conn is not None
        
        if conn:
            cursor = conn.cursor()
            
            # Listar tablas
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [t[0] for t in cursor.fetchall()]
            results["tables"] = tables
            
            # Contar registros en citas
            if 'citas' in tables:
                cursor.execute("SELECT COUNT(*) FROM citas")
                results["citas_count"] = cursor.fetchone()[0]
            
            # Contar registros en leads
            if 'leads' in tables:
                cursor.execute("SELECT COUNT(*) FROM leads")
                results["leads_count"] = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            results["message"] = "✅ Conexión exitosa"
        else:
            results["message"] = "❌ No se pudo conectar"
            
    except Exception as e:
        results["error"] = str(e)
        results["message"] = "❌ Error"
    
    return jsonify(results)

@app.route("/debug-files", methods=["GET"])
def debug_files():
    """Muestra los archivos disponibles en el servidor"""
    import os
    files = os.listdir('.')
    html_files = [f for f in files if f.endswith('.html')]
    return jsonify({
        "current_directory": os.getcwd(),
        "all_files": files[:20],  # Primeros 20 archivos
        "html_files": html_files,
        "admin_html_exists": os.path.exists('admin.html'),
        "admin_html_size": os.path.getsize('admin.html') if os.path.exists('admin.html') else 0,
        "cwd": os.getcwd()
    })



if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("🏠 🏠 🏠 WHATSAPP BOT INMOBILIARIO - VERSIÓN 2.1")
    print("=" * 60)
    
    # DEBUG: Probar PostgreSQL
    print("🔍 DEBUG: Probando PostgreSQL...")
    debug_postgresql()
    
    propiedades = cargar_propiedades()
    print(f"📊 Propiedades cargadas: {len(propiedades)}")

    
    # Probar conexión a PostgreSQL
    print("🔍 Probando conexión a PostgreSQL...")
    conexion_pg = probar_conexion_postgresql()
    
    
    if propiedades:
        ventas = len([p for p in propiedades if p.get('operacion') == 'venta'])
        alquileres = len([p for p in propiedades if p.get('operacion') == 'alquiler'])
        print(f"💰 En venta: {ventas} propiedades")
        print(f"🔑 En alquiler: {alquileres} propiedades")
    
    token_valid, token_info = check_token_validity()
    if token_valid:
        print(f"✅ TOKEN VÁLIDO")
        print(f"   📞 Número: {token_info.get('display_phone_number', 'N/A')}")
        print(f"   📛 Nombre: {token_info.get('verified_name', 'N/A')}")
    else:
        print(f"❌❌❌ TOKEN INVÁLIDO O EXPIRADO ❌❌❌")
        print(f"   ⚠️  El bot NO PODRÁ ENVIAR MENSAJES")
    
    print(f"🌐 URL: https://meta-rjpb.onrender.com")
    print(f"📁 Propiedades: {PROPIEDADES_FILE}")
    print(f"📅 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if conexion_pg:
        print("✅ PostgreSQL: Conectado correctamente")
    else:
        print("⚠️ PostgreSQL: No se pudo conectar (leads solo en JSON)")
    
    print("=" * 60 + "\n")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)