import os
import threading

# ========== CONFIGURACIÓN GOOGLE CALENDAR ==========
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'google_calendar_key.json'

# ========== CACHE TOKEN WHATSAPP ==========
whatsapp_token_cache = {"valid": False, "expires_at": 0}
whatsapp_token_lock = threading.Lock()

# ========== CONFIGURACIÓN ==========
VERIFY_TOKEN = "mi_token_secreto_123"
# 🔥 CAMBIO IMPORTANTE: Usar variable de entorno para el token
ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN", "EAAJYsGl5pHgBQz2NpRHUAItiHE0GznHoZBd6Mk8BarPC2ny5Ih2PgPtp2qGneVhDI5KTs5ejmlVoP9vsCTZA0csphcsBtjSOpExZCWKWni1OcgEA7KfMHwpZBg0Mkvb7SWBu0Kg8ar0PRNohAmZAKeOmvW61LZA1qOXemD8HVce0vZBNLSqqZAstYO2vlNiTDQZDZD")

# config.py

# Número que recibirá las alertas (Dante Agente)
# Usamos el nuevo número que definiste: 549117877334

# CAMBIAR EN R E N D E R
# En config.py, verifica que el formato sea el correcto:
AGENT_NUMBER = os.getenv("AGENT_NUMBER", "5491178877334")  # 
ADMIN_NUMBER = "5491176596523"

PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "1061691623689167")
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "10276359504441539")
IG_BUSINESS_ID = os.getenv("IG_BUSINESS_ID", "17841403923335775")
APP_ID = os.getenv("APP_ID", "660464660489336")
FB_CONFIG_ID = os.getenv("FB_CONFIG_ID", "1619594132663970")

# Tokens específicos por plataforma (fallback al ACCESS_TOKEN general)
FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_TOKEN", ACCESS_TOKEN)
IG_ACCESS_TOKEN = os.getenv("IG_IG_TOKEN", ACCESS_TOKEN)

BASE_URL = os.environ.get("BASE_URL", "https://meta-rjpb.onrender.com")
BASE_URL_AI = os.environ.get("BASE_URL_AI", "http://localhost:8001")
LEADS_FILE = "leads.json"
ADMIN_ACCESS_KEY = os.getenv('ADMIN_KEY', 'dante2026')
CITAS_FILE = "citas.json"
PROPIEDADES_FILE = "propiedades.json"
HORARIOS_FILE = "dias-horarios-visitas.json"
FICHAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fichas")
os.makedirs(FICHAS_DIR, exist_ok=True)

# ========== CONFIGURACIÓN DE TASACIÓN ==========
DOLAR_VALOR = float(os.getenv("DOLAR_VALOR", "1250.0")) # Valor por defecto actualizado

CITAS_DISPONIBLES = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
    "17:00", "17:30", "18:00", "18:30"
]

# ========== CONFIGURACIÓN DE IA (GEMINI) ==========
GEMINI_KEYS = [
    os.environ.get("GEMINI_KEY_1", "AIzaSyCf_UBys6b4_uceLlN3HtVVy64W_MLkpcw"),
    os.environ.get("GEMINI_KEY_2", "AIzaSyBIRmNG2iJVWieK5Z4qY5xWpJWzQwlrkow")
]
WORKING_MODEL = os.environ.get("WORKING_MODEL", "gemini-2.0-flash-001")
