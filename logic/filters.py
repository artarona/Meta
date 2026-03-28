"""
Módulo de detección de filtros desde texto del usuario
"""
import re
from typing import Dict, Any
from .filter_data import BARRIOS, TIPOS, OPERACIONES

def detect_filters(text: str) -> Dict[str, Any]:
    """
    Detecta filtros en el texto del usuario basándose en palabras clave.
    
    Args:
        text: Texto del usuario en minúsculas
        
    Returns:
        Dict con los filtros detectados
    """
    filters = {}
    text_lower = text.lower()
    
    # Detectar barrio
    for barrio in BARRIOS:
        if barrio.lower() in text_lower:
            filters['barrio'] = barrio
            break
    
    # Detectar tipo de propiedad
    tipo_mapping = {
        'casa': 'Casa',
        'departamento': 'Departamento',
        'depto': 'Departamento',
        'ph': 'PH',
        'terreno': 'Terreno',
        'oficina': 'Oficina',
        'local': 'Local',
        'galpón': 'Galpón',
        'galpon': 'Galpón',
        'casaquinta': 'Casaquinta',
        'duplex': 'Duplex',
        'triplex': 'Triplex'
    }
    
    for keyword, tipo in tipo_mapping.items():
        if keyword in text_lower:
            filters['tipo'] = tipo
            break
    
    # Detectar operación
    if 'alquiler' in text_lower:
        if 'temporal' in text_lower or 'vacacional' in text_lower:
            filters['operacion'] = 'Alquiler Temporal'
        else:
            filters['operacion'] = 'Alquiler'
    elif 'venta' in text_lower or 'comprar' in text_lower:
        filters['operacion'] = 'Venta'
    
    # Detectar cantidad de ambientes
    ambientes_match = re.search(r'(\d+)\s*(ambientes?|dormitorios?|habitaciones?)', text_lower)
    if ambientes_match:
        filters['ambientes'] = int(ambientes_match.group(1))
    
    # Detectar precio mínimo
    min_price_match = re.search(r'mínimo\s*[:=]?\s*([\d,\.]+)', text_lower)
    if min_price_match:
        try:
            filters['min_price'] = float(min_price_match.group(1).replace(',', ''))
        except ValueError:
            pass
    
    # Detectar precio máximo
    max_price_match = re.search(r'máximo|maximo|máx\s*[:=]?\s*([\d,\.]+)', text_lower)
    if max_price_match:
        try:
            filters['max_price'] = float(max_price_match.group(1).replace(',', ''))
        except ValueError:
            pass
    
    # Detectar metros cuadrados
    sqm_match = re.search(r'(\d+)\s*m²?|(\d+)\s*metros?', text_lower)
    if sqm_match:
        try:
            filters['metros_cuadrados'] = float(sqm_match.group(1) or sqm_match.group(2))
        except ValueError:
            pass
    
    return filters
