"""
Módulo de base de datos para Dante Propiedades
Maneja SQLite para propiedades e historial de conversaciones
"""
import os
import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Paths
DB_PATH = os.environ.get('DB_PATH', 'instance/dante_properties.db')
LOG_PATH = 'instance/conversations.log'

def get_db_connection():
    """Obtiene conexión a la base de datos"""
    Path(os.path.dirname(DB_PATH)).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def verificar_y_reparar_bd():
    """Verifica y repara la base de datos si es necesario"""
    print("🔍 Verificando base de datos...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si la tabla existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='propiedades'")
        if cursor.fetchone() is None:
            print("📦 Creando tablas de base de datos...")
            initialize_databases()
        else:
            print("✅ Base de datos verificada")
        
        conn.close()
    except Exception as e:
        print(f"⚠️ Error verificando BD: {e}")

def initialize_databases():
    """Inicializa todas las tablas de la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla de propiedades
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS propiedades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_temporal TEXT UNIQUE NOT NULL,
            titulo TEXT,
            barrio TEXT,
            precio REAL,
            ambientes INTEGER,
            metros_cuadrados REAL,
            descripcion TEXT,
            operacion TEXT,
            tipo TEXT,
            direccion TEXT,
            antiguedad INTEGER,
            estado TEXT,
            orientacion TEXT,
            expensas REAL,
            amenities TEXT,
            cochera TEXT,
            balcon TEXT,
            pileta TEXT,
            acepta_mascotas TEXT,
            aire_acondicionado TEXT,
            info_multimedia TEXT,
            documentos TEXT,
            videos TEXT,
            fotos TEXT,
            moneda_precio TEXT,
            moneda_expensas TEXT,
            fecha_procesamiento TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de historial de conversaciones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_conversaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canal TEXT,
            mensaje_usuario TEXT,
            respuesta_bot TEXT,
            timestamp REAL,
            response_time REAL,
            search_performed INTEGER,
            results_count INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada correctamente")

def query_properties(filters: Dict[str, Any] = None) -> List[Dict]:
    """
    Consulta propiedades con filtros opcionales
    
    Args:
        filters: Diccionario con filtros de búsqueda
        
    Returns:
        Lista de propiedades que coinciden con los filtros
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM propiedades WHERE 1=1"
    params = []
    
    if filters:
        if filters.get('barrio'):
            query += " AND LOWER(barrio) = LOWER(?)"
            params.append(filters['barrio'])
        
        if filters.get('operacion'):
            query += " AND operacion = ?"
            params.append(filters['operacion'])
        
        if filters.get('tipo'):
            query += " AND tipo = ?"
            params.append(filters['tipo'])
        
        if filters.get('min_price'):
            query += " AND precio >= ?"
            params.append(filters['min_price'])
        
        if filters.get('max_price'):
            query += " AND precio <= ?"
            params.append(filters['max_price'])
        
        if filters.get('min_rooms'):
            query += " AND ambientes >= ?"
            params.append(filters['min_rooms'])
        
        if filters.get('min_sqm'):
            query += " AND metros_cuadrados >= ?"
            params.append(filters['min_sqm'])
        
        if filters.get('id_temporal'):
            query += " AND id_temporal = ?"
            params.append(filters['id_temporal'])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Convertir a lista de diccionarios
    results = []
    for row in rows:
        prop = dict(row)
        # Parsear campos JSON
        for field in ['fotos', 'videos', 'documentos', 'amenities', 'info_multimedia']:
            if prop.get(field) and isinstance(prop[field], str):
                try:
                    prop[field] = json.loads(prop[field])
                except:
                    prop[field] = []
        results.append(prop)
    
    return results

def get_historial_canal(canal: str, limit: int = 5) -> List[str]:
    """
    Obtiene el historial reciente de conversaciones de un canal
    
    Args:
        canal: Canal de comunicación (web, whatsapp, etc.)
        limit: Número máximo de mensajes a retornar
        
    Returns:
        Lista de mensajes del historial
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT respuesta_bot FROM historial_conversaciones
        WHERE canal = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (canal, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [row['respuesta_bot'] for row in rows]

def get_last_bot_response(canal: str) -> Optional[str]:
    """
    Obtiene la última respuesta del bot para un canal
    
    Args:
        canal: Canal de comunicación
        
    Returns:
        Último mensaje del bot o None
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT respuesta_bot FROM historial_conversaciones
        WHERE canal = ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (canal,))
    
    row = cursor.fetchone()
    conn.close()
    
    return row['respuesta_bot'] if row else None

def log_conversation(
    user_message: str,
    bot_response: str,
    canal: str,
    response_time: float,
    search_performed: bool,
    results_count: int
):
    """
    Registra una conversación en el historial
    
    Args:
        user_message: Mensaje del usuario
        bot_response: Respuesta del bot
        canal: Canal de comunicación
        response_time: Tiempo de respuesta
        search_performed: Si se realizó búsqueda
        results_count: Cantidad de resultados
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO historial_conversaciones
            (canal, mensaje_usuario, respuesta_bot, timestamp, response_time, search_performed, results_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            canal,
            user_message[:1000],  # Limitar largo del mensaje
            bot_response[:5000],  # Limitar largo de respuesta
            time.time(),
            response_time,
            1 if search_performed else 0,
            results_count
        ))
        
        conn.commit()
    except Exception as e:
        print(f"Error guardando conversación: {e}")
    finally:
        conn.close()

def add_property(propiedad: Dict) -> bool:
    """
    Agrega una propiedad a la base de datos
    
    Args:
        propiedad: Diccionario con datos de la propiedad
        
    Returns:
        True si se agregó correctamente
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Serializar campos JSON
        json_fields = ['fotos', 'videos', 'documentos', 'amenities', 'info_multimedia']
        for field in json_fields:
            if field in propiedad and isinstance(propiedad[field], list):
                propiedad[field] = json.dumps(propiedad[field], ensure_ascii=False)
        
        cursor.execute('''
            INSERT OR REPLACE INTO propiedades
            (id_temporal, titulo, barrio, precio, ambientes, metros_cuadrados, descripcion,
             operacion, tipo, direccion, antiguedad, estado, orientacion, expensas,
             amenities, cochera, balcon, pileta, acepta_mascotas, aire_acondicionado,
             info_multimedia, documentos, videos, fotos, moneda_precio, moneda_expensas, fecha_procesamiento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            propiedad.get('id_temporal'),
            propiedad.get('titulo'),
            propiedad.get('barrio'),
            propiedad.get('precio'),
            propiedad.get('ambientes'),
            propiedad.get('metros_cuadrados'),
            propiedad.get('descripcion'),
            propiedad.get('operacion'),
            propiedad.get('tipo'),
            propiedad.get('direccion'),
            propiedad.get('antiguedad'),
            propiedad.get('estado'),
            propiedad.get('orientacion'),
            propiedad.get('expensas'),
            propiedad.get('amenities'),
            propiedad.get('cochera'),
            propiedad.get('balcon'),
            propiedad.get('pileta'),
            propiedad.get('acepta_mascotas'),
            propiedad.get('aire_acondicionado'),
            propiedad.get('info_multimedia'),
            propiedad.get('documentos'),
            propiedad.get('videos'),
            propiedad.get('fotos'),
            propiedad.get('moneda_precio'),
            propiedad.get('moneda_expensas'),
            propiedad.get('fecha_procesamiento')
        ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error agregando propiedad: {e}")
        return False
    finally:
        conn.close()

def get_property_count() -> int:
    """
    Obtiene la cantidad total de propiedades en la base de datos
    
    Returns:
        Cantidad de propiedades
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM propiedades")
    row = cursor.fetchone()
    conn.close()
    
    return row['count'] if row else 0
