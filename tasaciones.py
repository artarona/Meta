from utils import log, numero_a_emoji
from config import *
from database import *
from whatsapp_api import *
from logic.response_builder import WhatsAppResponse
import json
import os

def verificar_combinacion_valida(barrio, tipo, operacion='venta'):
    """
    Verifica si existe una combinación EXACTA en el mapa.
    Retorna True si hay match exacto Y muestra > 0 Y avg_m2 válido.
    """
    try:
        map_path = os.path.join(os.path.dirname(__file__), "market_valuation_map.json")
        if not os.path.exists(map_path):
            log(f"🚫 No se halló el archivo market_valuation_map.json")
            return False
        
        with open(map_path, 'r', encoding='utf-8') as f:
            vmap = json.load(f)
        
        barrio_key = barrio.lower().strip()
        op_key = operacion.lower().strip()
        tipo_key = tipo.lower().strip()
        
        log(f"🔎 Verificando match EXACTO: '{barrio_key}' - '{op_key}' - '{tipo_key}'")
        
        if barrio_key not in vmap:
            log(f"❌ Barrio '{barrio_key}' no existe en el mapa")
            return False
        
        op_data = vmap[barrio_key].get(op_key)
        if not op_data:
            log(f"❌ Operación '{op_key}' no existe para barrio '{barrio_key}'")
            return False
        
        if tipo_key not in op_data:
            log(f"❌ Tipo '{tipo_key}' no existe para barrio '{barrio_key}' - operación '{op_key}'")
            return False
        
        stats = op_data[tipo_key]
        muestra = stats.get('muestra', 0)
        
        if muestra <= 0:
            log(f"❌ Combinación encontrada pero muestra = 0")
            return False
        
        avg_m2 = stats.get('avg_m2')
        if avg_m2 is None or avg_m2 <= 0:
            log(f"❌ Combinación encontrada pero avg_m2 inválido")
            return False
        
        log(f"✅ Match EXACTO válido encontrado")
        return True
        
    except Exception as e:
        log(f"⚠️ Error en verificación: {e}")
        return False


def obtener_tasacion_local(barrio, tipo, estado, operacion='venta'):
    """Obtiene los datos de valoración SOLO si existe match exacto."""
    try:
        map_path = os.path.join(os.path.dirname(__file__), "market_valuation_map.json")
        if not os.path.exists(map_path):
            return None
        
        with open(map_path, 'r', encoding='utf-8') as f:
            vmap = json.load(f)
        
        barrio_key = barrio.lower().strip()
        op_key = operacion.lower().strip()
        tipo_key = tipo.lower().strip()
        
        if barrio_key in vmap:
            op_data = vmap[barrio_key].get(op_key)
            if op_data and tipo_key in op_data:
                stats = op_data[tipo_key]
                muestra = stats.get('muestra', 0)
                
                if muestra <= 0:
                    return None
                
                avg_m2 = stats.get('avg_m2')
                if avg_m2 is None or avg_m2 <= 0:
                    return None
                
                moneda = stats.get('currency', 'USD' if op_key == 'venta' else 'ARS')
                
                return {
                    "precio_m2": avg_m2,
                    "moneda": moneda,
                    "is_fallback": False,
                    "fuentes": ["Estadísticas de Mercado (Consolidado)"],
                    "muestra": muestra
                }
        return None
        
    except Exception as e:
        log(f"⚠️ Error en tasación local: {e}")
        return None


def manejar_menu_tasacion(text_lower, estado_usuario, user_id):
    """Inicia el flujo de tasación adaptado a la plataforma"""
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram")
    
    if 'data' not in estado_usuario or not isinstance(estado_usuario['data'], dict):
        estado_usuario['data'] = {}
    
    estado_usuario['data']['datos_tasacion'] = {}
    estado_usuario['paso'] = 'tasacion_operacion'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    if es_fb_ig:
        # Facebook/Instagram: texto con emojis numéricos
        return {
            "type": "text",
            "body": "📊 *TASACIÓN VIRTUAL*\n\n¿Qué tipo de operación te interesa tasar?\n\n1️⃣ Venta 🏠\n2️⃣ Alquiler 🗝️\n\n🔙 M. Volver\n❌ S. Salir",
            "preview": False
        }
    else:
        # WhatsApp: botones interactivos
        return {
            "type": "interactive_buttons",
            "body": "📊 *TASACIÓN VIRTUAL*\n\n¿Qué tipo de operación te interesa tasar?",
            "buttons": [
                {"id": "1", "title": "Venta 🏠"},
                {"id": "2", "title": "Alquiler 🗝️"},
                {"id": "m", "title": "Volver 🔙"}
            ],
            "footer": "Selecciona una opción 👇"
        }
        
        
        
def manejar_tasacion_operacion(text_lower, estado_usuario, user_id):
    """Guarda la operación y continúa"""
    ops = {"1": "venta", "2": "alquiler"}
    
    # Manejar caso de reintentar (ID 10)
    if text_lower == "10":
        return manejar_reintentar_tasacion(estado_usuario, user_id)
    
    if text_lower in ops:
        if 'datos_tasacion' not in estado_usuario['data']:
            estado_usuario['data']['datos_tasacion'] = {}
        
        estado_usuario['data']['datos_tasacion']['operacion'] = ops[text_lower]
        estado_usuario['paso'] = 'tasacion_barrio'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Después de seleccionar operación, preguntar barrio
        platform = estado_usuario.get('platform', 'whatsapp')
        if platform in ['whatsapp', 'whatsapp_business']:
            return "📍 *¿En qué barrio se encuentra la propiedad?* (ej: Palermo, Belgrano, Tigre...)"
        else:
            return "📍 *¿En qué barrio se encuentra la propiedad?*\n\nEjemplo: Palermo, Belgrano, Tigre, etc."
    else:
        return "⚠️ Por favor, elegí 1 para Venta o 2 para Alquiler."


def manejar_reintentar_tasacion(estado_usuario, user_id):
    """
    Maneja el reintento de tasación.
    Reinicia el flujo desde la pregunta del barrio.
    """
    user_id_str = str(user_id)
    log(f"🔄 Reintentando tasación para usuario {user_id_str}")
    
    # Obtener o crear estado del usuario
    from database import obtener_estado_usuario, actualizar_estado_usuario
    
    # Asegurar que estado_usuario tenga la estructura correcta
    if 'data' not in estado_usuario or not isinstance(estado_usuario['data'], dict):
        estado_usuario['data'] = {}
    
    # Verificar si ya tenemos operación guardada
    datos_tasacion = estado_usuario['data'].get('datos_tasacion', {})
    
    if datos_tasacion.get('operacion'):
        # Si ya tenía operación, preguntar directamente por el barrio
        estado_usuario['paso'] = 'tasacion_barrio'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        platform = estado_usuario.get('platform', 'whatsapp')
        if platform in ['whatsapp', 'whatsapp_business']:
            return "📍 *Perfecto, reiniciemos la tasación.*\n\n¿En qué barrio se encuentra la propiedad? (ej: Palermo, Belgrano, Tigre...)"
        else:
            return "📍 *Perfecto, reiniciemos la tasación.*\n\n¿En qué barrio se encuentra la propiedad?\n\nEjemplo: Palermo, Belgrano, Tigre, etc."
    else:
        # Si no hay operación, volver a preguntar operación primero
        estado_usuario['paso'] = 'tasacion_operacion'
        estado_usuario['data']['datos_tasacion'] = {}
        actualizar_estado_usuario(user_id, estado_usuario)
        
        return manejar_menu_tasacion(None, estado_usuario, user_id)


def manejar_tasacion_barrio(text, estado_usuario, user_id):
    """Guarda el barrio y muestra menú de tipos con emojis numéricos"""
    barrio = text.strip()
    datos_tasacion = estado_usuario['data'].get('datos_tasacion', {})
    operacion = datos_tasacion.get('operacion', 'venta')
    
    try:
        map_path = os.path.join(os.path.dirname(__file__), "market_valuation_map.json")
        if not os.path.exists(map_path):
            return _respuesta_rechazo_tasacion(estado_usuario, user_id)
        
        with open(map_path, 'r', encoding='utf-8') as f:
            vmap = json.load(f)
        
        barrio_key = barrio.lower().strip()
        
        if barrio_key not in vmap:
            log(f"❌ Tasación rechazada: Barrio '{barrio_key}' no existe")
            return _respuesta_rechazo_tasacion(estado_usuario, user_id)
        
        if 'datos_tasacion' not in estado_usuario['data']:
            estado_usuario['data']['datos_tasacion'] = {}
        
        estado_usuario['data']['datos_tasacion']['barrio'] = barrio
        estado_usuario['paso'] = 'tasacion_tipo'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram")
        
        if es_fb_ig:
            # Facebook/Instagram: texto con emojis numéricos
            return {
                "type": "text",
                "body": "🏠 *¿Qué tipo de propiedad es?*\n\n1️⃣ Departamento\n2️⃣ Casa\n3️⃣ PH\n4️⃣ Oficina / Local\n5️⃣ Terreno\n\n🔙 M. Volver\n❌ S. Salir",
                "preview": False
            }
        else:
            
            return {
                "type": "interactive_list",
                "body": "🏠 *¿Qué tipo de propiedad es?*\n\nSelecciona una opción 👇",
                "button_text": "Tipos",
                "sections": [
                    {
                        "title": "Tipo de Propiedad",
                        "rows": [
                            {"id": "1", "title": "Departamento"},
                            {"id": "2", "title": "Casa"},
                            {"id": "3", "title": "PH"},
                            {"id": "4", "title": "Oficina / Local"},
                            {"id": "5", "title": "Terreno"},
                            {"id": "M", "title": "↩️ Volver al menú anterior"},
                            {"id": "S", "title": "❌ Salir"}
                        ]
                    }
                ]
            }

            # WhatsApp: lista interactiva
            # return {
            #     "type": "interactive_list",
            #     "body": "🏠 *¿Qué tipo de propiedad es?*",
            #     "button_text": "Tipos",
            #     "sections": [
            #         {
            #             "title": "Tipo de Propiedad",
            #             "rows": [
            #                 {"id": "1", "title": "Departamento"},
            #                 {"id": "2", "title": "Casa"},
            #                 {"id": "3", "title": "PH"},
            #                 {"id": "4", "title": "Oficina / Local"},
            #                 {"id": "5", "title": "Terreno"}
            #             ]
            #         }
            #     ],
            #     "footer": "Ⓜ️ Envía 'M' para Volver | ❌ Envía 'S' para Salir"
            # }
        
    except Exception as e:
        log(f"⚠️ Error verificando barrio: {e}")
        return _respuesta_rechazo_tasacion(estado_usuario, user_id)
    
    
    
    
def manejar_tasacion_tipo(text_lower, estado_usuario, user_id):
    """
    Guarda el tipo y Verifica INMEDIATAMENTE la combinación completa.
    Si no existe → rechazar tasación inmediatamente.
    """
    tipos = {
        "1": "Departamento",
        "2": "Casa",
        "3": "PH",
        "4": "Oficina",
        "5": "Terreno"
    }
    
    if text_lower not in tipos:
        return "⚠️ Por favor, elegí una opción válida (1 al 5)."
    
    tipo = tipos[text_lower]
    datos_tasacion = estado_usuario['data'].get('datos_tasacion', {})
    barrio = datos_tasacion.get('barrio')
    operacion = datos_tasacion.get('operacion', 'venta')
    
    if not barrio:
        log(f"❌ Error: No hay barrio guardado al seleccionar tipo")
        return _respuesta_rechazo_tasacion(estado_usuario, user_id)
    
    # VERIFICACIÓN INMEDIATA de la combinación completa
    es_valido = verificar_combinacion_valida(barrio, tipo, operacion)
    
    if not es_valido:
        log(f"❌ Tasación rechazada: Combinación inválida - Barrio:'{barrio}' Tipo:'{tipo}' Operación:'{operacion}'")
        return _respuesta_rechazo_tasacion(estado_usuario, user_id)
    
    # Si es válido, guardar y continuar
    if 'datos_tasacion' not in estado_usuario['data']:
        estado_usuario['data']['datos_tasacion'] = {}
    
    estado_usuario['data']['datos_tasacion']['tipo'] = tipo
    estado_usuario['paso'] = 'tasacion_m2'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    if platform in ['whatsapp', 'whatsapp_business']:
        return "📏 *¿Cuántos m² cubiertos tiene la propiedad?* (Ingresá solo el número, ej: 65)"
    else:
        return "📏 *¿Cuántos m² cubiertos tiene la propiedad?*\n\nIngresá solo el número (ej: 65, 120, 200)"


def manejar_tasacion_m2(text, estado_usuario, user_id):
    """Guarda los m2 e inicia la carga de ambientes (o finaliza si es Terreno)"""
    try:
        m2_str = text.replace(',', '.').strip()
        m2 = float(m2_str)
        
        if m2 < 5 or m2 > 10000:
            return "⚠️ Por favor, ingresá un número válido de m² (entre 5 y 10000).\n\nEjemplo: 65, 120, 200, etc."
        
        if 'datos_tasacion' not in estado_usuario['data']:
            estado_usuario['data']['datos_tasacion'] = {}
            
        estado_usuario['data']['datos_tasacion']['m2'] = m2
        datos = estado_usuario['data']['datos_tasacion']
        
        # SI ES TERRENO, SALTAR AMBIENTES Y ESTADO
        if datos.get('tipo') == 'Terreno':
            log(f"🌱 Propiedad tipo Terreno detectada para {user_id}. Saltando pasos adicionales.")
            datos['ambientes'] = 1
            datos['estado'] = 'Bueno'
            actualizar_estado_usuario(user_id, estado_usuario)
            return _finalizar_tasacion_y_responder(user_id, estado_usuario, datos)
            
        estado_usuario['paso'] = 'tasacion_ambientes'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        platform = estado_usuario.get('platform', 'whatsapp')
        if platform in ['whatsapp', 'whatsapp_business']:
            return "🔢 *¿Cuántos ambientes tiene?* (ej: 3)"
        else:
            return "🔢 *¿Cuántos ambientes tiene?*\n\nEjemplo: 1, 2, 3, 4"
        
    except ValueError:
        log(f"⚠️ Error: No se pudo convertir '{text}' a número")
        return "⚠️ Por favor, ingresá un número válido para los metros cuadrados (usa . para decimales si es necesario).\n\nEjemplo: 65, 120.5, 200"
    except Exception as e:
        log(f"🔥 Error crítico en manejar_tasacion_m2: {e}")
        return "⚠️ Por favor, ingresá un número válido para los metros cuadrados."


def manejar_tasacion_ambientes(text, estado_usuario, user_id):
    """Guarda ambientes e inicia la carga de estado con emojis numéricos"""
    try:
        amb_str = "".join(filter(str.isdigit, text))
        ambientes = int(amb_str) if amb_str else 0
        
        if ambientes < 1:
            return "⚠️ Por favor, ingresá un número válido de ambientes (mínimo 1).\n\nEjemplo: 1, 2, 3, etc."
        
        if 'datos_tasacion' not in estado_usuario['data']:
            estado_usuario['data']['datos_tasacion'] = {}
            
        estado_usuario['data']['datos_tasacion']['ambientes'] = ambientes
        estado_usuario['paso'] = 'tasacion_estado'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram")
        
        if es_fb_ig:
            # Facebook/Instagram: texto con emojis numéricos
            return {
                "type": "text",
                "body": "🏗️ *¿En qué estado se encuentra la propiedad?*\n\n1️⃣ Excelente / A estrenar\n2️⃣ Muy bueno\n3️⃣ Bueno\n4️⃣ Regular\n5️⃣ A refaccionar\n\n🔙 M. Volver\n❌ S. Salir",
                "preview": False
            }
        else:
            # WhatsApp: lista interactiva
            return {
                "type": "interactive_list",
                "body": "🏗️ *¿En qué estado se encuentra la propiedad?*",
                "button_text": "Estado",
                "sections": [
                    {
                        "title": "Condición",
                        "rows": [
                            {"id": "1", "title": "Excelente / A estrenar"},
                            {"id": "2", "title": "Muy bueno"},
                            {"id": "3", "title": "Bueno"},
                            {"id": "4", "title": "Regular"},
                            {"id": "5", "title": "A refaccionar"}
                        ]
                    }
                ],
                "footer": "Ⓜ️ Envía 'M' para Volver | ❌ Envía 'S' para Salir"
            }
    except Exception as e:
        log(f"⚠️ Error en manejar_tasacion_ambientes: {e}")
        return "⚠️ Por favor, ingresá un número para los ambientes. (Ejemplo: 2, 3, 4)"
    
    

def manejar_tasacion_estado(text_lower, estado_usuario, user_id):
    """Finaliza la recolección de datos y muestra la tasación"""
    estados = {
        "1": "Excelente",
        "2": "Muy bueno",
        "3": "Bueno",
        "4": "Regular",
        "5": "A refaccionar"
    }
    
    if text_lower in estados:
        if 'datos_tasacion' not in estado_usuario['data']:
            log(f"❌ Error: datos_tasacion no encontrado")
            return _respuesta_rechazo_tasacion(estado_usuario, user_id)
            
        datos = estado_usuario['data']['datos_tasacion']
        campos_requeridos = ['barrio', 'tipo', 'm2', 'ambientes']
        
        for campo in campos_requeridos:
            if campo not in datos or datos[campo] is None:
                log(f"❌ Error: Campo '{campo}' faltante")
                return _respuesta_rechazo_tasacion(estado_usuario, user_id)
        
        try:
            datos['m2'] = float(datos['m2'])
            datos['ambientes'] = int(datos['ambientes'])
        except (ValueError, TypeError) as e:
            log(f"❌ Error al convertir: {e}")
            return _respuesta_rechazo_tasacion(estado_usuario, user_id)
        
        datos['estado'] = estados[text_lower]
        actualizar_estado_usuario(user_id, estado_usuario)
        
        log(f"✅ Datos completos, procediendo a tasación")
        return _finalizar_tasacion_y_responder(user_id, estado_usuario, datos)
    else:
        return "⚠️ Por favor, elegí una opción válida (1 al 5)."


def _respuesta_rechazo_tasacion(estado_usuario, user_id):
    """
    Respuesta unificada para rechazo de tasación.
    """
    # Limpiar datos de tasación
    if 'data' in estado_usuario and 'datos_tasacion' in estado_usuario['data']:
        estado_usuario['data']['datos_tasacion'] = {}
    
    estado_usuario['paso'] = 'tasacion_operacion'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram")
    
    if es_fb_ig:
        # Facebook/Instagram: texto plano con numeración simple 1., 2., 3.
        return {
            "type": "text",
            "body": "❌ *Tasación no disponible*\n\nNo contamos con datos suficientes para esta combinación.\n\n*Acciones:*\n\n1. 📈 Reintentar Tasación\n2. 👤 Hablar con Asesor\n3. 🔙 Volver al Menú\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        # WhatsApp: botones interactivos
        return WhatsAppResponse.buttons(
            header="Tasación no disponible",
            body="Tasación no disponible: no contamos con datos suficientes para esta combinación.\n\n¿Deseas intentar con otros datos, volver al menú o hablar con un asesor?",
            buttons=[
                {"id": "10", "title": "📈 Reintentar Tasación"},
                {"id": "5", "title": "👤 Hablar con Asesor"},
                {"id": "m", "title": "🔙 Volver al Menú"}
            ]
        )

def _finalizar_tasacion_y_responder(user_id, estado_usuario, datos):
    """Calcula la tasación (ya validada) y responde adaptado a la plataforma"""
    try:
        # Obtener datos de tasación (ya sabemos que es válido por la validación previa)
        tasacion = obtener_tasacion_local(
            datos['barrio'], 
            datos['tipo'], 
            datos['estado'],
            datos.get('operacion', 'venta')
        )
        
        # Esto no debería fallar porque ya validamos antes, pero por seguridad:
        if not tasacion:
            log(f"⚠️ Tasación no disponible a pesar de validación previa")
            return _respuesta_rechazo_tasacion(estado_usuario, user_id)
        
        # Aplicar ajuste de estado
        ajustes = {"Excelente": 1.10, "Muy bueno": 1.05, "Bueno": 1.00, "Regular": 0.85, "A refaccionar": 0.70}
        factor = ajustes.get(datos['estado'], 1.0)
        valor_estimado = tasacion['precio_m2'] * float(datos['m2']) * factor
        valor_redondeado = round(valor_estimado, -2)
        
        # Registrar Lead exitoso
        detalles = f"Tasación exitosa: {datos['tipo']} en {datos['barrio']}, {datos['m2']}m2, {datos['ambientes']} amb, estado {datos['estado']}, operación {datos.get('operacion', 'venta')}. Resultado: {valor_redondeado:,.0f} {tasacion['moneda']}"
        registrar_lead(user_id, "TASACION_VIRTUAL", "tasacion", detalles)
        notificar_agente(f"📈 *NUEVO LEAD DE TASACIÓN*\n📞 Tel: +{user_id}\n📝 {detalles}")
        
        # Construir respuesta
        muestra = tasacion.get("muestra", 0)
        fuentes_str = ", ".join(tasacion.get("fuentes", ["Mercado Local"]))
        
        # Detectar plataforma
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram")
        
        # Texto base del resultado
        operacion_texto = "venta" if datos.get('operacion', 'venta') == 'venta' else "alquiler"
        mensaje_base = f"""📊 *RESULTADO DE TU TASACIÓN VIRTUAL*

Basado en el análisis estadístico de mercado para *{datos['barrio']}* ({operacion_texto}):

🏠 *Propiedad:* {datos['tipo']}
📏 *Superficie:* {datos['m2']} m²
💰 *Valor estimado:* {tasacion['moneda']} ${valor_redondeado:,.0f}
📈 *Precio promedio m²:* {tasacion['moneda']} ${tasacion['precio_m2']:,.0f}

🔍 *Análisis:* basado en {muestra} propiedades de {fuentes_str}.

⚠️ *Nota:* Esta es una estimación orientativa basada en datos de mercado. Para una tasación profesional, un asesor debe visitar la propiedad."""

        if es_fb_ig:
            # Facebook/Instagram: texto con EMOJIS NUMÉRICOS
            mensaje_completo = (
                f"{mensaje_base}\n\n"
                "*¿Qué deseas hacer?*\n\n"
                "1️⃣ ✅ Deseas una Tasación Profesional - Con visita de asesor\n"
                "2️⃣ ⏭️ No por ahora - Continuar explorando\n"
                "3️⃣ 🔙 Menú Principal - Ir al inicio\n"
                "4️⃣ ❌ Salir - Terminar sesión\n\n"
                "💡 *Envía el número de la opción deseada*"
            )
            
            estado_usuario['paso'] = 'tasacion_esperando_contacto'
            actualizar_estado_usuario(user_id, estado_usuario)
            
            return {
                "type": "text",
                "body": mensaje_completo,
                "preview": False
            }
        else:
            # WhatsApp: lista interactiva
            estado_usuario['paso'] = 'tasacion_esperando_contacto'
            actualizar_estado_usuario(user_id, estado_usuario)
            
            return WhatsAppResponse.list_menu(
                body=mensaje_base,
                button_text="Opciones",
                sections=[
                    {
                        "title": "Acciones",
                        "rows": [
                            {"id": "1", "title": "✅ Deseas una Tasación", "description": "Profesional con visita"},
                            {"id": "2", "title": "⏭️ No por ahora", "description": "Continuar explorando"},
                            {"id": "m", "title": "🔙 Menú Principal", "description": "Ir al inicio"},
                            {"id": "s", "title": "❌ Salir", "description": "Terminar sesión"}
                        ]
                    }
                ],
                footer="Selecciona una opción 👇"
            )
        
    except Exception as e:
        log(f"🔥 Error en _finalizar_tasacion_y_responder: {e}")
        import traceback
        log(traceback.format_exc())
        return "❌ Ocurrió un error al procesar la tasación. Por favor contacta a un asesor enviando '5'."
    

def manejar_tasacion_contacto(text_lower, estado_usuario, user_id):
    """Maneja la respuesta final del flujo de tasación"""
    text_normalized = text_lower.lower().strip()
    
    # Detectar plataforma
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram")
    
    # Mapeo de opciones para Facebook/Instagram (con números)
    if es_fb_ig:
        opciones = {
            "1": "1",
            "1️⃣": "1",
            "2": "2",
            "2️⃣": "2",
            "3": "menu",
            "3️⃣": "menu",
            "m": "menu",
            "4": "salir",
            "4️⃣": "salir",
            "s": "salir"
        }
        comando = opciones.get(text_normalized, text_normalized)
    else:
        # Mapeo para WhatsApp
        mapeo_botones = {
            "1": "1",
            "2": "2",
            "m": "menu",
            "s": "salir"
        }
        comando = mapeo_botones.get(text_normalized, text_normalized)
    
    if comando == "1":
        notificar_agente(f"📞 *SOLICITUD DE TASACIÓN PROFESIONAL*\n📞 Tel: +{user_id}\nEl cliente solicitó contacto humano después de la tasación virtual.")
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "✅ ¡Perfecto! Un asesor se pondrá en contacto con vos a la brevedad para coordinar la visita. ¡Gracias por confiar en nosotros! 🏠🗝️"
    
    elif comando == "menu":
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "WELCOME_FLOW_TRIGGER"
    
    elif comando == "salir":
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "¡Gracias por confiar en Dante Propiedades! 🏠🗝️"
    
    else:
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "Entendido. Si necesitás algo más, acá estoy. 😊"