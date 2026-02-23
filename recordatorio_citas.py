#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de recordatorios automáticos de citas
Ejecutar diariamente a las 9:00 AM
"""

import requests
import psycopg2
from datetime import datetime, timedelta
import os
import sys
import logging
from dotenv import load_dotenv




# Configuración
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración de base de datos
DATABASE_URL = os.getenv('DATABASE_URL')
ADMIN_KEY = os.getenv('ADMIN_KEY', 'dante_admin_2024')
BASE_URL = os.getenv('BASE_URL', 'https://meta-rjpb.onrender.com')

def get_db_connection():
    """Obtiene conexión a PostgreSQL"""
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.error(f"Error conectando a DB: {e}")
        return None

def obtener_citas_para_recordatorio():
    """
    Obtiene citas para mañana que no han recibido recordatorio
    """
    try:
        conn = get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # Calcular mañana
        manana = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        logger.info(f"🔍 Buscando citas para {manana}")
        
        # 👇 SOLO 7 COLUMNAS, EN EL MISMO ORDEN QUE ESPERA enviar_recordatorio()
        cursor.execute("""
            SELECT 
                id,              -- 1. cita_id
                telefono,        -- 2. telefono
                nombre,          -- 3. nombre
                fecha_cita,      -- 4. fecha
                hora_cita,       -- 5. hora
                propiedad_id,    -- 6. propiedad_id
                email            -- 7. email
            FROM citas 
            WHERE fecha_cita = %s 
            AND estado = 'pendiente'
            AND (recordatorio_enviado = FALSE OR recordatorio_enviado IS NULL)
        """, (manana,))
        
        citas = cursor.fetchall()
        logger.info(f"📊 Encontradas {len(citas)} citas para recordatorio")
        
        cursor.close()
        conn.close()
        
        return citas
        
    except Exception as e:
        logger.error(f"Error obteniendo citas: {e}")
        return []
    


def obtener_titulo_propiedad(propiedad_id):
    """
    Obtiene el título de una propiedad desde propiedades.json
    """
    try:
        if os.path.exists('propiedades.json'):
            with open('propiedades.json', 'r', encoding='utf-8') as f:
                propiedades = json.load(f)
                for p in propiedades:
                    if p.get('id_temporal') == propiedad_id:
                        return p.get('titulo', propiedad_id)
    except Exception as e:
        logger.error(f"Error obteniendo título de propiedad {propiedad_id}: {e}")
    
    return propiedad_id  # Si no encuentra, devuelve el ID


    
def enviar_recordatorio(cita):
    """
    Envía recordatorio para una cita específica
    """
    cita_id, telefono, nombre, fecha, hora, propiedad_id, email = cita
    
    logger.info(f"📤 Enviando recordatorio a {nombre} ({telefono}) - Cita {fecha} {hora}")
    
    propiedad_titulo = obtener_titulo_propiedad(propiedad_id)
    fecha_formateada = fecha.strftime('%d/%m') if hasattr(fecha, 'strftime') else fecha
    
    # Datos para el endpoint
    data = {
        "user_id": telefono,
        "nombre": nombre,
        "fecha": fecha_formateada,
        "fecha_iso": str(fecha),
        "hora": hora,
        "propiedad": propiedad_titulo
    }
    
    # Obtener BASE_URL (ya debería estar configurada)
    BASE_URL = os.getenv('BASE_URL', 'https://meta-rjpb.onrender.com')
    url = f"{BASE_URL}/api/internal/send-reminder"
    
    logger.info(f"📞 Llamando a: {url}")
    
    try:
        # ⬆️ AUMENTAR TIMEOUT A 30 SEGUNDOS ⬆️
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"✅ Recordatorio enviado a {nombre}")
            
            # Marcar como enviado en DB
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE citas 
                    SET recordatorio_enviado = TRUE, 
                        recordatorio_enviado_en = NOW() 
                    WHERE id = %s
                """, (cita_id,))
                conn.commit()
                cursor.close()
                conn.close()
            
            return True
        else:
            logger.error(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error(f"⏰ Timeout después de 30 segundos - El endpoint tarda más de lo esperado")
        return False
    except Exception as e:
        logger.error(f"❌ Error enviando recordatorio: {e}")
        return False

def main():
    """Función principal"""
    logger.info("🚀 Iniciando proceso de recordatorios")
    
    citas = obtener_citas_para_recordatorio()
    
    if not citas:
        logger.info("No hay citas para recordatorio hoy")
        return
    
    exitosos = 0
    fallidos = 0
    
    for cita in citas:
        if enviar_recordatorio(cita):
            exitosos += 1
        else:
            fallidos += 1
    
    logger.info(f"📊 Resumen: {exitosos} exitosos, {fallidos} fallidos")

if __name__ == "__main__":
    main()