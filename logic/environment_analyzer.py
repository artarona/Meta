"""
Environment Analyzer - Generador de análisis de barrios usando IA
Este módulo genera descripciones completas de barrios basándose en su nombre,
utilizando Gemini API para crear contenido rico y detallado.
"""
import os
import json
import sys
from typing import Dict, Any, List, Optional

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.gemini_client import call_gemini_with_rotation

def generate_analysis(nombre_barrio: str) -> Dict[str, Any]:
    """
    Genera un análisis completo del barrio usando IA.
    
    Args:
        nombre_barrio: Nombre del barrio a analizar
        
    Returns:
        Dict con la información generada o un dict con 'error' si falla
    """
    
    # Verificar si hay API key configurada
    try:
        from logic.gemini_client import API_KEYS
        if not API_KEYS:
            print("⚠️ No hay API keys de Gemini configuradas")
            return get_fallback_analysis(nombre_barrio)
    except ImportError:
        print("⚠️ No se pudo importar API_KEYS")
        return get_fallback_analysis(nombre_barrio)
    
    # Capitalizar el nombre del barrio
    nombre_formateado = nombre_barrio.strip().title()
    
    # Prompt para Gemini
    prompt = f"""
Genera un análisis completo del barrio "{nombre_formateado}" de Buenos Aires, Argentina.

Necesito un análisis estructurado en formato JSON con los siguientes campos:
1. descripcion_general: Una descripción general del barrio (2-3 oraciones)
2. transporte: Lista de 2-3 items sobre transporte público y conectividad
3. educacion: Lista de 3-4 instituciones educativas destacadas
4. salud: Lista de 3-4 centros de salud y hospitales
5. comercio: Lista de 3-4 zonas o tipos de comercio
6. gastronomia: Lista de 3-4 restaurantes o zonas gastronómicas
7. servicios_financieros: Lista de 2-3 bancos o servicios financieros
8. seguridad: Lista de 2-3 items sobre seguridad
9. espacios_verdes: Lista de 2-3 parques o plazas
10. contaminacion: Lista de 2-3 items sobre contaminación y ruido
11. vida_barrio: Lista de 2-3 items sobre la vida del barrio

Responde SOLO con JSON válido, sin texto adicional.
El JSON debe ser parseable directamente.
"""
    
    try:
        print(f"🔍 Generando análisis para: {nombre_barrio}")
        response = call_gemini_with_rotation(prompt)
        
        # Verificar si la respuesta es válida (no es el mensaje de fallback)
        if not response or len(response) < 10 or response.startswith("🤖"):
            print("⚠️ Gemini no disponible, usando análisis de fallback")
            return get_fallback_analysis(nombre_barrio)
        
        # Limpiar respuesta (quitar posibles backticks)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        # Verificar que la respuesta no esté vacía
        if not response or len(response) < 10:
            print("⚠️ Respuesta vacía de Gemini, usando análisis de fallback")
            return get_fallback_analysis(nombre_barrio)
        
        # Parsear JSON
        data = json.loads(response)
        
        # Validar estructura
        required_fields = ['descripcion_general', 'transporte', 'educacion', 'salud', 
                          'comercio', 'gastronomia', 'servicios_financieros', 'seguridad',
                          'espacios_verdes', 'contaminacion', 'vida_barrio']
        
        for field in required_fields:
            if field not in data:
                data[field] = []
        
        # Asegurar que las listas sean listas
        for key in data:
            if not isinstance(data[key], list):
                data[key] = [str(data[key])] if data[key] else []
        
        print(f"✅ Análisis generado para {nombre_barrio}")
        return data
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        print(f"📄 Respuesta recibida: {response[:200]}...")
        return get_fallback_analysis(nombre_barrio)
        
    except Exception as e:
        print(f"❌ Error generando análisis: {e}")
        return get_fallback_analysis(nombre_barrio)


def get_fallback_analysis(nombre_barrio: str) -> Dict[str, Any]:
    """
    Genera un análisis básico cuando no hay API key disponible.
    
    Args:
        nombre_barrio: Nombre del barrio
        
    Returns:
        Dict con información básica del barrio
    """
    nombre_formateado = nombre_barrio.strip().title()
    
    return {
        "descripcion_general": f"{nombre_formateado} es un barrio de Buenos Aires con características propias de su zona. Ofrece una combinación de vida urbana y residencial.",
        "transporte": [
            f"Conexiones de transporte público en {nombre_formateado}",
            "Líneas de colectivo locales",
            "Acceso a red de subte y tren"
        ],
        "educacion": [
            "Institutos educativos locales",
            "Escuelas primarias y secundarias",
            "Centros de formación"
        ],
        "salud": [
            "Centros de salud del barrio",
            "Farmacias locales",
            "Hospitales cercanos"
        ],
        "comercio": [
            "Comercio de barrio tradicional",
            "Locales comerciales",
            "Mercados y ferias"
        ],
        "gastronomia": [
            "Restaurantes locales",
            "Bares y cafes",
            "Opciones gastronómicas diversas"
        ],
        "servicios_financieros": [
            "Cajeros automáticos",
            "Sucursales bancarias",
            "Servicios financieros"
        ],
        "seguridad": [
            "Comisaría del barrio",
            "Vigilancia policial",
            "Nivel de seguridad medio"
        ],
        "espacios_verdes": [
            "Plazas locales",
            "Áreas verdes",
            "Parques cercanos"
        ],
        "contaminacion": [
            "Nivel de contaminación típico urbano",
            "Tráfico moderado",
            "Calidad del aire variable"
        ],
        "vida_barrio": [
            "Comunidad establecida",
            "Actividades vecinales",
            "Vida comunitaria activa"
        ]
    }


class EnvironmentAnalyzer:
    """
    Clase envoltorio para el analizador de entorno.
    Mantiene compatibilidad con el código existente que espera esta interfaz.
    """
    
    def __init__(self):
        """Inicializa el analizador"""
        pass
    
    def generate_analysis(self, nombre_barrio: str) -> Dict[str, Any]:
        """
        Genera un análisis del barrio.
        
        Args:
            nombre_barrio: Nombre del barrio a analizar
            
        Returns:
            Dict con la información generada
        """
        return generate_analysis(nombre_barrio)
