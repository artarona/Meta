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
        
        # 🟢 PASO 3: Si hay diferencia, mostrar DETALLE de todas las citas para diagnóstico
        if len(citas) < total_para_manana:
            logger.info("🔍 DETALLE de TODAS las citas para mañana:")
            
            cursor.execute("""
                SELECT 
                    id, nombre, telefono, hora_cita, 
                    estado, recordatorio_enviado, email
                FROM citas 
                WHERE fecha_cita = %s
                ORDER BY id
            """, (manana,))
            
            todas_citas = cursor.fetchall()
            
            for cita in todas_citas:
                cita_id = cita[0]
                nombre = cita[1] or "Sin nombre"
                telefono = cita[2] or "Sin teléfono"
                hora = cita[3] or "Sin hora"
                estado = cita[4] or "pendiente"
                recordatorio = cita[5]
                email = cita[6] or "Sin email"
                
                # Determinar por qué NO fue seleccionada
                if estado != 'pendiente':
                    motivo = f"Estado '{estado}' (debe ser 'pendiente')"
                elif recordatorio:
                    motivo = f"Recordatorio ya enviado (TRUE)"
                else:
                    motivo = "Cumple criterios (DEBERÍA estar incluida)"
                
                logger.info(f"   📌 ID {cita_id}: {nombre} - {hora} - Tel: {telefono}")
                logger.info(f"      Estado: {estado} | Recordatorio enviado: {recordatorio} | Email: {email}")
                logger.info(f"      Motivo exclusión: {motivo}")
        
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
    """Función principal con manejo robusto de errores"""
    start_time = datetime.now()
    logger.info("🚀 Iniciando proceso de recordatorios")
    
    try:
        citas = obtener_citas_para_recordatorio()
        
        if not citas:
            logger.info("📭 No hay citas para recordatorio hoy")
            return
        
        logger.info(f"📋 Total de citas a procesar: {len(citas)}")
        
        exitosos = 0
        fallidos = 0
        detalles = []
        
        for idx, cita in enumerate(citas, 1):
            cita_id = cita[0]  # El ID está en la primera posición
            logger.info(f"🔄 Procesando cita {idx}/{len(citas)} (ID: {cita_id})")
            
            try:
                # Registrar inicio del proceso para esta cita
                inicio_cita = datetime.now()
                
                if enviar_recordatorio(cita):
                    exitosos += 1
                    detalles.append({
                        "cita_id": cita_id,
                        "estado": "exitoso",
                        "tiempo_ms": (datetime.now() - inicio_cita).total_seconds() * 1000
                    })
                    logger.info(f"✅ Cita {cita_id} procesada exitosamente")
                else:
                    fallidos += 1
                    detalles.append({
                        "cita_id": cita_id,
                        "estado": "fallido",
                        "error": "La función enviar_recordatorio devolvió False"
                    })
                    logger.warning(f"⚠️ Cita {cita_id} marcada como fallida")
                    
            except Exception as e:
                fallidos += 1
                error_msg = str(e)
                detalles.append({
                    "cita_id": cita_id,
                    "estado": "error",
                    "error": error_msg
                })
                logger.error(f"🔥 Error procesando cita {cita_id}: {error_msg}")
                # Continuamos con la siguiente cita
                continue
            
            # Pequeña pausa entre envíos para no sobrecargar la API
            if idx < len(citas):
                time.sleep(1)  # 1 segundo de pausa entre envíos
        
        # Resumen final
        tiempo_total = (datetime.now() - start_time).total_seconds()
        logger.info(f"📊 RESUMEN FINAL - Tiempo total: {tiempo_total:.2f}s")
        logger.info(f"   ✅ Exitosos: {exitosos}")
        logger.info(f"   ❌ Fallidos: {fallidos}")
        logger.info(f"   📈 Tasa de éxito: {(exitosos/(exitosos+fallidos)*100):.1f}%")
        
        # Guardar resumen en base de datos (opcional)
        guardar_resumen_recordatorios({
            "fecha": start_time.strftime('%Y-%m-%d'),
            "total": len(citas),
            "exitosos": exitosos,
            "fallidos": fallidos,
            "detalles": detalles,
            "tiempo_segundos": tiempo_total
        })
        
    except Exception as e:
        logger.critical(f"💥 Error CRÍTICO en main(): {e}")
        # Aquí podrías enviar una alerta al admin
        raise  # Re-lanzamos la excepción para que Gunicorn la registre

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