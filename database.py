import os
import json
import time
import psycopg2
from datetime import datetime
from functools import lru_cache
from config import *
from utils import log, _strip_media_fields, save_json_atomic

estados_usuarios = {}

def get_db_connection(max_retries=5):
    """Obtiene conexión a PostgreSQL con reintentos para manejar errores intermitentes de SSL"""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        log("❌ DATABASE_URL no encontrada", "ERROR")
        return None

    # Sanitizar la URL de conexión
    database_url = database_url.strip()
    # Algunas configuraciones incluyen el nombre de la variable en el valor
    # Manejar: "DATABASE_URL=...", "DATABASE_URL =...", "DATABASE_URL = ..." etc.
    if database_url.upper().startswith("DATABASE_URL"):
        # Quitar "DATABASE_URL" y luego "=" y espacios
        database_url = database_url[len("DATABASE_URL"):].lstrip().lstrip("=").lstrip()
    # psycopg2 requiere "postgresql://" en vez de "postgres://"
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    log(f"🔗 DSN formato: {database_url[:30]}...")

    # Neon y Supabase suelen requerir SSL. Si no viene en la URL, lo forzamos.
    connect_params = {
        "dsn": database_url,
        "connect_timeout": 15,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "options": '-c statement_timeout=30000'
    }
    
    # Solo añadir sslmode='require' si no está explícito en la URL para evitar conflictos
    if "sslmode=" not in database_url.lower():
        connect_params["sslmode"] = "require"

    for i in range(max_retries):
        try:
            conn = psycopg2.connect(**connect_params)
            # Verificar si la conexión es funcional
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            
            if i > 0:
                log(f"✅ Conexión establecida tras {i} reintentos")
            else:
                log("✅ Conexión a PostgreSQL exitosa")
            return conn
            
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            error_str = str(e)
            if "SSL connection has been closed unexpectedly" in error_str or "connection to server at" in error_str or "Name or service not known" in error_str:
                log(f"⚠️ Error de conexión (Intento {i+1}/{max_retries}): {error_str}", "WARNING")
                if i < max_retries - 1:
                    time.sleep(2) # Esperar dos segundos antes de reintentar
                    continue
            log(f"❌ Error fatal conectando a PostgreSQL: {e}", "ERROR")
            if "Name or service not known" in error_str:
                log("💡 TIP: Si estás usando Render, asegúrate de usar la 'External Database URL' de Neon/Supabase.", "TIP")
            break
        except Exception as e:
            log(f"❌ Error inesperado conectando a PostgreSQL: {e}", "ERROR")
            break
            
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
                recordatorio_fecha_respuesta TIMESTAMP,
                
                -- Nuevas columnas para feedback
                feedback_enviado BOOLEAN DEFAULT FALSE,
                feedback_enviado_en TIMESTAMP
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
                tipo_seleccionado VARCHAR(50),
                ambientes_seleccionados INTEGER,
                ultima_accion VARCHAR(50),
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
        
        -- Nuevas columnas para feedback
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS feedback_enviado BOOLEAN DEFAULT FALSE;
        ALTER TABLE citas ADD COLUMN IF NOT EXISTS feedback_enviado_en TIMESTAMP;
        
        -- Columnas para user_states si la tabla ya existía
        ALTER TABLE user_states ADD COLUMN IF NOT EXISTS tipo_seleccionado VARCHAR(50);
        ALTER TABLE user_states ADD COLUMN IF NOT EXISTS ambientes_seleccionados INTEGER;
        ALTER TABLE user_states ADD COLUMN IF NOT EXISTS ultima_accion VARCHAR(50);
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


def obtener_estado_usuario(user_id):
    """Obtiene o crea el estado de un usuario (Cache + PostgreSQL)"""
    # 1. Guardar referencia al caché en memoria como FALLBACK
    cached_state = estados_usuarios.get(user_id)
        
    # 2. Intentar desde PostgreSQL (fuente primaria)
    conn = None
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT paso, operacion_seleccionada, propiedades_filtradas, ultimo_indice_preguntado, nombre_cliente, email_cliente, fecha_cita, hora_cita, horarios_disponibles, data, tipo_seleccionado, ambientes_seleccionados, timestamp, ultima_accion FROM user_states WHERE user_id = %s", (user_id,))
            res = cursor.fetchone()
            if res:
                # Función auxiliar para parseo seguro y profundo
                def safe_json_loads(data, default):
                    if not data: return default
                    # Si ya es un objeto (dict/list), devolverlo
                    if isinstance(data, (dict, list)): return data
                    
                    # Si es un string, intentar parsear
                    current_data = data
                    max_depth = 3 # Evitar bucles infinitos
                    for _ in range(max_depth):
                        if not isinstance(current_data, str):
                            break
                        try:
                            # Trim para ver si parece JSON
                            trimmed = current_data.strip()
                            if (trimmed.startswith('{') and trimmed.endswith('}')) or (trimmed.startswith('[') and trimmed.endswith(']')):
                                parsed = json.loads(current_data)
                                if parsed is not None:
                                    current_data = parsed
                                else:
                                    break
                            else:
                                break # No parece JSON
                        except:
                            break
                            
                    # Si al final es un dict/list, éxito. Si no, devolver default si era string basura
                    if isinstance(current_data, (dict, list)):
                        return current_data
                    return default if isinstance(data, str) and not isinstance(current_data, (dict, list)) else current_data

                row_timestamp = res[12] if len(res) > 12 else None
                estado = {
                    'paso': res[0],
                    'operacion_seleccionada': res[1],
                    'propiedades_filtradas': safe_json_loads(res[2], []),
                    'ultimo_indice_preguntado': res[3],
                    'nombre_cliente': res[4],
                    'email_cliente': res[5],
                    'fecha_cita': res[6],
                    'hora_cita': res[7],
                    'horarios_disponibles': safe_json_loads(res[8], []),
                    'data': safe_json_loads(res[9], {}),
                    'tipo_seleccionado': res[10],
                    'ambientes_seleccionados': res[11],
                    'timestamp': row_timestamp if row_timestamp else datetime.now().isoformat(),
                    'ultima_accion': res[13] if len(res) > 13 else None
                }
                
                # REPARACIÓN GLOBAL: Si la lista está vacía pero la operación es 'todas', recargarla
                # Esto soluciona que 'F' (fotos) falle después de elegir una propiedad de la lista completa
                if not estado['propiedades_filtradas'] and estado['operacion_seleccionada'] == 'todas':
                    log(f"🔄 [GLOBAL] Recargando propiedades desde cache para usuario {user_id}")
                    estado['propiedades_filtradas'] = cargar_propiedades_cached()

                if cached_state and cached_state.get('timestamp') and row_timestamp:
                    try:
                        if cached_state['timestamp'] > row_timestamp:
                            log(f"🔄 Usando estado cacheado más reciente para {user_id} (DB: {row_timestamp}, Cache: {cached_state['timestamp']})")
                            return cached_state
                    except Exception:
                        pass

                estados_usuarios[user_id] = estado
                return estado
    except Exception as e:
        log(f"⚠️ Error recuperando estado de DB: {e}")
        # FALLBACK: Si PostgreSQL falla, usar caché en memoria
        if cached_state:
            log(f"🔄 Usando estado cacheado como fallback para {user_id} (paso: {cached_state.get('paso')})")
            return cached_state
    finally:
        if conn: conn.close()
        
    # 3. Si no existe, crear nuevo
    estado_nuevo = {
        'paso': 'menu_principal',
        'operacion_seleccionada': None,
        'propiedades_filtradas': [],
        'ultimo_indice_preguntado': None,
        'tipo_seleccionado': None,
        'ambientes_seleccionados': None,
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
                    fecha_cita, hora_cita, horarios_disponibles, data, 
                    tipo_seleccionado, ambientes_seleccionados, timestamp, ultima_accion
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    tipo_seleccionado = EXCLUDED.tipo_seleccionado,
                    ambientes_seleccionados = EXCLUDED.ambientes_seleccionados,
                    timestamp = EXCLUDED.timestamp,
                    ultima_accion = EXCLUDED.ultima_accion
            """, (
                user_id, 
                nuevo_estado.get('paso'),
                nuevo_estado.get('operacion_seleccionada'),
                json.dumps(_strip_media_fields(nuevo_estado.get('propiedades_filtradas', []))) if nuevo_estado.get('operacion_seleccionada') != 'todas' else "[]",
                nuevo_estado.get('ultimo_indice_preguntado'),
                nuevo_estado.get('nombre_cliente'),
                nuevo_estado.get('email_cliente'),
                nuevo_estado.get('fecha_cita'),
                nuevo_estado.get('hora_cita'),
                json.dumps(nuevo_estado.get('horarios_disponibles', [])),
                json.dumps(nuevo_estado.get('data', {})),
                nuevo_estado.get('tipo_seleccionado'),
                nuevo_estado.get('ambientes_seleccionados'),
                nuevo_estado.get('timestamp'),
                nuevo_estado.get('ultima_accion')
            ))
            conn.commit()
            log(f"✅ Estado persistido en DB para {user_id} (paso: {nuevo_estado.get('paso')})")
    except Exception as e:
        log(f"🔥 Error persistiendo estado en DB para {user_id} (paso: {nuevo_estado.get('paso')}): {e}", "ERROR")
        import traceback
        log(f"🔍 Traceback: {traceback.format_exc()}", "ERROR")
    finally:
        if conn:
            conn.close()


def registrar_lead(user_id, propiedad_id, accion, detalle=""):
    from whatsapp_api import notificar_agente
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
            try:
                with open(LEADS_FILE, 'r', encoding='utf-8') as f:
                    leads = json.load(f)
            except Exception as e:
                log(f"⚠️ Error cargando leads existentes: {e}. Se iniciará lista nueva para evitar pérdida de datos.")
        
        nuevo_lead = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'propiedad_id': propiedad_id,
            'accion': accion,
            'detalle': detalle,
            'propiedad_nombre': nombre_propiedad
        }
        leads.append(nuevo_lead)
        
        save_json_atomic(LEADS_FILE, leads)
        
        log(f"✅ Lead registrado en JSON: {user_id} - {accion}")
        
        # 2. GUARDAR EN POSTGRESQL - FIX CRÍTICO
        log("🔄 INICIANDO GUARDADO EN POSTGRESQL...")
        
        # Obtener el nombre del usuario desde su estado
        estado_usuario = obtener_estado_usuario(user_id)
        nombre_usuario_bd = estado_usuario.get('nombre_cliente', '')
        
        # Extraer nombre del cliente si está en el detalle (prioridad alta si viene específico para esta accion)
        nombre_cliente = "Cliente WhatsApp"
        
        if nombre_usuario_bd and nombre_usuario_bd.lower() != 'ninguno':
            nombre_cliente = nombre_usuario_bd
            
        if "Nombre:" in detalle:
            try:
                nombre_partes = detalle.split("Nombre:")[1].strip()
                if " - " in nombre_partes:
                    nombre_extraido = nombre_partes.split(" - ")[0]
                else:
                    nombre_extraido = nombre_partes
                if nombre_extraido and nombre_extraido.lower() != 'ninguno':
                    nombre_cliente = nombre_extraido
            except:
                pass
                
        # Si sigue siendo genérico, intentar ponerle los últimos 4 dígitos
        if nombre_cliente == "Cliente WhatsApp" and len(str(user_id)) >= 4:
            nombre_cliente = f"Cliente {str(user_id)[-4:]}"
        
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


def cargar_citas():
    """Carga las citas existentes desde el archivo JSON"""
    try:
        if os.path.exists(CITAS_FILE):
            with open(CITAS_FILE, 'r', encoding='utf-8') as f:
                citas = json.load(f)
                if not isinstance(citas, list):
                    log(f"⚠️ Formato inválido en {CITAS_FILE}")
                    return []
                for cita in citas:
                    if 'telefono' not in cita and 'user_id' in cita:
                        cita['telefono'] = cita['user_id']
                    if 'notas' not in cita:
                        cita['notas'] = 'Sin notas'
                return citas
        return []
    except Exception as e:
        log(f"❌ Error cargando citas: {e}")
        return []  # Retorna lista vacía en caso de error


def guardar_citas(citas):
    """Guarda las citas en el archivo JSON"""
    if citas is None:
        log("⚠️ Intento de guardar citas siendo None, operación cancelada.")
        return False
    return save_json_atomic(CITAS_FILE, citas)


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
        if citas is not None:
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
        else:
            log(f"⚠️ No se actualizó JSON de citas porque falló la carga (ID {cita_id})")
        return True
    except Exception as e:
        log(f"❌ Error actualizando cita: {e}", "ERROR")
        return False
    finally:
        if conn: conn.close()


@lru_cache(maxsize=128)
def cargar_propiedades_cached():
    """Carga propiedades con caché para mejor rendimiento"""
    return cargar_propiedades()


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


