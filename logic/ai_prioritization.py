import json
from datetime import datetime
from logic.gemini_client import call_gemini_with_rotation

def obtener_prioridad_lead(user_id, historial, propiedad_info):
    """
    Analiza el historial de conversación y la propiedad para determinar la prioridad del lead.
    Retorna un diccionario con 'score', 'label' y 'razonamiento'.
    """
    if not historial:
        return {"score": 5, "label": "⚡ WARM", "razonamiento": "Sin historial previo suficiente para análisis profundo."}

    # Formatear el historial para el prompt
    chat_text = "\n".join([f"{m['role']}: {m['text']}" for m in historial])
    
    prompt = f"""
Eres un experto en ventas inmobiliarias y psicología del consumidor. 
Tu tarea es analizar el historial de chat de un cliente interesado en una propiedad y determinar su nivel de interés y urgencia ("Temperatura").

PROPIEDAD:
- Título: {propiedad_info.get('titulo', 'N/A')}
- Precio: {propiedad_info.get('precio', 'N/A')} {propiedad_info.get('moneda_precio', 'USD')}
- Ubicación: {propiedad_info.get('barrio', 'N/A')}

HISTORIAL DE CHAT:
{chat_text}

CRITERIOS DE CALIFICACIÓN:
- 🔥 HOT (8-10): Usuario con intención clara de visitar, preguntas específicas sobre condiciones de compra/alquiler, o expresión de urgencia.
- ⚡ WARM (5-7): Usuario explorando, pide detalles básicos, responde positivamente pero sin compromiso inmediato.
- ❄️ COLD (1-4): Consultas vagas, errores de tipeo frecuentes, o interés que parece accidental/curiosidad leve.

RESPONDE ÚNICAMENTE EN FORMATO JSON:
{{
  "score": número del 1 al 10,
  "label": "HOT", "WARM" o "COLD",
  "razonamiento": "Breve explicación de 1 oración en español"
}}
"""
    try:
        response_text = call_gemini_with_rotation(prompt)
        
        # Limpiar posible formato markdown del JSON
        clean_json = response_text.replace('```json', '').replace('```', '').strip()
        result = json.loads(clean_json)
        
        # Mapear label a emoji
        emojis = {"HOT": "🔥 HOT", "WARM": "⚡ WARM", "COLD": "❄️ COLD"}
        result['label_emoji'] = emojis.get(result.get('label', 'WARM'), "⚡ WARM")
        
        return result
    except Exception as e:
        print(f"⚠️ Error en análisis de prioridad IA: {e}")
        return {"score": 5, "label": "WARM", "label_emoji": "⚡ WARM", "razonamiento": "Error técnico en el análisis de IA."}
