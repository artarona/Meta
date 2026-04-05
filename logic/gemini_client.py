import os
from google import genai
from google.genai import types
from typing import Optional, Dict, Any, List

# ============================================================
# CONFIGURACIÓN DE API KEYS DE GEMINI
# ============================================================
# ORDEN DE PRIORIDAD:
# 1. Si hay clave manual en MANUAL_API_KEY, usar SOLO esa
# 2. Si no, buscar en variables de entorno GEMINI_KEYS_1, GEMINI_KEYS_2, etc.

# ✅ CLAVE MANUAL - USAR ESTA SIEMPRE
# ✅ CLAVE MANUAL - COMENTADA PARA USAR .ENV
# MANUAL_API_KEY = "AIzaSyDD_34SenFY8w_tf5Vr311v3ZLVwny_saw"

# Inicializar lista de claves
API_KEYS = []

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Buscar claves en variables de entorno (formato: GEMINI_KEY_1, GEMINI_KEY_2, etc.)
for i in range(1, 10):
    key_name = f"GEMINI_KEY_{i}"
    key_value = os.environ.get(key_name)
    if key_value and key_value.strip():
        if key_value.strip().startswith('AIza'):
            API_KEYS.append(key_value.strip())
            print(f"✅ {key_name}: Clave cargada exitosamente")

# Si no hay claves, intentar con variable simple o usar los fallbacks de config.py
if not API_KEYS:
    single_key = os.environ.get("GEMINI_API_KEY")
    if single_key and single_key.strip().startswith('AIza'):
        API_KEYS.append(single_key.strip())
        print(f"✅ GEMINI_API_KEY: Clave cargada")
    else:
        # Claves de respaldo (mismas que en config.py)
        API_KEYS = [
            "AIzaSyCf_UBys6b4_uceLlN3HtVVy64W_MLkpcw",
            "AIzaSyBIRmNG2iJVWieK5Z4qY5xWpJWzQwlrkow"
        ]
        print(f"⚠️ Usando {len(API_KEYS)} claves de respaldo (fallback)")

# Modelo a usar
MODEL = os.environ.get("WORKING_MODEL", "gemini-2.0-flash-001")

print(f"🎯 CONFIGURACIÓN FINAL: Modelo={MODEL}")
print(f"🔑 Claves API disponibles: {len(API_KEYS)}")
print("=" * 50)

def call_gemini_with_rotation(prompt: str) -> str:
    """Función para llamar a Gemini API con rotación de claves"""
    print(f"🎯 INICIANDO ROTACIÓN DE CLAVES")
    print(f"🔧 Modelo: {MODEL}")
    print(f"🔑 Claves disponibles: {len(API_KEYS)}")
    
    if not API_KEYS:
        print("⚠️ No hay API keys configuradas, usando modo básico")
        return get_fallback_response()
    
    for i, key in enumerate(API_KEYS):
        try:
            print(f"🔄 Probando clave {i+1}/{len(API_KEYS)}...")
            
            # ✅ CONFIGURACIÓN EXPLÍCITA
            client = genai.Client(api_key=key)
            
            print(f"   📝 Prompt length: {len(prompt)} caracteres")
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=4000,
                )
            )
            
            print(f"   ✅ Respuesta recibida, partes: {len(response.candidates[0].content.parts) if response.candidates and response.candidates[0].content.parts else 0}")
            
            if not response.candidates or not response.candidates[0].content.parts:
                raise Exception("Respuesta vacía de Gemini")
            
            answer = response.text.strip()
            print(f"✅ Éxito con clave {i+1}")
            print(f"   📄 Respuesta: {answer[:100]}...")
            return answer

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            print(f"❌ ERROR Clave {i+1}:")
            print(f"   🏷️  Tipo: {error_type}")
            print(f"   📄 Mensaje: {error_msg}")
            
            if "429" in error_msg:
                print(f"   💡 Clave {i+1} agotada (rate limit)")
            elif "401" in error_msg or "PermissionDenied" in error_type or "API_KEY_INVALID" in error_msg:
                print(f"   💡 Clave {i+1} no autorizada/inválida")
            elif "quota" in error_msg.lower():
                print(f"   💡 Clave {i+1} sin quota")
            elif "503" in error_msg or "500" in error_msg:
                print(f"   💡 Error del servidor Gemini")
            elif "403" in error_msg or "leaked" in error_msg.lower():
                print(f"   💡 Clave {i+1} reportada como filtrada - usar nueva key")
            else:
                print(f"   💡 Error desconocido")
    
    print("💥 TODAS las claves fallaron - usando modo básico")
    return get_fallback_response()

def get_fallback_response():
    """Respuesta de fallback cuando Gemini no funciona"""
    return "🤖 **Dante Propiedades**\n\n¡Hola! La aplicación está funcionando pero hay un problema temporal con el servicio de IA.\n\n**Sistema disponible:**\n✅ Búsqueda de propiedades\n✅ Filtros por barrio, precio, tipo\n✅ Base de datos cargada\n\n⚠️ **El modo conversacional IA está temporalmente desactivado.**\n\n**Cómo usar:**\n1. Escribí tu búsqueda (ej: \"departamento en palermo\")\n2. La app encontrará propiedades relevantes\n3. Usá los filtros para refinar resultados\n\n🏠 **¡La búsqueda de propiedades funciona perfectamente!**"

def build_prompt(user_text, results=None, filters=None, channel="web", style_hint="", property_details=None):
    whatsapp_tone = channel == "whatsapp"
    
    if property_details:
        property_context = f"""
📍 **PROPIEDAD ENCONTRADA:**

**📝 Descripción:** {property_details.get('descripcion', 'Sin descripción')}
**💰 Precio:** {property_details.get('precio', 'Consultar')}
**📐 Superficie:** {property_details.get('superficie', 'N/D')}m²
**🛏️ Ambientes:** {property_details.get('ambientes', 'N/D')}
**📅 Antigüedad:** {property_details.get('antiguedad', 'N/D')}
**📍 Ubicación:** {property_details.get('ubicacion', 'No especificada')}
**🏷️ Tipo:** {property_details.get('tipo', 'Propiedad')}
**📋 Características:** {', '.join(property_details.get('caracteristicas', [])) or 'Consultar'}
**✅ Estado:** {property_details.get('estado', 'Disponible')}
"""
        
        base_prompt = f"""
Eres Dante, un asistente experto en propiedades en Buenos Aires.

{property_context}

El usuario preguntó: "{user_text}"

Tu tarea es:
1. Responder de manera útil y natural sobre esta propiedad
2. Mencionar los detalles clave de la propiedad
3. Si es necesario, preguntar si quiere ver más propiedades similares
4. Mantener un tono profesional pero amigable

Responde de forma concisa y directa.
"""
        return base_prompt
    
    if results is not None and results:
        return build_conversational_prompt(user_text, results, filters, whatsapp_tone)
    else:
        return build_conversational_prompt(user_text, results, filters, whatsapp_tone)

def build_conversational_prompt(user_text: str, results=None, filters=None, whatsapp_tone=False):
    """Construye el prompt conversacional"""
    
    property_types = {
        'departamento': ['depto', 'departamento', 'ph', 'apartamento'],
        'casa': ['casa', 'chalet', 'casaquinta', 'townhouse'],
        'terreno': ['terreno', 'lote', ' parcela', 'solar'],
        'oficina': ['oficina', 'local comercial', 'comercial', 'ph comercial'],
    }
    
    detected_type = 'propiedad'
    for ptype, keywords in property_types.items():
        if any(kw in user_text.lower() for kw in keywords):
            detected_type = ptype
            break
    
    intent = "consulta"
    if any(kw in user_text.lower() for kw in ['alquiler', 'alquilar', 'alquilo', 'rent']):
        intent = "alquiler"
    elif any(kw in user_text.lower() for kw in ['venta', 'vender', 'comprar', 'venta']):
        intent = "venta"
    elif any(kw in user_text.lower() for kw in ['precio', 'cuanto', 'valor', 'cuesta']):
        intent = "precio"
    elif any(kw in user_text.lower() for kw in ['ubicación', 'donde', 'zona', 'barrio', 'dirección']):
        intent = "ubicacion"
    elif any(kw in user_text.lower() for kw in ['características', 'caracteristicas', 'ambientes', 'metros', 'superficie']):
        intent = "caracteristicas"
    
    if whatsapp_tone:
        prompt = f"""Eres Dante, un asistente especializado en propiedades en Buenos Aires.

El usuario dice: "{user_text}"

Contexto: Tipo de propiedad: {detected_type} | Intención: {intent} | Filtros: {filters or 'ninguno'}
"""
    else:
        prompt = f"""Eres Dante, un asistente especializado en propiedades en Buenos Aires.

User input: "{user_text}"

Context: Property type: {detected_type} | Intent: {intent} | Filters: {filters or 'none'}
"""
    
    if results is not None and results:
        count = len(results)
        prompt += f"""
📊 Hay {count} propiedades que coinciden con la búsqueda.
"""
    
    prompt += """
Tu objetivo es:
- Entender la necesidad del usuario
- Responder de manera útil y natural
- Sugerir próximos pasos si corresponde
- Mantener un tono profesional pero amigable

Responde de forma concisa (máximo 2-3 oraciones).
"""
    
    return prompt
