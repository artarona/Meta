import os
import json
import openai
from database import cargar_propiedades_cached

# Load OpenAI key from environment variables (must be set in Render or .env)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

def es_consulta_portal(mensaje):
    """Detecta si un mensaje parece provenir de un portal inmobiliario"""
    mensaje = mensaje.lower()
    keywords = ["zonaprop", "argenprop", "mercado libre", "mercadolibre", "vi esta propiedad", "me interesa la propiedad", "info sobre el aviso", "te contacto por"]
    # Check if keyword in message or if there is an URL
    if any(k in mensaje for k in keywords) or "http" in mensaje or "www." in mensaje:
        return True
    return False

def extraer_id_propiedad_con_ia(mensaje, propiedades):
    """Usa IA (gpt-4o-mini) para detectar de qué propiedad habla el cliente."""
    if not openai.api_key:
        # Fallback básico si no hay API key
        for p in propiedades:
            if p.get('id_temporal') and p.get('id_temporal').lower() in mensaje.lower():
                return p.get('id_temporal')
        return None
    
    catalogo = []
    for p in propiedades:
        titulo = p.get('titulo', '')
        direccion = p.get('direccion', '')
        barrio = p.get('barrio', '')
        precio = p.get('precio', '')
        moneda = p.get('moneda_precio', '')
        id_temp = p.get('id_temporal', '')
        catalogo.append(f"ID: {id_temp} | {titulo} | {direccion}, {barrio} | Precio: {precio} {moneda}")
    
    sys_prompt = (
        f"Sos un asistente interno. El cliente envió este mensaje de WhatsApp: '{mensaje}'.\n"
        f"Tenemos estas propiedades en la base de datos:\n"
        f"{chr(10).join(catalogo)}\n\n"
        "Analizá el mensaje (puede tener links, direcciones, barrios o precios). "
        "Respondé ÚNICAMENTE con el 'ID' exacto de la propiedad a la que se refiere. "
        "Si estás seguro, respondé el ID (ejemplo: PROP-DANTE-11). "
        "Si no lográs identificar ninguna propiedad con certeza o hay ambigüedad, respondé 'NINGUNA'."
    )
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": sys_prompt}],
            max_tokens=20,
            temperature=0
        )
        respuesta = response.choices[0].message.content.strip()
        # Limpiar la respuesta por si la IA agregó puntos o comillas
        respuesta = respuesta.replace('"', '').replace('.', '').replace("'", "").strip()
        
        # Verificar que el ID exista realmente
        if respuesta != "NINGUNA" and any(p.get('id_temporal') == respuesta for p in propiedades):
            return respuesta
    except Exception as e:
        print(f"Error IA identificación de propiedad: {e}")
    
    # Fallback textual
    for p in propiedades:
        if p.get('id_temporal') and p.get('id_temporal').lower() in mensaje.lower():
            return p.get('id_temporal')
            
    return None

def cargar_entorno(barrio):
    """Carga y devuelve los datos del barrio desde entorno.json"""
    try:
        ruta_entorno = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entorno.json")
        if not os.path.exists(ruta_entorno):
            return None
            
        with open(ruta_entorno, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            
        if not barrio: return None
            
        b = barrio.lower().strip()
        # Búsqueda difusa simple
        for key_barrio, info_barrio in datos.items():
            if key_barrio in b or b in key_barrio:
                return info_barrio
    except Exception as e:
        print(f"Error cargando entorno.json: {e}")
        
    return None

def generar_respuesta_ia(mensaje, historial_mensajes, propiedad_id):
    """
    Genera la respuesta conversacional.
    historial_mensajes debe ser una lista de dicts: [{'role': 'user', 'content': '...'}, ...]
    Retorna (texto_respuesta, intencion)
    """
    if not openai.api_key:
        return "⚠️ La inteligencia artificial no está configurada (Falta OPENAI_API_KEY en el servidor). Contactando a un asesor...", "FALLBACK"
        
    propiedades = cargar_propiedades_cached()
    propiedad = next((p for p in propiedades if p.get('id_temporal') == propiedad_id), None)
    
    if not propiedad:
        return "Disculpá, no logré encontrar la ficha de esta propiedad en nuestra base activa. Un asesor te responderá a la brevedad.", "FALLBACK"
        
    entorno = cargar_entorno(propiedad.get('barrio', ''))
    
    # Formatear contexto para que sea fácil de leer por la IA pero no consuma tantos tokens
    prop_simplificada = {k: v for k, v in propiedad.items() if k not in ['fotos', 'imagenes']}
    contexto_prop = json.dumps(prop_simplificada, ensure_ascii=False, indent=2)
    
    if entorno:
        # Extraer solo lo más importante del entorno (scoring, descripcion general, transporte)
        entorno_simplificado = {
            "descripcion": entorno.get("descripcion_general"),
            "transporte": entorno.get("transporte", {}).get("descripcion"),
            "seguridad": entorno.get("seguridad", {}).get("descripcion"),
            "comercios": entorno.get("comercio", {}).get("descripcion")
        }
        contexto_entorno = json.dumps(entorno_simplificado, ensure_ascii=False, indent=2)
    else:
        contexto_entorno = "Información específica del barrio no disponible."
    
    sys_prompt = f"""Sos el Asesor Inmobiliario Inteligente de Dante Propiedades.
Tu principal objetivo es VENDER VISITAS a las propiedades. El usuario está interesado en esta propiedad.

REGLAS DE ORO:
1. Tono y Personalidad: Sos amable, argentino y porteño (usá vos, tratá de usted solo a gente mayor, usá expresiones cálidas pero súper profesionales).
2. Respuestas Concisas: Estás en WhatsApp. NO envíes bloques enormes de texto. Respondé puntualmente a lo que el usuario preguntó basándote en la ficha.
3. Vender la Zona: Si preguntan sobre la ubicación, usá los datos del Barrio para destacar por qué es excelente opción.
4. Call to Action CONSTANTE: Al final de tu explicación, INVITÁ al cliente a dar el siguiente paso (ir a verla). Ejemplo: "¿Te gustaría que arreglemos una visita para esta semana?".
5. TRIGGER DE AGENDAMIENTO: Si el cliente muestra una intención CLARA de querer visitar, agendar, ir a ver la propiedad, o pide coordinar horario, DEBÉS colocar al final de tu mensaje el texto exacto: >>>AGENDAR_CITA<<<. Si pones esto, el sistema tomará el control para reservar en el calendario. NO lo pongas si solo están preguntando el precio.

--- FICHA DE LA PROPIEDAD ---
{contexto_prop}

--- INFORMACIÓN DEL BARRIO ---
{contexto_entorno}
"""

    messages = [{"role": "system", "content": sys_prompt}]
    
    # Agregar historial evitando que crezca infinito (max 6 ultimos msjs)
    if isinstance(historial_mensajes, list):
        messages.extend(historial_mensajes[-6:])
        
    # Agregamos el mensaje actual
    messages.append({"role": "user", "content": mensaje})

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=300,
            temperature=0.7
        )
        respuesta = response.choices[0].message.content.strip()
        
        # Detectar el trigger
        intent = "CHARLA"
        if ">>>AGENDAR_CITA<<<" in respuesta:
            intent = "AGENDAR"
            respuesta = respuesta.replace(">>>AGENDAR_CITA<<<", "").strip()
            
        return respuesta, intent
        
    except Exception as e:
        print(f"Error OpenAI Generación: {e}")
        return "Hubo una interrupción en mi sistema de análisis. Aguardá un momento, le aviso a un humano para que te asista 😊.", "FALLBACK"
