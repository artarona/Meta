# ========== CONFIGURACIÓN CON VARIABLES DE ENTORNO ==========
"""
Configuración del Chatbot Inmobiliario
Inmobiliaria: Buenos Aires / CABA / San Telmo

IMPORTANTE: En producción, usar variables de entorno para tokens sensibles.
"""

import os

# ========== WHATSAPP API (Variables de entorno para producción) ==========
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mi_token_secreto_123")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "TU_ACCESS_TOKEN_AQUI")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "TU_PHONE_NUMBER_ID")

# ========== CACHE ==========
CACHE_MAX_SIZE = 1000
CACHE_TTL = 300  # 5 minutos

# ========== SESIONES ==========
SESSION_TIMEOUT = 1800  # 30 minutos de inactividad

# ========== OPERACIONES DISPONIBLES ==========
OPERACIONES = {
    "1": {"id": "compra", "nombre": "Comprar", "emoji": "🏠"},
    "2": {"id": "alquiler", "nombre": "Alquilar (largo plazo)", "emoji": "🔑"},
    "3": {"id": "vacacional", "nombre": "Alquiler vacacional", "emoji": "🏖️"},
    "4": {"id": "tasacion", "nombre": "Tasar mi propiedad", "emoji": "📊"},
}

# ========== TIPOS DE INMUEBLE ==========
TIPOS_INMUEBLE = {
    "1": {"id": "apartamento", "nombre": "Apartamento/Departamento", "emoji": "🏢"},
    "2": {"id": "casa", "nombre": "Casa/Chalet", "emoji": "🏡"},
    "3": {"id": "terreno", "nombre": "Terreno", "emoji": "🌳"},
    "4": {"id": "local", "nombre": "Local comercial", "emoji": "🏪"},
    "5": {"id": "oficina", "nombre": "Oficina", "emoji": "🏛️"},
}

# ========== ZONAS DE BUENOS AIRES ==========
ZONAS = {
    "1": {"id": "san_telmo", "nombre": "San Telmo", "emoji": "🎭"},
    "2": {"id": "palermo", "nombre": "Palermo", "emoji": "🌳"},
    "3": {"id": "recoleta", "nombre": "Recoleta", "emoji": "🏛️"},
    "4": {"id": "belgrano", "nombre": "Belgrano", "emoji": "🏠"},
    "5": {"id": "puerto_madero", "nombre": "Puerto Madero", "emoji": "🌊"},
    "6": {"id": "caballito", "nombre": "Caballito", "emoji": "🐴"},
    "7": {"id": "nunez", "nombre": "Núñez", "emoji": "⚽"},
    "8": {"id": "villa_crespo", "nombre": "Villa Crespo", "emoji": "🎨"},
    "9": {"id": "otra", "nombre": "Otra zona", "emoji": "📍"},
}

# ========== RANGOS DE AMBIENTES ==========
AMBIENTES = {
    "1": {"id": "monoambiente", "nombre": "Monoambiente", "min": 0, "max": 1},
    "2": {"id": "2amb", "nombre": "2 ambientes", "min": 2, "max": 2},
    "3": {"id": "3amb", "nombre": "3 ambientes", "min": 3, "max": 3},
    "4": {"id": "4amb", "nombre": "4+ ambientes", "min": 4, "max": 99},
}

# ========== RANGOS DE PRESUPUESTO (USD) ==========
PRESUPUESTO_COMPRA = {
    "1": {"id": "hasta_50k", "nombre": "Hasta USD 50.000", "min": 0, "max": 50000},
    "2": {"id": "50k_100k", "nombre": "USD 50.000 - 100.000", "min": 50000, "max": 100000},
    "3": {"id": "100k_150k", "nombre": "USD 100.000 - 150.000", "min": 100000, "max": 150000},
    "4": {"id": "150k_250k", "nombre": "USD 150.000 - 250.000", "min": 150000, "max": 250000},
    "5": {"id": "mas_250k", "nombre": "Más de USD 250.000", "min": 250000, "max": 99999999},
}

# ========== RANGOS DE ALQUILER (ARS mensual) ==========
PRESUPUESTO_ALQUILER = {
    "1": {"id": "hasta_300k", "nombre": "Hasta $300.000/mes", "min": 0, "max": 300000},
    "2": {"id": "300k_500k", "nombre": "$300.000 - $500.000/mes", "min": 300000, "max": 500000},
    "3": {"id": "500k_800k", "nombre": "$500.000 - $800.000/mes", "min": 500000, "max": 800000},
    "4": {"id": "mas_800k", "nombre": "Más de $800.000/mes", "min": 800000, "max": 99999999},
}

# ========== URGENCIA ==========
URGENCIA = {
    "1": {"id": "inmediato", "nombre": "Inmediato (este mes)", "emoji": "🔥"},
    "2": {"id": "1_3_meses", "nombre": "En 1-3 meses", "emoji": "📅"},
    "3": {"id": "3_6_meses", "nombre": "En 3-6 meses", "emoji": "🗓️"},
    "4": {"id": "explorando", "nombre": "Solo estoy explorando", "emoji": "🔍"},
}

# ========== CARACTERÍSTICAS ADICIONALES ==========
CARACTERISTICAS = {
    "1": {"id": "cochera", "nombre": "Cochera/Parking", "emoji": "🚗"},
    "2": {"id": "piscina", "nombre": "Piscina", "emoji": "🏊"},
    "3": {"id": "quincho", "nombre": "Quincho/Parrilla", "emoji": "🔥"},
    "4": {"id": "terraza", "nombre": "Terraza/Balcón", "emoji": "🌅"},
    "5": {"id": "amenities", "nombre": "Amenities (gym, SUM)", "emoji": "🏋️"},
    "6": {"id": "mascotas", "nombre": "Acepta mascotas", "emoji": "🐕"},
    "7": {"id": "amueblado", "nombre": "Amueblado", "emoji": "🛋️"},
    "0": {"id": "ninguna", "nombre": "Ninguna en particular", "emoji": "➡️"},
}

# ========== ESTADOS DEL FLUJO ==========
class Estados:
    INICIO = "inicio"
    OPERACION = "operacion"
    TIPO_INMUEBLE = "tipo_inmueble"
    ZONA = "zona"
    ZONA_OTRA = "zona_otra"
    AMBIENTES = "ambientes"
    PRESUPUESTO = "presupuesto"
    URGENCIA = "urgencia"
    CARACTERISTICAS = "caracteristicas"
    RESUMEN = "resumen"
    CONFIRMACION = "confirmacion"
    # Estados especiales para tasación
    TASACION_DIRECCION = "tasacion_direccion"
    TASACION_TIPO = "tasacion_tipo"
    TASACION_M2 = "tasacion_m2"
    TASACION_ANTIGUEDAD = "tasacion_antiguedad"
    TASACION_RESUMEN = "tasacion_resumen"
    # Finalizado
    FINALIZADO = "finalizado"
    AGENTE_HUMANO = "agente_humano"

# ========== DATOS DE LA INMOBILIARIA ==========
INMOBILIARIA = {
    "nombre": os.environ.get("INMOBILIARIA_NOMBRE", "Tu Inmobiliaria"),
    "telefono_agente": os.environ.get("TELEFONO_AGENTE", "+5491112345678"),
    "email": os.environ.get("EMAIL_CONTACTO", "info@tuinmobiliaria.com"),
    "web": os.environ.get("WEB_URL", "www.tuinmobiliaria.com"),
    "horario": "Lunes a Viernes 9:00 - 18:00",
}
