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
ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN", "EAAJYsGl5pHgBQxaEEQ4rF2R7Y52iQzMb5wT3sAxpThJcuuSA9XW57MdrjmLtCMgz1ZClfqXoybrWJ3WkSjSYlzIuIWgw0rRLRlIRcvLG9m6MZCiDRPJLBjtzRGMXx3e7st0wrQ5c8zFDDTXbwisNBZBZBdVlNMShzfJ5YYcfVs2ErrP7v55zjit0S5J5jHhcsKHAVYBz4jG1IacGq4l3BYwH9vouv5p0XiAeYgB8tss6rsbGdpIpxFjs1LkAlUHhTPWOLwDNsZC6IV6mrOKrDRZB9DRntGMSUjvBWp")

PHONE_NUMBER_ID = "1000705633118215"
ADMIN_NUMBER = "5491151511579"
BASE_URL = os.environ.get("BASE_URL", "https://meta-rjpb.onrender.com")
BASE_URL_AI = os.environ.get("BASE_URL_AI", "http://localhost:8001")
LEADS_FILE = "leads.json"
ADMIN_ACCESS_KEY = os.getenv('ADMIN_KEY', 'dante2026')
CITAS_FILE = "citas.json"
PROPIEDADES_FILE = "propiedades.json"
HORARIOS_FILE = "dias-horarios-visitas.json"
FICHAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fichas")
os.makedirs(FICHAS_DIR, exist_ok=True)

# ========== CONFIGURACIÓN DE CITAS ==========
CITAS_DISPONIBLES = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
    "17:00", "17:30", "18:00", "18:30"
]
