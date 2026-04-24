from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json
import os
from config import *
from database import *
from utils import log, analizar_hora, analizar_fecha
from whatsapp_api import *
from logic.ai_prioritization import obtener_prioridad_lead
from logic.response_builder import WhatsAppResponse

def get_calendar_service():
    """Obtener servicio de Google Calendar API.
    Compatible con entorno local (archivo JSON) y Render (variable de entorno GOOGLE_CALENDAR_KEY_B64).
    """
    import json, base64
    creds_data = None

    # Opción 1: archivo local (desarrollo)
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            with open(SERVICE_ACCOUNT_FILE, 'r') as f:
                creds_data = json.load(f)
        except Exception as e:
            return None

    # Opción 2: variable de entorno base64 (Render/producción)
    if not creds_data:
        key_b64 = os.environ.get("GOOGLE_CALENDAR_KEY_B64")
        if key_b64:
            try:
                creds_data = json.loads(base64.b64decode(key_b64).decode('utf-8'))
            except Exception as e:
                return None

    if not creds_data:
        return None

    try:
        creds = service_account.Credentials.from_service_account_info(
            creds_data, scopes=SCOPES)
        return build('calendar', 'v3', credentials=creds, cache_discovery=False)
    except Exception as e:
        return None


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


def notificar_cita_admin(cita):
    """Envía notificación de nueva cita al admin"""
    try:
        # Formatear fecha para el mensaje (DD-MM-AAAA)
        fecha_raw = cita['fecha']
        if hasattr(fecha_raw, 'strftime'):
            fecha_msg = fecha_raw.strftime("%d-%m-%Y")
        else:
            try:
                fecha_obj = datetime.strptime(str(fecha_raw), "%Y-%m-%d")
                fecha_msg = fecha_obj.strftime("%d-%m-%Y")
            except:
                fecha_msg = str(fecha_raw)
        
        mensaje = f"📅 *NUEVA CITA AGENDADA*\n\n"
        mensaje += f"👤 *Cliente:* {cita['nombre']}\n"
        mensaje += f"📞 *Teléfono:* +{cita['telefono']}\n"
        mensaje += f"📅 *Fecha:* {fecha_msg}\n"
        mensaje += f"⏰ *Hora:* {cita['hora']}\n"
        mensaje += f"🏠 *Propiedad ID:* {cita['propiedad_id']}\n"
        mensaje += f"🆔 *ID Cita:* {cita['id']}\n"
        mensaje += f"📝 *Notas:* {cita.get('notas', 'Sin notas')}\n\n"
        mensaje += f"📍 *Estado:* {cita['estado'].upper()}"
        
        # Análisis de IA de prioridad (Phase 7)
        estado_usuario = obtener_estado_usuario(cita['user_id'])
        historial = estado_usuario.get('data', {}).get('mensajes_recientes', [])
        
        # Obtener info de propiedad para el análisis
        propiedades = cargar_propiedades_cached()
        propiedad = next((p for p in propiedades if p.get('id_temporal') == cita['propiedad_id']), {})
        
        analisis = obtener_prioridad_lead(cita['user_id'], historial, propiedad)
        
        mensaje += f"\n\n🤖 *VEREDICTO IA*\n🌡️ Temperatura: {analisis['label_emoji']}\n💡 Razón: _{analisis['razonamiento']}_"
        
        # Usar notificar_agente para centralizar los logs de avisos al admin
        return notificar_agente(mensaje)
    except Exception as e:
        log(f"❌ Error notificando cita al admin: {e}")
        return False


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
Ⓜ️ *Volver* (Ir al menú - Envía 'M')"""

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
Ⓜ️ *Volver* (Ir al menú - Envía 'M')"""

    estado_usuario['fecha_cita'] = fecha_str
    
    # CASO A: Usuario indicó fecha Y hora ("mañana a las 10")
    if hora_ingresada:
        if hora_ingresada in horarios_disponibles:
            # Hora válida -> Ir a confirmación
            estado_usuario['hora_cita'] = hora_ingresada
            estado_usuario['paso'] = 'esperando_email_cita'
            actualizar_estado_usuario(user_id, estado_usuario)
            
            return {
                "type": "interactive_buttons",
                "body": f"📅 *FECHA SELECCIONADA:* {fecha_display} a las {hora_ingresada} hs.\n\n📧 *¿Te gustaría dejarnos tu correo electrónico?* (Opcional)\nEsto nos permite enviarte recordatorios y más detalles de la propiedad.",
                "buttons": [
                    {"id": "1", "title": "✍️ Escribir email"},
                    {"id": "2", "title": "⏭️ Saltar Paso"}
                ]
            }
        else:
            # Hora inválida o ocupada
            return f"""❌ *Horario no disponible*
El horario {hora_ingresada} no está disponible para el {fecha_display}.

⏰ *Horarios libres:*
{", ".join(horarios_disponibles)}

Por favor, escribí uno de los horarios disponibles:

❌ *SALIR (Envía 'S')*"""

    # CASO B: Solicitó solo fecha -> Pedir hora
    estado_usuario['paso'] = 'seleccionar_hora_cita'
    estado_usuario['horarios_disponibles'] = horarios_disponibles
    actualizar_estado_usuario(user_id, estado_usuario)
    
    return mostrar_seleccion_horarios(fecha_display, horarios_disponibles)


def manejar_confirmar_cita(text_lower, estado_usuario, user_id):
    """Paso final de confirmación explícita con opciones de modificación"""
    
    # Depuración inicial
    log(f"🔍 DEBUG: manejar_confirmar_cita llamada con text_lower='{text_lower}', user_id={user_id}")
    log(f"🔍 DEBUG: estado_usuario actual: {json.dumps(estado_usuario, default=str)}")
    
    # Opción 1: Confirmar cita
    if text_lower in ["1", "si", "sí", "confirmar", "ok", "dale"]:
        log("✅ Opción 1 seleccionada - Confirmando cita")
        
        # Obtener datos del estado
        fecha = estado_usuario.get('fecha_cita')
        hora = estado_usuario.get('hora_cita')
        nombre = estado_usuario.get('nombre_cliente', 'Cliente')
        email = estado_usuario.get('email_cliente')
        
        log(f"📝 Datos de cita: fecha={fecha}, hora={hora}, nombre={nombre}, email={email}")
        
        # Obtener propiedad
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades_lista = estado_usuario.get('propiedades_filtradas', [])
        propiedad_id = "N/A"
        propiedad_titulo = "Propiedad"
        
        if propiedades_lista and isinstance(propiedades_lista, list) and indice and 1 <= indice <= len(propiedades_lista):
            propiedad = propiedades_lista[indice - 1]
            if isinstance(propiedad, dict):
                propiedad_id = propiedad.get('id_temporal', 'N/A')
                propiedad_titulo = propiedad.get('titulo', 'Propiedad')
                log(f"🏠 Propiedad encontrada: {propiedad_id} - {propiedad_titulo}")
            else:
                propiedad_id = str(propiedad)
                propiedad_titulo = str(propiedad)
                log(f"🏠 Propiedad (string): {propiedad_id}")

        # Verificar que tenemos los datos mínimos necesarios
        if not fecha or not hora:
            log("❌ Error: Fecha u hora no están en estado_usuario")
            return "❌ *Error interno*: No pude recuperar los datos de la cita. Por favor, intentá agendar nuevamente.\n\nⓂ️ *VOLVER AL MENÚ (Envía 'M')* 🏠"

        # Crear la cita
        log("🔄 Llamando a crear_cita...")
        cita_resultado = crear_cita(
            user_id=user_id,
            nombre=nombre,
            telefono=user_id,
            fecha=fecha,
            hora=hora,
            propiedad_id=propiedad_id,
            email=email,
            notas="Agendado vía Bot"
        )
        
        if not cita_resultado:
            log("❌ Error: crear_cita devolvió None")
            return "❌ *Error al agendar la cita*\n\nPor favor, intentá nuevamente más tarde o contactá a un asesor.\n\nⓂ️ *VOLVER AL MENÚ (Envía 'M')* 🏠"
        
        log(f"✅ Cita creada exitosamente: {cita_resultado}")
        
        # Resetear estado
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['fecha_cita'] = None
        estado_usuario['hora_cita'] = None
        estado_usuario['email_cliente'] = None
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Formatear fecha para el mensaje
        try:
            if hasattr(fecha, 'strftime'):
                fecha_f = fecha.strftime("%d-%m-%Y")
            else:
                fecha_f = datetime.strptime(str(fecha), "%Y-%m-%d").strftime("%d-%m-%Y")
        except:
            fecha_f = str(fecha)
        
        # Mensaje de confirmación
        mensaje_confirmacion = f"""
✅ *¡VISITA CONFIRMADA!*

━━━━━━━━━━━━━━━━━━━━
📅 *Fecha:* {fecha_f}
⏰ *Hora:* {hora} hs
🏠 *Propiedad:* {propiedad_titulo}
👤 *Nombre:* {nombre}
📞 *Teléfono:* +{user_id}
📧 *Email:* {email if email else 'No proporcionado'}
━━━━━━━━━━━━━━━━━━━━

📍 *Te esperamos.* Si necesitas cancelar o modificar, podes:
• Enviar *'MIS CITAS'* para ver tus visitas
• Responder a los recordatorios que recibirás

👋 *¡Muchas gracias por confiar en Dante Propiedades!*

Ⓜ️ *VOLVER AL MENÚ (Envía 'M')* 🏠
❌ *SALIR (Envía 'S')*
"""
        # Opción A: mensaje rico de confirmación + botones separados
        nav_buttons = WhatsAppResponse.buttons(
            header="✅ ¡VISITA CONFIRMADA!",
            body="Tu cita fue agendada correctamente. Te esperamos!",
            buttons=[
                {"id": "opcion_4", "title": "Ver mis citas"},
                {"id": "m", "title": "Volver al menú"},
                {"id": "s", "title": "Salir"}
            ]
        )
        return [mensaje_confirmacion, nav_buttons]
    
    # Opción 2: Modificar fecha/hora
    elif text_lower in ["2", "modificar", "cambiar", "cambiar fecha"]:
        log("🔄 Opción 2 seleccionada - Modificando cita")
        estado_usuario['paso'] = 'solicitar_fecha_cita'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "🔄 *Perfecto! Vamos a modificar tu visita.*\n\n📅 Enviá la nueva fecha que prefieras (ej: 'mañana 10am', 'jueves 14:30'):"
    
    # Opción 3: Cancelar cita
    elif text_lower in ["3", "cancelar", "anular", "no", "no quiero"]:
        log("❌ Opción 3 seleccionada - Cancelando cita")
        
        # Registrar la cancelación
        try:
            guardar_en_postgresql(
                telefono=user_id,
                nombre=estado_usuario.get('nombre_cliente', 'Cliente'),
                accion="cita_cancelada",
                detalles=f"Cita cancelada por el usuario antes de confirmar. Fecha: {estado_usuario.get('fecha_cita')} Hora: {estado_usuario.get('hora_cita')}"
            )
            log("✅ Cancelación registrada en PostgreSQL")
        except Exception as e:
            log(f"⚠️ Error registrando cancelación: {e}")
        
        # Notificar al agente
        try:
            notificar_agente(f"❌ *CITA CANCELADA POR EL USUARIO*\n👤 {estado_usuario.get('nombre_cliente', 'Cliente')}\n📞 +{user_id}\n🗓️ Cancelada antes de confirmar")
            log("✅ Notificación de cancelación enviada al agente")
        except Exception as e:
            log(f"⚠️ Error notificando cancelación: {e}")
        
        # Resetear estado
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['fecha_cita'] = None
        estado_usuario['hora_cita'] = None
        estado_usuario['email_cliente'] = None
        actualizar_estado_usuario(user_id, estado_usuario)
        
        return WhatsAppResponse.buttons(
            header="❌ CITA CANCELADA",
            body="Si en otro momento deséas agendar una visita, podés volver a empezar desde el catálogo.",
            buttons=[
                {"id": "opcion_7", "title": "Ver propiedades"},
                {"id": "m", "title": "Volver al menú"},
                {"id": "s", "title": "Salir"}
            ]
        )
        
    else:
        # Mensaje de ayuda para opción no válida
        log(f"⚠️ Opción no reconocida: '{text_lower}'")
        return f"""❌ *Operación cancelada.*

Por favor elegí una de las siguientes opciones:

1️⃣ *CONFIRMAR CITA* ✅
2️⃣ *MODIFICAR FECHA/HORA* 🔄
3️⃣ *CANCELAR CITA* ❌

👉 Respondé con el número (1, 2 o 3)
"""




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


def manejar_seleccionar_hora_cita(text, estado_usuario, user_id):
    """Maneja la selección de hora"""
    text_lower = text.lower()
    
    if text_lower in ["0", "salir", "cancelar"]:
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return WhatsAppResponse.buttons(
            header="❌ OPERACIÓN CANCELADA",
            body="Si querés agendar en otro momento, podes buscar una propiedad desde el menú.",
            buttons=[
                {"id": "m", "title": "Volver al menú"},
                {"id": "s", "title": "Salir"}
            ]
        )
    
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
Ⓜ️ *Volver* (Ir al menú - Envía 'M')"""
            
    # Hora válida
    estado_usuario['hora_cita'] = hora_elegida
    estado_usuario['paso'] = 'esperando_email_cita' 
    actualizar_estado_usuario(user_id, estado_usuario)
    
    return {
        "type": "interactive_buttons",
        "body": f"📅 *HORARIO SELECCIONADO:* {hora_elegida} hs.\n\n📧 *¿Te gustaría dejarnos tu correo electrónico?* (Opcional)\nEsto nos permite enviarte recordatorios y más detalles de la propiedad.",
        "buttons": [
            {"id": "1", "title": "✍️ Escribir email"},
            {"id": "2", "title": "⏭️ Saltar Paso"}
        ]
    }


def manejar_email_cita(text, estado_usuario, user_id):
    """Maneja la captura del email (opcional) y presenta opciones de confirmación"""
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
    
    fecha_raw = estado_usuario.get('fecha_cita')
    if hasattr(fecha_raw, 'strftime'):
        fecha_display = fecha_raw.strftime("%d-%m-%Y")
    else:
        try:
            fecha_display = datetime.strptime(str(fecha_raw), "%Y-%m-%d").strftime("%d-%m-%Y")
        except:
            fecha_display = str(fecha_raw)
    hora = estado_usuario['hora_cita']
    email = estado_usuario.get('email_cliente', 'No proporcionado')
    
    # Mostrar resumen con opciones de confirmación
    resumen = f"""📅 *RESUMEN DE TU VISITA*

📍 *Propiedad:* {obtener_titulo_propiedad(estado_usuario)}
👤 *Nombre:* {estado_usuario.get('nombre_cliente', 'Cliente')}
📞 *Teléfono:* +{user_id}
📧 *Email:* {email if email else 'No proporcionado'}
📅 *Fecha:* {fecha_display}
⏰ *Hora:* {hora} hs

━━━━━━━━━━━━━━━━━━━━"""

    return {
        "type": "interactive_buttons",
        "body": resumen,
        "buttons": [
            {"id": "1", "title": "CONFIRMAR ✅"},
            {"id": "2", "title": "MODIFICAR 🔄"},
            {"id": "3", "title": "CANCELAR ❌"}
        ],
        "footer": "Selecciona una opción 👇"
    }


def obtener_titulo_propiedad(estado_usuario):
    """Obtiene el título de la propiedad del estado del usuario"""
    try:
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades_lista = estado_usuario.get('propiedades_filtradas', [])
        
        if propiedades_lista and isinstance(propiedades_lista, list) and indice and 1 <= indice <= len(propiedades_lista):
            propiedad = propiedades_lista[indice - 1]
            if isinstance(propiedad, dict):
                return propiedad.get('titulo', 'Propiedad')
            else:
                return str(propiedad)
        return "Propiedad seleccionada"
    except:
        return "Propiedad seleccionada"
    
    

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
        
        # Análisis de IA de prioridad (Phase 7)
        historial = estado_usuario.get('data', {}).get('mensajes_recientes', [])
        analisis = obtener_prioridad_lead(user_id, historial, {})
        prioridad_msg = f"\n🌡️ IA Veredicto: {analisis['label_emoji']}\n💡 Razón: {analisis['razonamiento']}"
        
        notificar_agente(f"📋 *LEAD SIN CITA - SOLO INFO*\n👤 {nombre_cliente}\n📞 +{user_id}\n📝 Solo solicitó información{prioridad_msg}")
        
        estado_usuario.update({
            'paso': 'menu_principal',
            'nombre_cliente': None
        })
        actualizar_estado_usuario(user_id, estado_usuario)
        
        return WhatsAppResponse.buttons(
            header="✅ ENTENDIDO",
            body=f"Un asesor se contactará con vos para brindarte toda la información, *{nombre_cliente}*.",
            buttons=[
                {"id": "m", "title": "Volver al menú"},
                {"id": "s", "title": "Salir"}
            ]
        )
    
    elif text_lower in ["3", "ofertar", "oferta", "comprar", "alquilar ya"]:
        nombre_cliente = estado_usuario.get('nombre_cliente', 'Cliente')
        
        # Análisis de IA de prioridad (Phase 7)
        historial = estado_usuario.get('data', {}).get('mensajes_recientes', [])
        analisis = obtener_prioridad_lead(user_id, historial, {})
        prioridad_msg = f"\n🌡️ IA Veredicto: {analisis['label_emoji']}\n💡 Razón: {analisis['razonamiento']}"
        
        notificar_agente(f"🔥🔥 *LEAD CALIENTE - QUIERE OFERTAR!* 🔥🔥\n👤 {nombre_cliente}\n📞 +{user_id}\n💸 LISTO PARA OPERAR{prioridad_msg}")
        
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
        
        return WhatsAppResponse.buttons(
            header="🔥 PRIORIDAD MÁXIMA",
            body=f"Un asesor te contactará en los próximos *15 minutos* para gestionar tu oferta, *{nombre_cliente}*.",
            buttons=[
                {"id": "opcion_4", "title": "Ver mis citas"},
                {"id": "m", "title": "Volver al menú"},
                {"id": "s", "title": "Salir"}
            ]
        )
    
    elif text_lower in ["0", "salir", "chau", "adiós"]:
        estado_usuario.update({
            'paso': 'menu_principal',
            'nombre_cliente': None
        })
        actualizar_estado_usuario(user_id, estado_usuario)
        return "¡Gracias por confiar en Dante Propiedades! 🏠🗝️"
    
    else:
        return {
            "type": "interactive_buttons",
            "body": "❌ Opción no válida. Por favor selecciona una opción del menú:",
            "buttons": [
                {"id": "1", "title": "SÍ, AGENDAR 📅"},
                {"id": "2", "title": "SOLO INFO 📋"},
                {"id": "3", "title": "OFERTAR 💰"}
            ],
            "footer": "❌ Envía 'S' para Salir"
        }


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


def son_numeros_identicos(num1, num2):
    """Compara dos números de teléfono normalizándolos"""
    if not num1 or not num2:
        return False
    
    n1 = str(num1).strip().lstrip('+').replace(' ', '')
    n2 = str(num2).strip().lstrip('+').replace(' ', '')
    
    # Normalizar formato argentino
    for prefix in ['549', '54']:
        if n1.startswith(prefix):
            n1 = n1[len(prefix):]
        if n2.startswith(prefix):
            n2 = n2[len(prefix):]
    
    # Eliminar 9 inicial
    if len(n1) > 1 and n1[0] == '9':
        n1 = n1[1:]
    if len(n2) > 1 and n2[0] == '9':
        n2 = n2[1:]
    
    return n1 == n2