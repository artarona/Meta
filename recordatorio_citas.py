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
        hoy = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Buscando citas para {manana}")
        
        cursor.execute("""
            SELECT 
                id, user_id, telefono, nombre, 
                fecha_cita, hora_cita, propiedad_id, email,
                recordatorio_enviado
            FROM citas 
            WHERE fecha_cita = %s 
            AND estado = 'pendiente'
            AND (recordatorio_enviado = FALSE OR recordatorio_enviado IS NULL)
            ORDER BY hora_cita
        """, (manana,))
        
        citas = cursor.fetchall()
        logger.info(f"Encontradas {len(citas)} citas para recordatorio")
        
        cursor.close()
        conn.close()
        
        return citas
        
    except Exception as e:
        logger.error(f"Error obteniendo citas: {e}")
        return []

def enviar_recordatorio(cita):
    """
    Envía recordatorio para una cita específica
    """
    cita_id, user_id, telefono, nombre, fecha, hora, propiedad_id, email, recordatorio_previo = cita
    
    logger.info(f"Enviando recordatorio a {nombre} ({telefono}) - Cita {fecha} {hora}")
    
    # Buscar título de propiedad (opcional)
    propiedad_titulo = propiedad_id
    try:
        # Intentar obtener de propiedades.json
        import json
        if os.path.exists('propiedades.json'):
            with open('propiedades.json', 'r', encoding='utf-8') as f:
                propiedades = json.load(f)
                for p in propiedades:
                    if p.get('id_temporal') == propiedad_id:
                        propiedad_titulo = p.get('titulo', propiedad_id)
                        break
    except:
        pass
    
    # Datos para el endpoint
    data = {
        "user_id": telefono or user_id,
        "nombre": nombre,
        "fecha": datetime.strptime(str(fecha), '%Y-%m-%d').strftime('%d/%m'),
        "fecha_iso": str(fecha),
        "hora": hora,
        "propiedad": propiedad_titulo
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/internal/send-reminder?key={ADMIN_KEY}",
            json=data,
            timeout=15
        )
        
        if response.status_code == 200:
            logger.info(f"✅ Recordatorio enviado a {nombre}")
            return True
        else:
            logger.error(f"❌ Error {response.status_code}: {response.text}")
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