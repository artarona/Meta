#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de seguimiento post-visita para Dante Propiedades
Busca citas confirmadas del día anterior y envía una encuesta de feedback.
"""
import time
import requests
import psycopg2
from datetime import datetime, timedelta
import os
import logging
import json
from dotenv import load_dotenv

# Configuración
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')
BASE_URL = os.getenv('BASE_URL', 'https://meta-rjpb.onrender.com')

def get_db_connection(max_retries=5):
    """Obtiene conexión a PostgreSQL con reintentos para manejar errores intermitentes de SSL"""
    import time
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL no encontrada en variables de entorno")
        return None

    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                DATABASE_URL,
                sslmode='require',
                connect_timeout=15,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5
            )
            return conn
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            if i < max_retries - 1:
                logger.warning(f"⚠️ Error de conexión (Intento {i+1}): {e}. Reintentando...")
                time.sleep(2)
                continue
            logger.error(f"❌ Error final conectando a DB: {e}")
            break
        except Exception as e:
            logger.error(f"❌ Error inesperado conectando a DB: {e}")
            break
    return None

def obtener_titulo_propiedad(propiedad_id):
    """Obtiene el título de la propiedad desde propiedades.json"""
    try:
        path = os.path.join(os.path.dirname(__file__), 'propiedades.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                propiedades = json.load(f)
                for p in propiedades:
                    if p.get('id_temporal') == propiedad_id:
                        return p.get('titulo', propiedad_id)
    except Exception as e:
        logger.error(f"Error obteniendo título {propiedad_id}: {e}")
    return propiedad_id

def obtener_citas_para_feedback():
    """Busca citas finalizadas ayer para pedir feedback"""
    try:
        conn = get_db_connection()
        if not conn: return []
        
        cursor = conn.cursor()
        
        # Citas de AYER que fueron confirmadas o completadas y no tienen feedback enviado
        ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        logger.info(f"🔍 Buscando visitas realizadas ayer ({ayer}) para feedback...")
        
        cursor.execute("""
            SELECT id, telefono, nombre, propiedad_id 
            FROM citas 
            WHERE fecha_cita = %s 
            AND estado IN ('confirmada', 'completada')
            AND (feedback_enviado = FALSE OR feedback_enviado IS NULL)
        """, (ayer,))
        
        citas = cursor.fetchall()
        logger.info(f"📊 Se encontraron {len(citas)} citas para seguimiento.")
        
        cursor.close()
        conn.close()
        return citas
    except Exception as e:
        logger.error(f"❌ Error al obtener citas para feedback: {e}")
        return []

def enviar_feedback(cita):
    """Envía mensaje de feedback vía API interna"""
    cita_id, telefono, nombre, propiedad_id = cita
    propiedad_titulo = obtener_titulo_propiedad(propiedad_id)
    
    url = f"{BASE_URL}/api/internal/send-feedback"
    data = {
        "user_id": telefono,
        "nombre": nombre,
        "propiedad": propiedad_titulo,
        "cita_id": cita_id
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            logger.info(f"✅ Feedback enviado a {nombre} (Cita {cita_id})")
            return True
        else:
            logger.error(f"❌ Fallo al enviar feedback ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        logger.error(f"🔥 Error enviando feedback cita {cita_id}: {e}")
        return False

def main():
    logger.info("🚀 Iniciando proceso de Seguimiento Post-Visita")
    citas = obtener_citas_para_feedback()
    
    if not citas:
        logger.info("📭 No hay visitas de ayer para procesar.")
        return

    for cita in citas:
        enviar_feedback(cita)
        time.sleep(3) # Pausa amigable entre envíos

if __name__ == "__main__":
    main()
