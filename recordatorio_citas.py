#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de recordatorios automáticos de citas
Ejecutar diariamente a las 9:00 AM
"""
import time
import requests
import psycopg2
from datetime import datetime, timedelta
import os
import sys
import logging
import json  # ← Agrega esta línea junto a los otros imports
from dotenv import load_dotenv




# Configuración
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración de base de datos
DATABASE_URL = os.getenv('DATABASE_URL')
ADMIN_KEY = os.getenv('ADMIN_KEY', 'dante_admin_2024')
BASE_URL = os.getenv('BASE_URL', 'https://meta-rjpb.onrender.com')

def get_db_connection(max_retries=3):
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
                connect_timeout=10,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5
            )
            # Verificar si la conexión es funcional
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return conn
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            error_str = str(e)
            if i < max_retries - 1:
                logger.warning(f"⚠️ Error de conexión (Intento {i+1}): {error_str}. Reintentando...")
                time.sleep(1)
                continue
            logger.error(f"❌ Error final conectando a DB: {e}")
            break
        except Exception as e:
            logger.error(f"❌ Error inesperado conectando a DB: {e}")
            break
    return None

def obtener_citas_para_recordatorio():
    """
    Obtiene citas para mañana que no han recibido recordatorio
    Incluye logs detallados para diagnóstico
    """
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("❌ No se pudo conectar a la base de datos")
            return []
        
        cursor = conn.cursor()
        
        # Calcular mañana
        manana = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        hoy = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"🔍 Buscando citas para MAÑANA: {manana}")
        logger.info(f"📅 Fecha de hoy: {hoy}")
        
        # 🔴 PASO 1: Ver cuántas citas hay en total para mañana (sin filtros)
        cursor.execute("""
            SELECT COUNT(*) FROM citas 
            WHERE fecha_cita = %s
        """, (manana,))
        total_para_manana = cursor.fetchone()[0]
        logger.info(f"📊 TOTAL de citas para mañana (sin filtros): {total_para_manana}")
        
        # 🟡 PASO 2: Ver cuántas están pendientes y sin recordatorio (las que procesaremos)
        cursor.execute("""
            SELECT 
                id, telefono, nombre, fecha_cita, hora_cita, 
                propiedad_id, email, estado, recordatorio_enviado
            FROM citas 
            WHERE fecha_cita = %s 
            AND estado = 'pendiente'
            AND (recordatorio_enviado = FALSE OR recordatorio_enviado IS NULL)
        """, (manana,))
        
        citas = cursor.fetchall()
        logger.info(f"📊 Citas que CUMPLEN CRITERIOS (pendientes + sin recordatorio): {len(citas)}")
        
        # 🟢 PASO 3: Solo loguear si no hay citas para dar contexto rápido
        if total_para_manana > 0 and len(citas) == 0:
            logger.info("ℹ️ Todas las citas de mañana ya fueron procesadas o no están en estado 'pendiente'.")
        
        # 🟣 PASO 4: Si hay citas seleccionadas, mostrar resumen
        if citas:
            logger.info(f"✅ Se procesarán {len(citas)} citas:")
            for idx, c in enumerate(citas, 1):
                logger.info(f"   {idx}. ID {c[0]}: {c[2]} - {c[4]} (Tel: {c[1]})")
        else:
            logger.info("📭 No hay citas para procesar hoy")
        
        cursor.close()
        conn.close()
        
        return citas
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo citas: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
    cita_id, telefono, nombre, fecha, hora, propiedad_id, email = cita[:7]
    
    logger.info(f"📤 Enviando recordatorio a {nombre} ({telefono}) - Cita {fecha} {hora} (ID: {cita_id})")
    
    propiedad_titulo = obtener_titulo_propiedad(propiedad_id)
    fecha_formateada = fecha.strftime('%d/%m') if hasattr(fecha, 'strftime') else fecha
    
    # Datos para el endpoint - INCLUIR CITA_ID
    data = {
        "user_id": telefono,
        "nombre": nombre,
        "fecha": fecha_formateada,
        "fecha_iso": str(fecha),
        "hora": hora,
        "propiedad": propiedad_titulo,
        "cita_id": cita_id  # ← NUEVO: pasar el ID
    }
    
    BASE_URL = os.getenv('BASE_URL', 'https://meta-rjpb.onrender.com')
    url = f"{BASE_URL}/api/internal/send-reminder"
    
    try:
        response = requests.post(url, json=data, timeout=45)
        
        if response.status_code == 200:
            logger.info(f"✅ Recordatorio enviado a {nombre} para cita {cita_id}")
            
            # Marcar como enviado
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
            
    except Exception as e:
        logger.error(f"❌ Error enviando recordatorio: {e}")
        return False

def main():
    """Función principal con envío escalonado de recordatorios"""
    start_time = datetime.now()
    logger.info("🚀 Iniciando proceso de recordatorios")
    
    try:
        citas = obtener_citas_para_recordatorio()
        
        if not citas:
            logger.info("📭 No hay citas para recordatorio hoy")
            return
        
        total_citas = len(citas)
        logger.info(f"📋 Total de citas a procesar: {total_citas}")
        
        # Configuración de escalonamiento
        PAUSA_BASE = 2  # segundos
        PAUSA_MAXIMA = 10  # segundos
        TIEMPO_MAXIMO_TOTAL = 110  # segundos (con timeout de 120s)
        
        exitosos = 0
        fallidos = 0
        tiempo_inicio = time.time()
        
        for idx, cita in enumerate(citas, 1):
            # Verificar tiempo total
            if time.time() - tiempo_inicio > TIEMPO_MAXIMO_TOTAL:
                logger.warning(f"⏰ Tiempo máximo cercano. Procesando última cita {idx}/{total_citas}")
            
            cita_id = cita[0]
            logger.info(f"🔄 Procesando cita {idx}/{total_citas} (ID: {cita_id})")
            
            try:
                inicio_cita = datetime.now()
                
                if enviar_recordatorio(cita):
                    exitosos += 1
                    logger.info(f"✅ Cita {cita_id} procesada exitosamente")
                else:
                    fallidos += 1
                    logger.warning(f"⚠️ Cita {cita_id} marcada como fallida")
                    
            except Exception as e:
                fallidos += 1
                logger.error(f"🔥 Error procesando cita {cita_id}: {e}")
            
            # Pausa escalonada entre envíos
            if idx < total_citas:
                # Pausa progresiva: 2s, 3s, 4s... (pero no más de 10s)
                pausa = min(PAUSA_BASE + (idx-1), PAUSA_MAXIMA)
                logger.info(f"⏱️ Pausa de {pausa}s antes de siguiente envío")
                time.sleep(pausa)
        
        # Resumen final
        tiempo_total = (datetime.now() - start_time).total_seconds()
        logger.info(f"📊 RESUMEN FINAL - Tiempo total: {tiempo_total:.2f}s")
        logger.info(f"   ✅ Exitosos: {exitosos}")
        logger.info(f"   ❌ Fallidos: {fallidos}")
        logger.info(f"   📈 Tasa de éxito: {(exitosos/(exitosos+fallidos)*100):.1f}%")
        
        ids_procesados = [c[0] for c in citas]
        
        guardar_resumen_recordatorios({
            "fecha": start_time.strftime('%Y-%m-%d'),
            "total": total_citas,
            "exitosos": exitosos,
            "fallidos": fallidos,
            "detalles": {"ids": ids_procesados},
            "tiempo_segundos": tiempo_total
        })
        
    except Exception as e:
        logger.critical(f"💥 Error CRÍTICO en main(): {e}")
        raise

def guardar_resumen_recordatorios(resumen):
    """Guarda un resumen de la ejecución en la base de datos"""
    try:
        conn = get_db_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO recordatorios_log 
            (fecha, total, exitosos, fallidos, detalles, tiempo_segundos)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            resumen['fecha'],
            resumen['total'],
            resumen['exitosos'],
            resumen['fallidos'],
            json.dumps(resumen['detalles'], default=str),
            resumen['tiempo_segundos']
        ))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error guardando resumen: {e}")
        
if __name__ == "__main__":
    main()