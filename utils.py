import re
import json
import os
from datetime import datetime, timedelta
from config import *

def normalizar_numero_argentina(numero):
    """
    Normaliza el número para la API de WhatsApp.
    En producción (E.164), se prefiere mantener el formato original sin el '15' 
    que se usaba en el Sandbox de Meta.
    """
    if not numero:
        return numero
    
    # Limpiar caracteres no numéricos
    numero = ''.join(filter(str.isdigit, str(numero)))
    
    # Si viene con el '9' intermedio (549...), lo dejamos como está para producción
    return numero


def normalizar_numero_whatsapp(numero):
    """
    Normaliza un número de WhatsApp quitando prefijos comunes
    y el '9' de Argentina para facilitar comparaciones de identidad.
    Retorna el número normalizado sin el '9' de móvil si es 549.
    """
    if not numero:
        return ""
    # Solo números
    num = ''.join(filter(str.isdigit, str(numero)))
    
    # Si empieza con 549 (Argentina móvil), normalizamos quitando el 9
    if num.startswith("549") and len(num) >= 12:
        num = "54" + num[3:]
    # Si empieza con 54 y no tiene el 9, pero tiene la longitud correcta, se deja
    
    return num


def son_numeros_identicos(num1, num2):
    """Compara dos números de teléfono de forma flexible para Argentina"""
    if not num1 or not num2:
        return False
    return normalizar_numero_whatsapp(num1) == normalizar_numero_whatsapp(num2)


def analizar_hora(texto):
    """
    Parsea horarios en lenguaje natural.
    Retorna HH:MM o None.
    """
    texto = texto.lower().replace('.', ':').strip()
    
    # 1. Formatos explícitos: 10:00, 17:30
    match_hora = re.search(r'(\d{1,2})[:](\d{2})', texto)
    if match_hora:
        h, m = map(int, match_hora.groups())
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"
    
    # 2. Formatos con "hs", "h", "horas" (ej: 10hs, 10 h)
    match_hs = re.search(r'(\d{1,2})\s*(?:hs|h|hrs|horas)', texto)
    if match_hs:
        h = int(match_hs.group(1))
        if 0 <= h <= 23:
            return f"{h:02d}:00"
            
    # 3. Formatos AM/PM (ej: 5 pm, 10 am)
    match_ampm = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', texto)
    if match_ampm:
        h = int(match_ampm.group(1))
        m = int(match_ampm.group(2) or 0)
        periodo = match_ampm.group(3)
        
        if periodo == 'pm' and h < 12:
            h += 12
        if periodo == 'am' and h == 12:
            h = 0
            
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"

    # 4. Formatos informales "tipo 6", "a las 10"
    match_simple = re.search(r'(?:tipo|a las|alas)\s*(\d{1,2})', texto)
    if match_simple:
        h = int(match_simple.group(1))
        if h < 8: # Asumir PM si es muy temprano (contexto inmobiliaria)
            h += 12
        if 0 <= h <= 23:
            return f"{h:02d}:00"
    
    # 5. Palabras clave: mediodia, mañana, tarde
    if "mediodia" in texto or "mediodía" in texto:
        return "12:00"
    if "mañana" in texto or "manana" in texto:
        if "esta" in texto or "por la" in texto: return "10:00" # "por la mañana"
    if "tarde" in texto:
        return "16:00"
    if "noche" in texto:
        return "20:00"
    
    return None


def analizar_fecha(texto):
    """Parsea fecha en formatos naturales (hoy, mañana, lunes) o DD-MM-AAAA"""
    texto = texto.lower().strip()
    ahora = datetime.now()
    
    # 1. Fechas relativas
    if "pasado mañana" in texto or "pasado manana" in texto:
        return ahora + timedelta(days=2)
    if "mañana" in texto or "manana" in texto:
        # Asegurarse que no sea "pasado mañana" (ya cubierto arriba pero por si acaso el orden importa)
        if "pasado" not in texto:
            return ahora + timedelta(days=1)
    if "hoy" in texto:
        return ahora
    
    # 1.1 "La semana que viene"
    desplazamiento_semana = 0
    if "semana que viene" in texto or "proxima semana" in texto or "próxima semana" in texto:
        desplazamiento_semana = 7
    
    # 2. Días de la semana
    dias = {
        "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
        "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6
    }
    
    # Buscar nombres de días en el texto
    for nombre_dia, num_dia in dias.items():
        if nombre_dia in texto:
            target_weekday = num_dia
            days_ahead = target_weekday - ahora.weekday()
            if days_ahead <= 0: 
                days_ahead += 7
            return ahora + timedelta(days=days_ahead + desplazamiento_semana)
    
    # 3. Formatos numéricos
    # Extraer tokens que parezcan fechas
    tokens = texto.split()
    formatos = [
        "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d",
        "%d-%m-%y", "%d/%m/%y"
    ]
    
    for token in tokens:
        # Limpiar puntuación
        token_limpio = token.strip('.,')
        for fmt in formatos:
            try:
                return datetime.strptime(token_limpio, fmt)
            except ValueError:
                continue
            
    return None


def save_json_atomic(filepath, data):
    """Guarda un archivo JSON de forma atómica usando un archivo temporal"""
    temp_file = f"{filepath}.tmp"
    try:
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                return super().default(obj)

        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False, cls=DateTimeEncoder)
        # Reemplazo atómico (en Windows os.replace es atómico para archivos)
        os.replace(temp_file, filepath)
        return True
    except Exception as e:
        log(f"❌ Error en guardado atómico de {filepath}: {e}")
        if os.path.exists(temp_file):
            try: os.remove(temp_file)
            except: pass
        return False


def _strip_media_fields(propiedades_list):
    """Elimina campos pesados (fotos, videos, etc.) de las propiedades antes de serializar a DB.
    Los datos multimedia se pueden volver a cargar de propiedades.json cuando se necesiten."""
    if not propiedades_list or not isinstance(propiedades_list, list):
        return propiedades_list
    campos_a_eliminar = ('fotos', 'videos', 'documentos', 'imagenes_360', 'info_multimedia')
    return [
        {k: v for k, v in p.items() if k not in campos_a_eliminar}
        for p in propiedades_list
        if isinstance(p, dict)
    ]


def log(message, level="INFO", user_id=None):
    """
    Función para logging con niveles y contexto de usuario opcional.
    Optimizada para no duplicar íconos si el mensaje ya trae uno.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Agregar contexto de usuario si está presente
    user_context = f" [USR: {user_id}]" if user_id else ""
    
    # Formatear el mensaje final
    full_message = f"{timestamp} {user_context} {message}"
    
    try:
        print(full_message, flush=True)
    except UnicodeEncodeError:
        # Fallback para Windows/Terminales sin UTF-8: eliminar emojis o caracteres no-ascii
        clean_message = full_message.encode('ascii', 'replace').decode('ascii')
        print(clean_message, flush=True)


def numero_a_emoji(n):
    """Convierte un número a su emoji correspondiente"""
    emojis = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    return emojis[n] if 0 <= n <= 10 else str(n)


def filtrar_propiedades_por_operacion(operacion):
    """Filtra propiedades por tipo de operación con caché"""
    propiedades = cargar_propiedades_cached()
    if not propiedades:
        return []
    
    return [p for p in propiedades if p.get('operacion', '').lower() == operacion.lower()]


def generar_listado_propiedades(propiedades):
    """Genera el mensaje de listado de propiedades"""
    if not propiedades:
        return "📭 No hay propiedades disponibles en este momento."
    
    # ✅ Descomentar esta línea o crearla
    mensaje = f"📋 *PROPIEDADES DISPONIBLES*\n\n"
    mensaje += f"Encontramos *{len(propiedades)}* propiedades:\n\n"
    
    for i, p in enumerate(propiedades, 1):
        titulo = p.get('titulo', 'Propiedad')

        precio_raw = p.get('precio', None)
        moneda = p.get('moneda_precio', '')  # USD / AR$ / etc.

        # Si el precio es 0 o None → Consultar
        if precio_raw in (0, None):
            precio = "Consultar"
        else:
            # Formateo normal
            if isinstance(precio_raw, (int, float)):
                precio_formateado = f"{precio_raw:,.0f}".replace(",", ".")
            else:
                precio_formateado = precio_raw

            precio = f"{moneda} {precio_formateado}".strip()

        operacion = p.get('operacion', '')
        simbolo = "💰 Venta -" if operacion == 'venta' else "🔑 Alquiler -"

        mensaje += f"*{i}.* {simbolo} {titulo}\n"
        mensaje += f"   💵 {precio}\n"
        mensaje += f"   📍 {p.get('barrio', 'Sin barrio')}\n\n"
    
    # 👇 NUEVO mensaje de ayuda
    mensaje += f"{'='*40}\n\n"
    mensaje += f"👉 *Respondé con el NÚMERO* de la propiedad que te interesa\n"
    mensaje += f"   (Ej: '1', '2', '3', ... '{len(propiedades)}')\n\n"
    mensaje += f"📱 *Envía 'MENU'* para volver al menú principal\n"
    mensaje += f"👋 *Envía 'SALIR'* para terminar la conversación"
    
    return mensaje


def formatear_detalle_propiedad(propiedad):
    """Formatea el detalle completo simulando el pitch de ventas de la IA (Costo 0)"""
    titulo = propiedad.get('titulo', 'Propiedad Destacada').strip()
    detalle = f"✨ *{titulo}* ✨\n\n"
    
    operacion = propiedad.get('operacion', '')
    if operacion == 'alquiler':
        detalle += "¡Excelente oportunidad de alquiler lista para mudarte! 🔑\n\n"
    elif operacion == 'venta':
        detalle += "¡Increíble oportunidad ideal para vivienda o inversión! 💰\n\n"
        
    detalle += f"📍 *Ubicación Estratégica:* {propiedad.get('direccion', 'Excelente zona')}, {propiedad.get('barrio', '')}\n"
    
    precio = propiedad.get('precio', 0)
    moneda = propiedad.get('moneda_precio', 'USD')
    simbolo = "USD$" if moneda == 'USD' else "$"
    detalle += f"💵 *Inversión:* {simbolo} {precio:,.0f}\n"
    
    expensas = propiedad.get('expensas', 0)
    if expensas > 0:
        moneda_exp = propiedad.get('moneda_expensas', 'ARS')
        simb_exp = "USD$" if moneda_exp == 'USD' else "$"
        if expensas < 50000 and moneda_exp == 'ARS':
            detalle += f"📉 *¡Expensas súper bajas!* Solo {simb_exp} {expensas:,.0f}\n"
        else:
            detalle += f"🏢 *Expensas:* {simb_exp} {expensas:,.0f}\n"
            
    detalle += f"📐 *Espacios:* {propiedad.get('ambientes', 0)} ambientes muy bien distribuidos en {propiedad.get('metros_cuadrados', 0)} m².\n"
    
    # Amenities con emojis y texto vendedor
    amenities = []
    if str(propiedad.get('cochera', 'No')).lower() in ['si', 'sí', '1', 'true', 'x']:
        amenities.append("🚗 Incluye cochera")
    if str(propiedad.get('balcon', 'No')).lower() in ['si', 'sí', '1', 'true', 'x']:
        amenities.append("🌆 Hermoso balcón")
    if str(propiedad.get('pileta', 'No')).lower() in ['si', 'sí', '1', 'true']:
        amenities.append("🏊 Pileta para disfrutar")
    if str(propiedad.get('aire_acondicionado', 'No')).lower() in ['si', 'sí', '1', 'true']:
        amenities.append("❄️ Aire acondicionado")
    if str(propiedad.get('acepta_mascotas', 'No')).lower() in ['si', 'sí', '1', 'true']:
        amenities.append("🐾 ¡Es Pet Friendly (Apto Mascotas)!")
        
    if amenities:
        detalle += "\n⭐ *Highlights de la Propiedad:*\n"
        for am in amenities:
            detalle += f"- {am}\n"
            
    # Intentar cargar entorno para vender la zona
    try:
        import os, json
        ruta_entorno = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entorno.json")
        if os.path.exists(ruta_entorno):
            with open(ruta_entorno, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            b = str(propiedad.get('barrio', '')).lower().strip()
            entorno = None
            for key_barrio, info_barrio in datos.items():
                if key_barrio in b or b in key_barrio:
                    entorno = info_barrio
                    break
            if entorno:
                detalle += "\n🌳 *Beneficios del Barrio:*\n"
                desc = entorno.get('descripcion_general', '')
                if desc: detalle += f"- {desc}\n"
                if 'transporte' in entorno:
                    detalle += f"- 🚇 {entorno['transporte'].get('descripcion', '')}\n"
                if 'seguridad' in entorno:
                    detalle += f"- 🚓 {entorno['seguridad'].get('descripcion', '')}\n"
    except Exception as e:
        pass
        
    # Descripción original acortada
    desc_orig = propiedad.get('descripcion', 'Sin descripción')
    if desc_orig and len(desc_orig) > 5:
        detalle += f"\n📝 *Más detalles:*\n{desc_orig[:250]}...\n"

    detalle += "\n"
    # Agregar link a Ficha PDF
    prop_id = propiedad.get('id_temporal')
    if prop_id:
        detalle += f"📄 *FICHA TÉCNICA (PDF):*\n{BASE_URL}/fichas/{prop_id}\n\n"
        
    detalle += "────────────────────\n"
    detalle += "¿Te gustaría que arreglemos una visita para esta semana, o querés conocer los requisitos de ingreso?\n\n"
    detalle += "📷 *FOTOS* (F) | 📄 *PDF* (P) | 8️⃣ *ME INTERESA*\n"
    detalle += "1️⃣ *VOLVER* | 0️⃣ *❌ SALIR*"
    
    return detalle


