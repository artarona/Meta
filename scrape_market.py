#!/usr/bin/env python3
"""
Script Standalone de Scraping y Análisis de Mercado Inmobiliario

Este script extrae datos de portales inmobiliarios argentinos y genera 
estadísticas de mercado, guardando los resultados en un archivo JSON.

Uso:
    python scrape_market.py --zona palermo
    python scrape_market.py --zona belgrano --operacion venta --tipo departamento
    python scrape_market.py --zona microcentro --output /ruta/personalizada/scraping.json

Argumentos:
    --zona, -z:      Zona o barrio a analizar (requerido)
    --operacion, -o: Tipo de operación (default: venta)
    --tipo, -t:      Tipo de propiedad (default: departamento)
    --output, -o:    Ruta del archivo JSON de salida (default: scraping.json)
    --ayuda, -h:     Muestra este mensaje de ayuda
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Añadir el directorio backend al path para importar los módulos de lógica
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuración por defecto
DEFAULT_OUTPUT_FILE = "scraping.json"
DEFAULT_OPERATION = "venta"
DEFAULT_PROPERTY_TYPE = "departamento"


def run_scraper(zone: str, operation: str = DEFAULT_OPERATION, 
                property_type: str = DEFAULT_PROPERTY_TYPE,
                output_file: str = DEFAULT_OUTPUT_FILE) -> dict:
    """
    Ejecuta el scraping de mercado inmobiliario y guarda los resultados.
    
    Args:
        zone: Barrio o zona a analizar
        operation: Tipo de operación (venta/alquiler)
        property_type: Tipo de propiedad (departamento/casa/ph/etc.)
        output_file: Ruta del archivo JSON de salida
    
    Returns:
        Diccionario con los resultados del scraping
    """
    print("=" * 70)
    print("SCRAPER DE MERCADO INMOBILIARIO - DANTE PROPIEDADES")
    print("=" * 70)
    print(f"[ZONA] Zona: {zone}")
    print(f"[DINERO] Operacion: {operation}")
    print(f"[CASA] Tipo de propiedad: {property_type}")
    print(f"[ARCHIVO] Archivo de salida: {output_file}")
    print("=" * 70)
    
    # Importar el gestor de scraping
    try:
        # Importación directa que funciona en Windows y Linux
        import importlib.util
        # Buscar el archivo - primero busca el viejo nombre (scraper.py) para compatibilidad
        logic_path = os.path.join(os.path.dirname(__file__), 'logic', 'scraper.py')
        if not os.path.exists(logic_path):
            logic_path = os.path.join(os.path.dirname(__file__), 'logic', 'market_scraper.py')
        spec = importlib.util.spec_from_file_location("market_scraper", logic_path)
        market_scraper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(market_scraper)
        ScrapingManager = market_scraper.ScrapingManager
        print("[OK] Modulo de scraping importado correctamente")
    except Exception as e:
        print(f"[ERROR] Error importando modulo de scraping: {e}")
        return {
            "success": False,
            "error": f"Error importando módulo de scraping: {e}"
        }
    
    # Inicializar el gestor de scraping
    try:
        manager = ScrapingManager()
        print("[OK] ScrapingManager inicializado")
    except Exception as e:
        print(f"[ERROR] Error inicializando ScrapingManager: {e}")
        return {
            "success": False,
            "error": f"Error inicializando ScrapingManager: {e}"
        }
    
    # Ejecutar el scraping
    print("\n[INICIO] Iniciando scraping de portales inmobiliarios...")
    print("[INFO] Este proceso puede tomar varios minutos debido a los delays anti-bloqueo\n")
    
    try:
        result = manager.scrape_market(zone, operation, property_type)
    except Exception as e:
        print(f"[ERROR] Error durante el scraping: {e}")
        return {
            "success": False,
            "error": f"Error durante el scraping: {e}"
        }
    
    # Formatear el resultado final
    final_result = {
        "success": result.get('sample_size', 0) > 0,
        "message": f"Analizadas {result.get('sample_size', 0)} propiedades de {result.get('raw_properties_count', 0)} extraídas",
        "zone": zone,
        "operation": operation,
        "property_type": property_type,
        "scraping_timestamp": datetime.now().isoformat(),
        "data": result,
        "errors": result.get('errors', [])
    }
    
    # Guardar en archivo JSON
    print(f"\n[GUARDANDO] Guardando resultados en: {output_file}")
    
    try:
        # Crear directorio si no existe
        output_dir = os.path.dirname(os.path.abspath(output_file))
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"[CARPETA] Directorio creado: {output_dir}")
        
        # Guardar el archivo JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] Archivo guardado exitosamente: {output_file}")
        
    except Exception as e:
        print(f"[ERROR] Error guardando archivo: {e}")
        final_result["file_error"] = str(e)
    
    # Mostrar resumen en consola
    print("\n" + "=" * 70)
    print("[ESTADISTICAS] RESUMEN DEL ANALISIS DE MERCADO")
    print("=" * 70)
    
    if final_result["success"]:
        stats = result.get('statistics', {})
        print(f"[OK] Muestra analizada: {result.get('sample_size', 0)} propiedades")
        print(f"[SUBE] Precio m2 promedio: ${stats.get('average_price_per_m2', 0):,.2f}")
        print(f"[BAJA] Precio m2 mediano: ${stats.get('median_price_per_m2', 0):,.2f}")
        print(f"[RANGO] Rango de precios: {stats.get('price_range_total', 'N/A')}")
        print(f"\n[SOURCES] Fuentes consultadas:")
        for source, count in result.get('source_breakdown', {}).items():
            print(f"   - {source}: {count} propiedades")
        print(f"\n[MONEDA] Distribucion por moneda:")
        for currency, count in result.get('currency_distribution', {}).items():
            print(f"   - {currency}: {count} propiedades")
    else:
        print("[WARNING] No se pudieron obtener datos del mercado")
        if final_result.get('errors'):
            print("\nErrores encontrados:")
            for error in final_result['errors']:
                print(f"   - {error}")
    
    print("=" * 70)
    print(f"[OK] Proceso completado en: {datetime.now().isoformat()}")
    print("=" * 70)
    
    return final_result


def main():
    """Función principal que procesa los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Script de Scraping y Análisis de Mercado Inmobiliario",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
    python scraper.py --zona palermo
    python scraper.py -z belgrano -o venta -t casa
    python scraper.py --zona "microcentro" --output datos/scraping.json
    python scraper.py -z nordelta -o alquiler -t departamento
        """
    )
    
    parser.add_argument(
        '--zona', '-z',
        type=str,
        required=True,
        help='Zona o barrio a analizar (requerido)'
    )
    
    parser.add_argument(
        '--operacion', '-o',
        type=str,
        default=DEFAULT_OPERATION,
        choices=['venta', 'alquiler'],
        help=f'Tipo de operación (default: {DEFAULT_OPERATION})'
    )
    
    parser.add_argument(
        '--tipo', '-t',
        type=str,
        default=DEFAULT_PROPERTY_TYPE,
        help=f'Tipo de propiedad (default: {DEFAULT_PROPERTY_TYPE})'
    )
    
    parser.add_argument(
        '--output', '-f',
        type=str,
        default=DEFAULT_OUTPUT_FILE,
        help=f'Ruta del archivo JSON de salida (default: {DEFAULT_OUTPUT_FILE})'
    )
    
    # Parsear argumentos
    args = parser.parse_args()
    
    # Ejecutar el scraper
    result = run_scraper(
        zone=args.zona,
        operation=args.operacion,
        property_type=args.tipo,
        output_file=args.output
    )
    
    # Exit code basado en el resultado
    sys.exit(0 if result.get("success", False) else 1)


if __name__ == "__main__":
    main()
