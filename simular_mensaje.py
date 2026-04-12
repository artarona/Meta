import os
import sys
import json
from datetime import datetime

# Añadir el directorio actual al path para importar módulos locales
sys.path.append(os.getcwd())

print("🚀 Iniciando Simulador de Mensajes para Dante Propiedades...")

try:
    # Intentar importar la lógica del bot
    # Nota: Puede fallar por dependencias como google-genai en entornos locales sin instalar
    import main
    from main import get_bot_response
    from database import obtener_estado_usuario
    print("✅ Lógica del bot cargada correctamente.\n")
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("\n💡 TIP: Este error suele deberse a que falta la librería 'google-genai'.")
    print("Prueba ejecutando: pip install google-genai")
    print("\nIntentando cargar el simulador en modo 'Sin IA' para que puedas probar los menús...")
    
    # Mocking components to allow limited simulation
    import sys
    from unittest.mock import MagicMock
    
    # Mockear el cliente de gemini si falla
    if 'genai' in str(e) or 'gemini' in str(e):
        mock_logic = MagicMock()
        sys.modules['logic.gemini_client'] = mock_logic
        mock_logic.call_gemini_with_rotation.return_value = "🤖 [Modo Simulación: IA Desactivada]"
        
        # Re-intentar importación
        try:
            import main
            from main import get_bot_response
            from database import obtener_estado_usuario
            print("⚠️ Lógica cargada en MODO SEGURO (Sin IA).")
        except Exception as e2:
            print(f"❌ No se pudo recuperar: {e2}")
            sys.exit(1)
    else:
        sys.exit(1)
except Exception as e:
    print(f"❌ Error inesperado: {e}")
    sys.exit(1)

def print_separator():
    print("-" * 50)

def main():
    user_id = "sim_user_123456"
    print(f"👤 Iniciando sesión de simulacro para el Usuario ID: {user_id}")
    print("Escribe 'salir' para terminar o 'estado' para ver el contexto actual.\n")
    
    while True:
        try:
            user_input = input("👉 Mensaje (Tú): ").strip()
            
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("👋 Simulador terminado.")
                break
                
            if user_input.lower() == 'estado':
                estado = obtener_estado_usuario(user_id)
                print("\n📊 ESTADO ACTUAL DEL USUARIO:")
                print(json.dumps(estado, indent=4, default=str, ensure_ascii=False))
                print()
                continue

            if not user_input:
                continue

            print_separator()
            print(f"⏳ Procesando mensaje: '{user_input}'...")
            
            # Obtener respuesta del bot
            # get_bot_response maneja tanto el procesamiento como la actualización del estado
            respuesta = get_bot_response(user_input, user_id)
            
            print(f"\n🤖 RESPUESTA DEL BOT:")
            
            if isinstance(respuesta, dict):
                # UI de Simulación de WhatsApp
                print("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
                
                # Cuerpo del mensaje
                body = respuesta.get('body', respuesta.get('text', ''))
                print(f"┃ {body}")
                print("┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫")
                
                # Botones (Tipo Interactive Button)
                if 'buttons' in respuesta:
                    for b in respuesta['buttons']:
                        title = b.get('title', '').center(48)
                        print(f"┃ [ {title} ] ┃")
                
                # Menú de lista (Tipo Interactive List)
                if 'sections' in respuesta:
                    print("┃ 📋 Menú de opciones:                             ┃")
                    for s in respuesta['sections']:
                        if s.get('title'):
                            print(f"┃ --- {s.get('title').ljust(42)} --- ┃")
                        for r in s.get('rows', []):
                            row_text = f"[{r.get('id')}] {r.get('title')}"
                            print(f"┃ • {row_text.ljust(45)} ┃")
                
                print("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
            else:
                # Texto simple con recuadro
                print("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
                for line in str(respuesta).split('\n'):
                    print(f"┃ {line.ljust(48)} ┃")
                print("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
            
            # Ver el nuevo paso del estado
            nuevo_estado = obtener_estado_usuario(user_id)
            print(f"\n📍 Nuevo paso: {nuevo_estado.get('paso', 'S/D')}")
            print_separator()
            
        except KeyboardInterrupt:
            print("\n👋 Simulador terminado.")
            break
        except Exception as e:
            print(f"\n❌ Error procesando mensaje: {e}")
            import traceback
            traceback.print_exc()
            print_separator()

if __name__ == "__main__":
    main()
