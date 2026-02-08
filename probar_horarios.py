import json
from datetime import datetime, timedelta
import sys
import os

# Importar funciones de main.py
try:
    from main import obtener_horarios_disponibles, cargar_propiedades, cargar_configuracion_horarios, CITAS_DISPONIBLES, obtener_texto_dias_habiles, obtener_texto_horarios
except ImportError:
    print("❌ Error: No se pudo importar main.py. Asegúrate de estar en el directorio correcto.")
    sys.exit(1)

def mostrar_menu_propiedades(propiedades):
    print("\n🏠 PROPIEDADES DISPONIBLES:")
    print(f"{'ID':<10} | {'TÍTULO'}")
    print("-" * 50)
    for p in propiedades:
        print(f"{p.get('id_temporal', 'N/A'):<10} | {p.get('titulo', 'Sin título')}")
    print("-" * 50)

def probar_logica():
    print("\n🧪 PRUEBA DE HORARIOS DE VISITA")
    print("===============================\n")

    # 1. Cargar datos
    propiedades = cargar_propiedades()
    config = cargar_configuracion_horarios()
    
    while True:
        mostrar_menu_propiedades(propiedades)
        
        prop_id = input("\n👉 Ingresa el ID de la propiedad (o 'salir'): ").strip()
        if prop_id.lower() == 'salir':
            break
            
        # Verificar si tiene configuración específica
        tiene_config = prop_id in config.get('propiedades', {})
        tipo_config = "ESPECÍFICA" if tiene_config else "GLOBAL"
        print(f"\nℹ️ Configuración usada: {tipo_config}")
        
        if tiene_config:
            c = config['propiedades'][prop_id]
            print(f"   Días hábiles: {c.get('dias_habiles')}")
            print(f"   Horarios: {c.get('horarios')}")
        else:
            c = config['configuracion_global']
            print(f"   Días hábiles: {c.get('dias_habiles')} (Default)")
            print(f"   Horarios: {len(c.get('horarios', []))} turnos (Default)")
            
        # Probar texto descriptivo
        try:
            texto_dias = obtener_texto_dias_habiles(prop_id)
            texto_horarios = obtener_texto_horarios(prop_id)
            print(f"   📝 Texto días hábiles: '{texto_dias}'")
            print(f"   📝 Texto horarios: '{texto_horarios}'")
        except Exception as e:
            print(f"   ⚠️ Error obteniendo texto días/horarios: {e}")

        fecha_str = input("\n📅 Ingresa una fecha (YYYY-MM-DD): ").strip()
        
        try:
            # Llamar a la función real de main.py
            horarios = obtener_horarios_disponibles(fecha_str, prop_id)
            
            print(f"\n✅ RESULTADO PARA {prop_id} el {fecha_str}:")
            if horarios:
                print(f"   Turnos disponibles ({len(horarios)}): {', '.join(horarios)}")
            else:
                print("   ❌ NO HAY TURNOS DISPONIBLES (Día no hábil o cupo lleno)")
                
        except Exception as e:
            print(f"❌ Error al consultar: {e}")
            
        input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    probar_logica()
