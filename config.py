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
ACCESS_TOKEN = os.environ.get("WHATSAPP_TOKEN", "EAAJYsGl5pHgBQ6Ku2KCqbcehj7AKAvSvOnbRdYZAU3lAp360oAje3GxZCEZAyDXvotcCy7uRXPdsLSKDSXOMiuVJwLEbnOn10xQPgotRV4NKHYPBGeYf2JtDp2pPWyekv3BdqX6Hf04Ov7uOeZCkCjrBiSV27D2ly2JySNkXgvc6quandytHXl4BdEKvNmHUpU5o75Xw80Pih1oQzZBkmlAmhsEtmwt5aslRS42VrjA5WoZCEdZAqRZAXz80f2VkDZCjXljBmBOwTRWEwNUGKApAHZAdlCRw7ZCAfZBGcZC6W")

PHONE_NUMBER_ID = "1000705633118215"
ADMIN_NUMBER = "5491151511579"
BASE_URL = os.environ.get("BASE_URL", "https://meta-rjpb.onrender.com")
BASE_URL_AI = os.environ.get("BASE_URL_AI", "http://localhost:8001")
LEADS_FILE = "leads.json"
ADMIN_ACCESS_KEY = os.getenv('ADMIN_KEY', 'dante2026')
CITAS_FILE = "citas.json"
HORARIOS_FILE = "dias-horarios-visitas.json"
FICHAS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fichas")
os.makedirs(FICHAS_DIR, exist_ok=True)

# ========== CONFIGURACIÓN DE CITAS ==========
CITAS_DISPONIBLES = [
    "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
    "17:00", "17:30", "18:00", "18:30"
]
