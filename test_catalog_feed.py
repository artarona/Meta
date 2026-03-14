import os
import json
import csv
from io import StringIO

def cargar_propiedades():
    if os.path.exists('propiedades.json'):
        with open('propiedades.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def test_feed():
    BASE_URL = "https://meta-rjpb.onrender.com"
    propiedades = cargar_propiedades()
    
    output = StringIO()
    writer = csv.writer(output)
    
    headers = [
        'home_listing_id', 'name', 'availability', 'address', 'neighborhood',
        'city', 'region', 'country', 'price', 'image_link', 'link',
        'description', 'property_type', 'num_rooms', 'area_size', 'area_unit'
    ]
    writer.writerow(headers)
    
    for p in propiedades:
        pid = p.get('id_temporal', '')
        name = p.get('titulo', 'Sin Titulo')
        op = p.get('operacion', '').lower()
        availability = 'for_sale' if op == 'venta' else 'for_rent' if op == 'alquiler' else 'for_sale'
        precio = p.get('precio', 0)
        moneda = p.get('moneda_precio', 'USD')
        price_str = f"{precio:.2f} {moneda}"
        fotos = p.get('fotos', [])
        image_link = ""
        if fotos:
            foto_name = os.path.basename(fotos[0])
            image_link = f"{BASE_URL}/imgs/{foto_name}"
        link = f"{BASE_URL}/fichas/{pid}"
        direccion = p.get('direccion_completa', p.get('direccion', 'Capital Federal, Argentina'))
        barrio = p.get('barrio', 'Buenos Aires')
        tipo_orig = p.get('tipo', '').lower()
        if 'departam' in tipo_orig: p_type = 'apartment'
        elif 'casa' in tipo_orig: p_type = 'house'
        elif 'ph' in tipo_orig: p_type = 'house'
        elif 'terreno' in tipo_orig: p_type = 'land'
        else: p_type = 'other'
        
        writer.writerow([
            pid, name, availability, direccion, barrio,
            'Buenos Aires', 'CABA', 'AR',
            price_str, image_link, link,
            p.get('descripcion', '')[:100],
            p_type, p.get('ambientes', 1), p.get('metros_cuadrados', 0), 'sq m'
        ])
    
    print("CSV Header check:")
    print(output.getvalue().split('\n')[0])
    print("\nFirst row check:")
    print(output.getvalue().split('\n')[1])

if __name__ == "__main__":
    test_feed()
