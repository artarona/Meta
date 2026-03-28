import os
import sqlite3
import json
from datetime import datetime

# Configuración de rutas
DB_PATH = 'instance/dante_properties.db'
SCRAPING_JSON = 'scraping.json'
OUTPUT_FILE = 'market_valuation_map.json'
EXCHANGE_RATE = 1050.0

def export_stats():
    """Genera un mapa de valoración combinando scraping.json y la base de datos (Ventas y Alquileres)"""
    print(f"🚀 Iniciando exportación de estadísticas de mercado...")
    
    valuation_map = {}
    
    # 1. Cargar mapa existente
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                valuation_map = json.load(f)
            print(f"📂 Cargado mapa existente con {len(valuation_map)} barrios.")
        except:
            pass

    # 2. Procesar scraping.json
    if os.path.exists(SCRAPING_JSON):
        try:
            with open(SCRAPING_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('success') and data.get('data'):
                s_data = data['data']
                barrio = s_data.get('zone', '').lower().strip()
                operacion = s_data.get('operation_type', 'venta').lower().strip()
                tipo = s_data.get('property_type', 'departamento').lower().strip()
                stats = s_data.get('statistics', {})
                
                if barrio and stats.get('average_price_per_m2'):
                    if barrio not in valuation_map: valuation_map[barrio] = {}
                    if operacion not in valuation_map[barrio]: valuation_map[barrio][operacion] = {}
                    
                    valuation_map[barrio][operacion][tipo] = {
                        "avg_m2": round(stats['average_price_per_m2'], 2),
                        "muestra": s_data.get('sample_size', 0),
                        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "source": "scraping.json",
                        "currency": s_data.get('currency_distribution', {}).get('USD', 0) > 0 and operacion == 'venta' and 'USD' or 'ARS'
                    }
                    print(f"✅ Datos de {barrio} | {operacion} | {tipo} actualizados desde scraping.json")
        except Exception as e:
            print(f"⚠️ Error procesando scraping.json: {e}")

    # 3. Procesar Base de Datos
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
            SELECT 
                LOWER(barrio) as barrio_key,
                LOWER(operacion) as op_key,
                LOWER(tipo) as tipo_key,
                moneda_precio,
                AVG(CASE 
                    WHEN operacion = 'venta' AND moneda_precio = 'ARS' THEN (precio / ?) / metros_cuadrados
                    ELSE precio / metros_cuadrados 
                END) as avg_m2,
                COUNT(*) as muestra
            FROM propiedades
            WHERE metros_cuadrados > 5 AND precio > 100
            GROUP BY barrio_key, op_key, tipo_key
            """
            cursor.execute(query, (EXCHANGE_RATE,))
            rows = cursor.fetchall()
            
            for row in rows:
                b, op, t = row['barrio_key'], row['op_key'], row['tipo_key']
                if b not in valuation_map: valuation_map[b] = {}
                if op not in valuation_map[b]: valuation_map[b][op] = {}
                
                # Solo agregar si no existe o es data vieja
                if t not in valuation_map[b][op]:
                    valuation_map[b][op][t] = {
                        "avg_m2": round(row['avg_m2'], 2),
                        "muestra": row['muestra'],
                        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "source": "database",
                        "currency": row['moneda_precio'] or ('USD' if op == 'venta' else 'ARS')
                    }
            conn.close()
            print(f"✅ Datos adicionales cargados desde la base de datos.")
        except Exception as e:
            if "no such table: propiedades" not in str(e):
                print(f"⚠️ Error en base de datos: {e}")

    # 4. Guardar
    if valuation_map:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(valuation_map, f, ensure_ascii=False, indent=2)
        print(f"✨ Mapa de valoración guardado con {len(valuation_map)} barrios en {OUTPUT_FILE}")

if __name__ == "__main__":
    export_stats()
