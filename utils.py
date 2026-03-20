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
            if days_ahead <= 0: # Si ya pasó, asumimos la próxima semana
                days_ahead += 7
            return ahora + timedelta(days=days_ahead)
    
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


def log(message, level="INFO"):
    """Función para logging con niveles"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    level_icons = {
        "INFO": "ℹ️",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "SUCCESS": "✅",
        "DEBUG": "🐛"
    }
    icon = level_icons.get(level, "📝")
    print(f"{timestamp} {icon} {message}", flush=True)


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
    """Genera un listado formateado de propiedades para WhatsApp"""
    if not propiedades:
        return "📭 No hay propiedades disponibles en este momento."
    
    listado = "📋 *LISTADO DE PROPIEDADES*\n\n"
    
    for i, prop in enumerate(propiedades[:10], 1):
        operacion = prop.get('operacion', '').upper()
        listado += f"{numero_a_emoji(i)} {prop.get('titulo', 'Sin título')} -- {operacion} --\n"
        listado += f"   📍 {prop.get('barrio', 'N/A')} | "
        
        precio = prop.get('precio', 0)
        moneda = prop.get('moneda_precio', 'USD')
        if moneda == 'USD':
            listado += f"💰 USD ${precio:,.0f}\n"
        else:
            listado += f"💰 $ {precio:,.0f} ARS\n"
        
        listado += f"   🛏️ {prop.get('ambientes', 0)} amb. | "
        listado += f"📐 {prop.get('metros_cuadrados', 0)} m²\n"
        
        if prop.get('operacion') == 'venta':
            estado = prop.get('estado', 'N/A')
            listado += f"   🏗️ Estado: {estado.capitalize()}\n"
        
        listado += "─" * 20 + "\n"
    
    if len(propiedades) > 10:
        listado += f"\n📊 ...y {len(propiedades) - 10} propiedades más.\n"
    
    listado += "\nPara ver detalles, responde con el número (ej: 1️⃣)\n"
    listado += f"{numero_a_emoji(0)} *❌ SALIR*"
    
    return listado


def formatear_detalle_propiedad(propiedad):
    """Formatea el detalle completo de una propiedad"""
    detalle = f"🏠 *{propiedad.get('titulo', 'Sin título')}*\n\n"
    
    detalle += f"📍 *Ubicación:* {propiedad.get('direccion', 'Sin dirección')}, {propiedad.get('barrio', '')}\n"
    
    precio = propiedad.get('precio', 0)
    moneda = propiedad.get('moneda_precio', 'USD')
    if moneda == 'USD':
        detalle += f"💰 *Precio:* USD ${precio:,.0f}\n"
    else:
        detalle += f"💰 *Precio:* $ {precio:,.0f} ARS\n"
    
    detalle += f"🛏️ *Ambientes:* {propiedad.get('ambientes', 0)}\n"
    detalle += f"📐 *Metros cuadrados:* {propiedad.get('metros_cuadrados', 0)} m²\n"
    detalle += f"📋 *Tipo:* {propiedad.get('tipo', '').capitalize()}\n"
    detalle += f"🏗️ *Estado:* {propiedad.get('estado', 'N/A').capitalize()}\n"
    
    expensas = propiedad.get('expensas', 0)
    if expensas > 0:
        moneda_exp = propiedad.get('moneda_expensas', 'ARS')
        if moneda_exp == 'USD':
            detalle += f"🏢 *Expensas:* USD ${expensas:,.0f}\n"
        else:
            detalle += f"🏢 *Expensas:* $ {expensas:,.0f} ARS\n"
    
    # Amenities con validación
    amenities = []
    if str(propiedad.get('cochera', 'No')).lower() in ['si', 'sí', '1', 'true', 'x']:
        amenities.append("🚗 Cochera")
    if str(propiedad.get('balcon', 'No')).lower() in ['si', 'sí', '1', 'true', 'x']:
        amenities.append("🌆 Balcón")
    if str(propiedad.get('pileta', 'No')).lower() in ['si', 'sí', '1', 'true']:
        amenities.append("🏊 Pileta")
    if str(propiedad.get('aire_acondicionado', 'No')).lower() in ['si', 'sí', '1', 'true']:
        amenities.append("❄️ Aire acondicionado")
    if str(propiedad.get('acepta_mascotas', 'No')).lower() in ['si', 'sí', '1', 'true']:
        amenities.append("🐕 Acepta mascotas")
    
    if amenities:
        detalle += "*Amenities:* " + " | ".join(amenities) + "\n"
    
    detalle += f"\n📝 *Descripción:*\n{propiedad.get('descripcion', 'Sin descripción')[:500]}...\n\n"
    
    # Agregar link a Ficha PDF
    prop_id = propiedad.get('id_temporal')
    if prop_id:
        detalle += f"📄 *FICHA TÉCNICA (PDF):*\n{BASE_URL}/fichas/{prop_id}\n\n"
        
    detalle += "────────────────────\n"
    detalle += "📷 *FOTOS* (F) | 📄 *PDF* (P) | 8️⃣ *ME INTERESA*\n"
    detalle += "1️⃣ *VOLVER* | 0️⃣ *❌ SALIR*"
    
    return detalle


