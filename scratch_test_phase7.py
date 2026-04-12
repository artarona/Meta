import sys
import os

# Ensure the root directory is in sys.path
sys.path.append(os.getcwd())

from logic.ai_prioritization import obtener_prioridad_lead
from database import obtener_estado_usuario, actualizar_estado_usuario
from datetime import datetime

def test_ai_scoring():
    print("--- TEST PRIORIZACION DE LEADS (IA) ---")
    
    user_id = "test_user_ai_999"
    
    # 1. Crear simulación de historial sugerente (Lead Caliente)
    historial_hot = [
        {"role": "user", "text": "Hola, estoy buscando casa con pileta en Pilar", "timestamp": datetime.now().isoformat()},
        {"role": "user", "text": "Me gusta la que dice Km 50", "timestamp": datetime.now().isoformat()},
        {"role": "user", "text": "Ya tengo el credito aprobado y quiero mudarme este mes", "timestamp": datetime.now().isoformat()}
    ]
    
    propiedad_test = {
        "titulo": "Barrio Privado Km 50 Pilar",
        "precio": 160000,
        "moneda_precio": "USD",
        "barrio": "Pilar"
    }
    
    print("\n[INFO] Analizando Lead Caliente...")
    res_hot = obtener_prioridad_lead(user_id, historial_hot, propiedad_test)
    print(f"RESULTADO: {res_hot.get('label', 'N/A')} (Score: {res_hot['score']}/10)")
    print(f"RAZÓN: {res_hot['razonamiento']}")
    
    # 2. Crear simulación de historial frío
    historial_cold = [
        {"role": "user", "text": "hola", "timestamp": datetime.now().isoformat()},
        {"role": "user", "text": "tienen algo barato?", "timestamp": datetime.now().isoformat()},
        {"role": "user", "text": "ah ok despues veo", "timestamp": datetime.now().isoformat()}
    ]
    
    print("\n[INFO] Analizando Lead Frío...")
    res_cold = obtener_prioridad_lead(user_id, historial_cold, propiedad_test)
    print(f"RESULTADO: {res_cold.get('label', 'N/A')} (Score: {res_cold['score']}/10)")
    print(f"RAZÓN: {res_cold['razonamiento']}")

if __name__ == "__main__":
    try:
        test_ai_scoring()
    except Exception as e:
        print(f"Error en el test: {e}")
