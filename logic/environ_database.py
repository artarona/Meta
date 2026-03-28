"""
Módulo de base de datos para Dante Propiedades
Maneja SQLite para análisis de entorno con IA
"""
import sqlite3
import json
import os
import time
from datetime import datetime
from pathlib import Path

# Paths
DB_PATH = os.environ.get('DB_PATH', 'instance/dante_properties.db')
LOG_PATH = 'instance/conversations.log'

def get_db_connection():
    """Obtiene conexión a la base de datos"""
    Path(os.path.dirname(DB_PATH)).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_environ_analysis_db():
    """Inicializa la base de datos para análisis de entorno"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla para almacenar análisis de entornos generados por IA
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS environ_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone TEXT UNIQUE NOT NULL,
            analysis_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_valid INTEGER DEFAULT 1
        )
    ''')
    
    # Tabla para logs de análisis
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS environ_analysis_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone TEXT NOT NULL,
            analysis_json TEXT,
            source TEXT DEFAULT 'ai',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success INTEGER DEFAULT 1,
            error TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de datos de análisis de entorno inicializada")

def save_environ_analysis(zone: str, analysis_data: dict, cache_days: int = 7):
    """Guarda el análisis de entorno en la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    analysis_json = json.dumps(analysis_data, ensure_ascii=False, indent=2)
    expires_at = datetime.now().timestamp() + (cache_days * 24 * 60 * 60)  # cache_days días
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO environ_analysis 
            (zone, analysis_json, updated_at, expires_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?)
        ''', (zone.lower().strip(), analysis_json, expires_at))
        
        conn.commit()
        print(f"✅ Análisis guardado para zona: {zone}")
        return True
    except Exception as e:
        print(f"❌ Error guardando análisis: {e}")
        return False
    finally:
        conn.close()

def get_environ_analysis(zone: str) -> dict:
    """Obtiene el análisis de entorno desde la base de datos"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT analysis_json, created_at, updated_at, expires_at
        FROM environ_analysis
        WHERE zone = ? AND is_valid = 1
    ''', (zone.lower().strip(),))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        # Verificar si expiró
        expires_at = datetime.fromisoformat(row['expires_at'])
        if expires_at > datetime.now():
            try:
                return json.loads(row['analysis_json'])
            except:
                pass
    
    return None

def is_environ_analysis_expired(zone: str) -> bool:
    """Verifica si el análisis de una zona está expirado"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT expires_at FROM environ_analysis
        WHERE zone = ? AND is_valid = 1
    ''', (zone.lower().strip(),))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return True  # No existe, considerar como expirado
    
    expires_at = datetime.fromisoformat(row['expires_at'])
    return expires_at <= datetime.now()

def log_environ_analysis_request(zone: str, success: bool = 1, error: str = None, analysis_json: str = None):
    """Guarda log de una solicitud de análisis"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO environ_analysis_logs 
            (zone, analysis_json, success, error)
            VALUES (?, ?, ?, ?)
        ''', (zone.lower().strip(), analysis_json, 1 if success else 0, error))
        
        conn.commit()
    except Exception as e:
        print(f"Error guardando log: {e}")
    finally:
        conn.close()

def delete_expired_environ_analysis():
    """Elimina análisis expirados"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM environ_analysis 
        WHERE expires_at < CURRENT_TIMESTAMP
    ''')
    
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted > 0:
        print(f"🧹 Eliminados {deleted} análisis expirados")
    
    return deleted
