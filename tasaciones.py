from utils import log, numero_a_emoji
from config import *
from database import *
from whatsapp_api import *
from logic.response_builder import WhatsAppResponse
import json
import requests
import os
from logic.constants import BARRIOS_VALIDOS
from campana_handlers import DESPEDIDA, iniciar_campana

# Cargar barrios válidos desde el mapa de tasación para que coincida exactamente con market_valuation_map.json
def _cargar_barrios_tasacion():
    try:
        map_path = os.path.join(os.path.dirname(__file__), "market_valuation_map.json")
        if os.path.exists(map_path):
            with open(map_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [k.title() for k in data.keys()]
    except Exception as e:
        log(f"⚠️ Error cargando market_valuation_map.json para barrios: {e}")
    return ['Palermo', 'Balvanera', 'Microcentro', 'Parque Avellaneda', 'Villa Lugano', 'Once', 'Almagro', 'Caballito', 'Belgrano', 'San Telmo', 'La Boca']

BARRIOS_VALIDOS = _cargar_barrios_tasacion()

def obtener_tasacion_local(barrio, tipo, estado, operacion='venta'):
    """Busca valoración en el mapa estadístico o BD local (Venta/Alquiler)"""
    try:
        # 1. Intentar con el mapa de valoración consolidado (Estadísticas 2026)
        map_path = os.path.join(os.path.dirname(__file__), "market_valuation_map.json")
        
        # Si no está en METAPATH, intentar buscarlo en la carpeta del backend si es local
        if not os.path.exists(map_path):
            backend_map = os.path.join(os.path.dirname(os.path.dirname(__file__)), "PAGINA WEB-IA", "BACKEND", "market_valuation_map.json")
            if os.path.exists(backend_map):
                map_path = backend_map

        if os.path.exists(map_path):
            log(f"📂 Archivo de mapa encontrado en: {map_path}")
            with open(map_path, 'r', encoding='utf-8') as f:
                vmap = json.load(f)
                
            barrio_key = barrio.lower().strip()
            op_key = operacion.lower().strip()
            tipo_key = tipo.lower().strip()
            log(f"🔎 Buscando en mapa: '{barrio_key}' - '{op_key}' - '{tipo_key}'")
            
            if barrio_key in vmap:
                # Acceder a la operación (venta/alquiler)
                op_data = vmap[barrio_key].get(op_key)
                if not op_data and op_key == 'venta': # Compatibilidad con mapas viejos sin 'venta' key
                    op_data = vmap[barrio_key] 
                
                if op_data:
                    stats = op_data.get(tipo_key)
                    if not stats and op_data:
                        # Fallback al primer tipo disponible en ese barrio/operacion
                        primer_tipo = next(iter(op_data))
                        stats = op_data[primer_tipo]
                        log(f"⚠️ Tipo '{tipo_key}' no hallado, usamos '{primer_tipo}'")
                    
                    if stats:
                        avg_m2 = stats['avg_m2']
                        moneda = stats.get('currency', 'USD' if op_key == 'venta' else 'ARS')
                        log(f"✅ Éxito: Promedio hallado {avg_m2} {moneda}/m2")
                        return {
                            "precio_m2": avg_m2,
                            "moneda": moneda,
                            "is_fallback": False,
                            "fuentes": ["Estadísticas de Mercado (Consolidado)"],
                            "muestra": stats.get('muestra', 0)
                        }
            else:
                log(f"❌ Barrio '{barrio_key}' no está en el mapa consolidado.")
        else:
            log(f"🚫 No se halló el archivo market_valuation_map.json en ninguna ruta local.")
        
        # 1.5 Intentar cargar desde URL (GitHub Pages o similar)
        remote_url = os.environ.get("VALUATION_MAP_URL")
        if remote_url:
            try:
                log(f"🌐 Intentando buscar mapa estadístico en URL remota: {remote_url}")
                resp = requests.get(remote_url, timeout=5)
                if resp.status_code == 200:
                    vmap = resp.json()
                    barrio_key = barrio.lower().strip()
                    op_key = operacion.lower().strip()
                    tipo_key = tipo.lower().strip()
                    
                    if barrio_key in vmap:
                        op_data = vmap[barrio_key].get(op_key) or (vmap[barrio_key] if op_key == 'venta' else None)
                        if op_data:
                            stats = op_data.get(tipo_key) or (next(iter(op_data.values())) if op_data else None)
                            if stats:
                                return {
                                    "precio_m2": stats['avg_m2'],
                                    "moneda": stats.get('currency', 'USD' if op_key == 'venta' else 'ARS'),
                                    "is_fallback": False,
                                    "fuentes": ["Estadísticas Remotas (GitHub Pages)"],
                                    "muestra": stats.get('muestra', 0)
                                }
            except Exception as e:
                log(f"⚠️ Error cargando mapa remoto: {str(e)}")

        # 2. Fallback Secundario: buscar en propiedades.json (raw data)
        path = os.path.join(os.path.dirname(__file__), "propiedades.json")
        if not os.path.exists(path):
            return None
            
        with open(path, 'r', encoding='utf-8') as f:
            propiedades = json.load(f)
            
        precios_m2 = []
        precios_barrio_solo = []
        
        op_key = operacion.lower().strip() # Ensure op_key is defined for this section
        
        for p in propiedades:
            barrio_match = p.get('barrio', '').lower().strip() == barrio.lower().strip()
            operacion_match = p.get('operacion', '').lower() == op_key
            tipo_match = p.get('tipo', '').lower().strip() == tipo.lower().strip()
            
            if barrio_match and operacion_match:
                m2 = float(p.get('metros_cuadrados', 0))
                precio = float(p.get('precio', 0))
                if m2 > 5 and precio > 0:
                    # Normalización simple para pesos (Usamos DOLAR_VALOR de config)
                    val_m2 = (precio / DOLAR_VALOR) / m2 if p.get('moneda_precio') == 'ARS' and op_key == 'venta' else precio / m2
                    precios_barrio_solo.append(val_m2)
                    if tipo_match:
                        precios_m2.append(val_m2)
        
        final_list = precios_m2 if precios_m2 else precios_barrio_solo
        if not final_list: return None
            
        avg_m2 = sum(final_list) / len(final_list)
        return {
            "precio_m2": avg_m2,
            "moneda": "USD" if op_key == 'venta' else "ARS",
            "is_fallback": True,
            "fuentes": ["Base de datos local"],
            "muestra": len(final_list)
        }
    except Exception as e:
        log(f"⚠️ Error en tasación local: {e}")
        return None


def obtener_tasacion_ia(barrio, tipo, m2, ambientes, estado, operacion='venta'):
    """Obtiene una valoración estimada usando el backend de IA con fallback local"""
    try:
        data_ia = None
        # 1. Intentar con el backend de IA
        url = f"{BASE_URL_AI}/api/valoracion"
        payload = {
            "barrio": barrio,
            "tipo": tipo,
            "m2": float(m2),
            "ambientes": int(ambientes),
            "estado": estado,
            "operacion": operacion
        }
        log(f"🧠 Solicitando valoración IA para {tipo} en {barrio} ({m2}m2)...")
        
        try:
            response = requests.post(url, json=payload, timeout=8)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    data_ia = data
        except Exception as conn_err:
            log(f"📡 Backend IA no alcanzable, intentando fallback local: {conn_err}")

        # 2. Obtener datos locales de market_valuation_map.json (siempre es bueno tenerlos listos)
        local_data = obtener_tasacion_local(barrio, tipo, estado, operacion)

        # 3. Decidir cuál usar: si IA tuvo éxito y no es fallback, la usamos.
        if data_ia and not data_ia.get("is_fallback"):
            return {
                "valor_estimado": data_ia.get("valor_estimado"),
                "precio_m2": data_ia.get("precio_m2_referencia"),
                "moneda": data_ia.get("moneda", "USD"),
                "is_fallback": False,
                "fuentes": data_ia.get("fuentes", []),
                "muestra": data_ia.get("muestra_size", 0),
                "fuente": "Dante AI Valuation",
                "detalles": data_ia.get("detalles", {})
            }
            
        # 4. Si la IA devolvió fallback o falló, usamos los datos locales si existen y son reales
        if local_data and not local_data.get("is_fallback"):
            # Aplicar ajustes de estado
            ajustes = {"Excelente": 1.10, "Muy bueno": 1.05, "Bueno": 1.00, "Regular": 0.85, "A refaccionar": 0.70}
            factor = ajustes.get(estado, 1.0)
            valor = local_data['precio_m2'] * float(m2) * factor
            return {
                "valor_estimado": round(valor, -2),
                "precio_m2": local_data['precio_m2'],
                "moneda": local_data.get('moneda', 'USD'),
                "is_fallback": False,
                "fuentes": local_data.get("fuentes", []),
                "muestra": local_data.get("muestra", 0),
                "fuente": "Mapa de Valoración Local"
            }

        # 5. Si todo falló (IA en fallback/error y Local no encontrado), usamos el fallback final referencial
        if not local_data:
            local_data = {
                "precio_m2": 2150.0 if operacion == 'venta' else 8500.0,
                "moneda": "USD" if operacion == 'venta' else "ARS",
                "is_fallback": True,
                "fuentes": [f"Promedio General CABA ({operacion.upper()})"],
                "muestra": 0
            }
            
        # Aplicar factor sobre el fallback final o el fallback de DB local
        ajustes = {"Excelente": 1.10, "Muy bueno": 1.05, "Bueno": 1.00, "Regular": 0.85, "A refaccionar": 0.70}
        factor = ajustes.get(estado, 1.0)
        valor = local_data['precio_m2'] * float(m2) * factor
        
        return {
            "valor_estimado": round(valor, -2),
            "precio_m2": local_data['precio_m2'],
            "moneda": local_data.get('moneda', 'USD'),
            "is_fallback": local_data.get("is_fallback", True),
            "fuentes": local_data.get("fuentes", []),
            "muestra": local_data.get("muestra", 0),
            "fuente": local_data.get("fuente", "Statistical Fallback")
        }
    except Exception as e:
        log(f"⚠️ Error crítico en obtención de tasación: {e}")
        return None


def manejar_menu_tasacion(text_lower, estado_usuario, user_id):
    """Inicia el flujo de tasación directamente con selección de barrio"""
    if 'data' not in estado_usuario or not isinstance(estado_usuario['data'], dict):
        estado_usuario['data'] = {}
    
    estado_usuario['data']['datos_tasacion'] = {
        "operacion": "venta"  # Forzar venta
    }
    estado_usuario['paso'] = 'tasacion_barrio_seleccion'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    # Mostrar la lista de barrios (NO llamar a la función de manejo)
    return mostrar_lista_barrios(estado_usuario, user_id)


def mostrar_lista_barrios(estado_usuario, user_id):
    """Muestra la lista de barrios disponibles para seleccionar"""
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if es_fb_ig:
        # Facebook/Instagram: mostrar texto con numeración
        barrios_texto = ""
        for i, barrio in enumerate(BARRIOS_VALIDOS, 1):
            barrios_texto += f"{i}. {barrio}\n"
        
        return {
            "type": "text",
            "body": f"📍 *Seleccioná el barrio de tu propiedad:*\n\n{barrios_texto}\n💡 *Envía el número o el nombre del barrio*\n\n1️⃣ Volver al menú\n2️⃣ Salir",
            "preview": False
        }
    else:
        # WhatsApp: lista interactiva
        rows_caba = [{"id": barrio, "title": barrio} for barrio in BARRIOS_VALIDOS]
        
        return WhatsAppResponse.list_menu(
            header="📍 Selección de Barrio",
            body="*¿En qué barrio se encuentra tu propiedad?*\n\nSeleccioná una opción de la lista:",
            button_text="Ver barrios",
            sections=[
                {
                    "title": "Barrios disponibles",
                    "rows": rows_caba
                }
            ],
            footer="Selecciona tu barrio 👇"
        )


def manejar_tasacion_operacion(text_lower, estado_usuario, user_id):
    """Guarda la operación e inicia la carga del barrio"""
    ops = {"1": "venta", "2": "alquiler"}
    if text_lower in ops:
        if 'datos_tasacion' not in estado_usuario['data']:
            estado_usuario['data']['datos_tasacion'] = {}
            
        estado_usuario['data']['datos_tasacion']['operacion'] = ops[text_lower]
        estado_usuario['paso'] = 'tasacion_barrio'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "📍 *¿En qué barrio se encuentra la propiedad?* (ej: Palermo, Belgrano, Tigre...)"
    else:
        return "⚠️ Por favor, elegí 1 para Venta o 2 para Alquiler."


# def manejar_tasacion_barrio(text, estado_usuario, user_id):
#     """Muestra lista de barrios para seleccionar"""
#     # Detectar plataforma
#     platform = estado_usuario.get('platform', 'whatsapp')
#     es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
#     # Si ya hay un barrio guardado (viene de la selección), procesarlo
#     if 'datos_tasacion' in estado_usuario['data'] and 'barrio_temp' in estado_usuario['data']['datos_tasacion']:
#         barrio_seleccionado = estado_usuario['data']['datos_tasacion'].get('barrio_temp')
#         if barrio_seleccionado:
#             # Guardar el barrio definitivo
#             estado_usuario['data']['datos_tasacion']['barrio'] = barrio_seleccionado
#             estado_usuario['data']['datos_tasacion'].pop('barrio_temp', None)
#             estado_usuario['paso'] = 'tasacion_tipo'
#             actualizar_estado_usuario(user_id, estado_usuario)
            
#             if es_fb_ig:
#                 return {
#                     "type": "text",
#                     "body": f"📍 Barrio seleccionado: *{barrio_seleccionado}* ✅\n\n🏠 *¿Qué tipo de propiedad es?*\n\n1️⃣ Departamento\n2️⃣ Casa\n3️⃣ PH\n4️⃣ Oficina / Local\n5️⃣ Terreno\n\n1️⃣ Volver al menú\n2️⃣ Salir\n\n💡 *Envía el número de la opción deseada*",
#                     "preview": False
#                 }
#             else:
#                 return {
#                     "type": "interactive_list",
#                     "body": f"📍 Barrio seleccionado: *{barrio_seleccionado}* ✅\n\n🏠 *¿Qué tipo de propiedad es?*",
#                     "button_text": "Ver tipos",
#                     "sections": [
#                         {
#                             "title": "Tipo de Propiedad",
#                             "rows": [
#                                 {"id": "1", "title": "Departamento"},
#                                 {"id": "2", "title": "Casa"},
#                                 {"id": "3", "title": "PH"},
#                                 {"id": "4", "title": "Oficina / Local"},
#                                 {"id": "5", "title": "Terreno"}
#                             ]
#                         }
#                     ],
#                     "footer": "Selecciona una opción 👇"
#                 }
    
#     # Primera vez: mostrar lista de barrios
#     if 'datos_tasacion' not in estado_usuario['data']:
#         estado_usuario['data']['datos_tasacion'] = {}
    
#     estado_usuario['paso'] = 'tasacion_barrio_seleccion'
#     actualizar_estado_usuario(user_id, estado_usuario)
    
#     # Crear rows para la lista de barrios (agrupados por zona)
#     rows_caba = []
#     rows_gba = []
    
#     for barrio in BARRIOS_VALIDOS:
#         rows_caba.append({"id": barrio, "title": barrio})
    
#     if es_fb_ig:
#         # Facebook/Instagram: mostrar texto con numeración
#         barrios_texto = ""
#         for i, barrio in enumerate(BARRIOS_VALIDOS, 1):
#             barrios_texto += f"{i}. {barrio}\n"
        
#         return {
#             "type": "text",
#             "body": f"📍 *Seleccioná el barrio de tu propiedad:*\n\n{barrios_texto}\n💡 *Envía el número o el nombre del barrio*\n\n1️⃣ Volver al menú\n2️⃣ Salir",
#             "preview": False
#         }
#     else:
#         # WhatsApp: lista interactiva
#         return WhatsAppResponse.list_menu(
#             header="📍 Selección de Barrio",
#             body="*¿En qué barrio se encuentra tu propiedad?*\n\nSeleccioná una opción de la lista:",
#             button_text="Ver barrios",
#             sections=[
#                 {
#                     "title": "Barrios disponibles",
#                     "rows": rows_caba
#                 }
#             ],
#             footer="Selecciona tu barrio 👇"
#         )




def manejar_tasacion_barrio_seleccion(text, estado_usuario, user_id):
    """Maneja la selección de barrio desde la lista"""
    text_stripped = text.strip()
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    # Si no hay texto (caso inicial), mostrar la lista
    if not text_stripped:
        return mostrar_lista_barrios(estado_usuario, user_id)
    
    # Comandos de navegación
    if text_stripped.lower() in ["menu", "m", "volver"] or text_stripped == "1":
        estado_usuario['paso'] = 'campana_intent'
        actualizar_estado_usuario(user_id, estado_usuario)
        return iniciar_campana(platform)
    
    if text_stripped.lower() in ["salir", "s", "exit"] or text_stripped == "2":
        estado_usuario['paso'] = 'campana_inicio'
        actualizar_estado_usuario(user_id, estado_usuario)
        return DESPEDIDA
    
    # Buscar el barrio seleccionado (por nombre o por número)
    barrio_seleccionado = None
    
    # Intentar por número (para FB/IG)
    if text_stripped.isdigit():
        idx = int(text_stripped) - 1
        if 0 <= idx < len(BARRIOS_VALIDOS):
            barrio_seleccionado = BARRIOS_VALIDOS[idx]
    
    # Intentar por nombre exacto
    if not barrio_seleccionado:
        for barrio in BARRIOS_VALIDOS:
            if barrio.lower() == text_stripped.lower():
                barrio_seleccionado = barrio
                break
    
    # Intentar por coincidencia parcial (ej: "pale" -> "Palermo")
    if not barrio_seleccionado:
        for barrio in BARRIOS_VALIDOS:
            if barrio.lower().startswith(text_stripped.lower()) or text_stripped.lower() in barrio.lower():
                barrio_seleccionado = barrio
                break
    
    if barrio_seleccionado:
        # Guardar el barrio definitivamente
        if 'datos_tasacion' not in estado_usuario['data']:
            estado_usuario['data']['datos_tasacion'] = {}
        
        estado_usuario['data']['datos_tasacion']['barrio'] = barrio_seleccionado
        estado_usuario['paso'] = 'tasacion_tipo'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Mostrar siguiente paso (selección de tipo de propiedad)
        if es_fb_ig:
            return {
                "type": "text",
                "body": f"📍 Barrio seleccionado: *{barrio_seleccionado}* ✅\n\n🏠 *¿Qué tipo de propiedad es?*\n\n1️⃣ Departamento\n2️⃣ Casa\n3️⃣ PH\n4️⃣ Oficina / Local\n5️⃣ Terreno\n\n1️⃣ Volver al menú\n2️⃣ Salir\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return {
                "type": "interactive_list",
                "body": f"📍 Barrio seleccionado: *{barrio_seleccionado}* ✅\n\n🏠 *¿Qué tipo de propiedad es?*",
                "button_text": "Ver tipos",
                "sections": [
                    {
                        "title": "Tipo de Propiedad",
                        "rows": [
                            {"id": "1", "title": "Departamento"},
                            {"id": "2", "title": "Casa"},
                            {"id": "3", "title": "PH"},
                            {"id": "4", "title": "Oficina / Local"},
                            {"id": "5", "title": "Terreno"}
                        ]
                    }
                ],
                "footer": "Selecciona una opción 👇"
            }
    else:
        # Barrio no válido, mostrar la lista nuevamente
        return mostrar_lista_barrios(estado_usuario, user_id)

def manejar_tasacion_tipo(text_lower, estado_usuario, user_id):
    """Guarda el tipo e inicia la carga de m2"""
    tipos = {
        "1": "Departamento",
        "2": "Casa",
        "3": "PH",
        "4": "Oficina",
        "5": "Terreno"
    }
    
    # Detectar plataforma
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if text_lower in tipos:
        if 'datos_tasacion' not in estado_usuario['data']:
            estado_usuario['data']['datos_tasacion'] = {}
            
        estado_usuario['data']['datos_tasacion']['tipo'] = tipos[text_lower]
        estado_usuario['paso'] = 'tasacion_m2'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        cuerpo = "📏 *¿Cuántos m² cubiertos tiene la propiedad?*\n_(Ingresá solo el número, ej: 65)_"
        
        if es_fb_ig:
            return {
                "type": "text",
                "body": f"{cuerpo}\n\n1️⃣ Volver al menú\n2️⃣ Salir\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body=cuerpo,
                buttons=[
                    {"id": "c_menu", "title": "📋 Volver al menú"},
                    {"id": "c_salir", "title": "❌ Salir"}
                ],
                footer="🏠 Dante Propiedades · Tu lugar ideal 🗝️"
            )
    else:
        # Si no es una opción válida, mostrar el menú de tipos nuevamente con botones (sin hint)
        if es_fb_ig:
            return {
                "type": "text",
                "body": "⚠️ Opción no válida.\n\n🏠 *¿Qué tipo de propiedad es?*\n\n1️⃣ Departamento\n2️⃣ Casa\n3️⃣ PH\n4️⃣ Oficina / Local\n5️⃣ Terreno\n\n1️⃣ Volver al menú\n2️⃣ Salir\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            # WhatsApp: lista interactiva SIN el hint en el footer
            return {
                "type": "interactive_list",
                "body": "⚠️ Opción no válida.\n\n🏠 *¿Qué tipo de propiedad es?*",
                "button_text": "Ver tipos",
                "sections": [
                    {
                        "title": "Tipo de Propiedad",
                        "rows": [
                            {"id": "1", "title": "Departamento"},
                            {"id": "2", "title": "Casa"},
                            {"id": "3", "title": "PH"},
                            {"id": "4", "title": "Oficina / Local"},
                            {"id": "5", "title": "Terreno"}
                        ]
                    }
                ],
                "footer": "Selecciona una opción 👇"  # ← Footer limpio
            }

def manejar_tasacion_m2(text, estado_usuario, user_id):
    """Guarda los m2 e inicia la carga de estado (saltando ambientes)"""
    try:
        m2_str = text.replace(',', '.').strip()
        m2 = float(m2_str)
        
        # Validar que m2 sea un número positivo y razonable
        if m2 < 5 or m2 > 10000:
            cuerpo = "⚠️ Por favor, ingresá un número válido de m² (entre 5 y 10000).\n\nEjemplo: 65, 120, 200, etc."
            
            platform = estado_usuario.get('platform', 'whatsapp')
            es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
            
            if es_fb_ig:
                return {
                    "type": "text",
                    "body": f"{cuerpo}\n\n1️⃣ Volver al menú\n2️⃣ Salir\n\n💡 *Envía el número de la opción deseada*",
                    "preview": False
                }
            else:
                return WhatsAppResponse.buttons(
                    body=cuerpo,
                    buttons=[
                        {"id": "c_menu", "title": "📋 Volver al menú"},
                        {"id": "c_salir", "title": "❌ Salir"}
                    ],
                    footer="🏠 Dante Propiedades · Tu lugar ideal 🗝️"
                )
        
        if 'datos_tasacion' not in estado_usuario['data']:
            estado_usuario['data']['datos_tasacion'] = {}
            
        estado_usuario['data']['datos_tasacion']['m2'] = m2
        
        # Asignar un valor por defecto para ambientes (no influye en la tasación)
        estado_usuario['data']['datos_tasacion']['ambientes'] = 1
        
        # Saltar directamente al estado de la propiedad
        estado_usuario['paso'] = 'tasacion_estado'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Detectar plataforma para mostrar estado
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
        
        if es_fb_ig:
            # Facebook/Instagram: texto con números con emoji
            return {
                "type": "text",
                "body": "🏗️ *¿En qué estado se encuentra la propiedad?*\n\n1️⃣ Excelente / A estrenar\n2️⃣ Muy bueno\n3️⃣ Bueno\n4️⃣ Regular\n5️⃣ A refaccionar\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            # WhatsApp: lista interactiva
            return {
                "type": "interactive_list",
                "body": "🏗️ *¿En qué estado se encuentra la propiedad?*",
                "button_text": "Estado",
                "sections": [
                    {
                        "title": "Condición",
                        "rows": [
                            {"id": "1", "title": "Excelente / A estrenar"},
                            {"id": "2", "title": "Muy bueno"},
                            {"id": "3", "title": "Bueno"},
                            {"id": "4", "title": "Regular"},
                            {"id": "5", "title": "A refaccionar"}
                        ]
                    }
                ],
                "footer": "Selecciona una opción 👇"
            }
    except ValueError:
        log(f"⚠️ Error: No se pudo convertir '{text}' a número")
        cuerpo = "⚠️ Por favor, ingresá un número válido para los metros cuadrados (usa . para decimales si es necesario).\n\nEjemplo: 65, 120.5, 200"
        
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
        
        if es_fb_ig:
            return {
                "type": "text",
                "body": f"{cuerpo}\n\n1️⃣ Volver al menú\n2️⃣ Salir\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body=cuerpo,
                buttons=[
                    {"id": "c_menu", "title": "📋 Volver al menú"},
                    {"id": "c_salir", "title": "❌ Salir"}
                ],
                footer="🏠 Dante Propiedades · Tu lugar ideal 🗝️"
            )
    except Exception as e:
        log(f"🔥 Error crítico en manejar_tasacion_m2: {e}")
        return "⚠️ Por favor, ingresá un número válido para los metros cuadrados."
    
    
    
    

def manejar_tasacion_ambientes(text, estado_usuario, user_id):
    """Guarda ambientes e inicia la carga de estado"""
    try:
        amb_str = "".join(filter(str.isdigit, text))
        ambientes = int(amb_str) if amb_str else 0
        
        if ambientes < 1:
            cuerpo = "⚠️ Por favor, ingresá un número válido de ambientes (mínimo 1).\n\nEjemplo: 1, 2, 3, etc."
            
            platform = estado_usuario.get('platform', 'whatsapp')
            es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
            
            if es_fb_ig:
                return {
                    "type": "text",
                    "body": f"{cuerpo}\n\n1️⃣ Volver al menú\n2️⃣ Salir\n\n💡 *Envía el número de la opción deseada*",
                    "preview": False
                }
            else:
                return WhatsAppResponse.buttons(
                    body=cuerpo,
                    buttons=[
                        {"id": "c_menu", "title": "📋 Volver al menú"},
                        {"id": "c_salir", "title": "❌ Salir"}
                    ],
                    footer="🏠 Dante Propiedades · Tu lugar ideal 🗝️"
                )
        
        if 'datos_tasacion' not in estado_usuario['data']:
            estado_usuario['data']['datos_tasacion'] = {}
            
        estado_usuario['data']['datos_tasacion']['ambientes'] = ambientes
        estado_usuario['paso'] = 'tasacion_estado'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Detectar plataforma para mostrar estado
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
        
        if es_fb_ig:
            # Facebook/Instagram: texto con números con emoji
            return {
                "type": "text",
                "body": "🏗️ *¿En qué estado se encuentra la propiedad?*\n\n1️⃣ Excelente / A estrenar\n2️⃣ Muy bueno\n3️⃣ Bueno\n4️⃣ Regular\n5️⃣ A refaccionar\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            # WhatsApp: lista interactiva
            return {
                "type": "interactive_list",
                "body": "🏗️ *¿En qué estado se encuentra la propiedad?*",
                "button_text": "Estado",
                "sections": [
                    {
                        "title": "Condición",
                        "rows": [
                            {"id": "1", "title": "Excelente / A estrenar"},
                            {"id": "2", "title": "Muy bueno"},
                            {"id": "3", "title": "Bueno"},
                            {"id": "4", "title": "Regular"},
                            {"id": "5", "title": "A refaccionar"}
                        ]
                    }
                ],
                "footer": "Selecciona una opción 👇"
            }
    except Exception as e:
        log(f"⚠️ Error en manejar_tasacion_ambientes: {e}")
        
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
        
        cuerpo = "⚠️ Por favor, ingresá un número para los ambientes. (Ejemplo: 2, 3, 4)"
        
        if es_fb_ig:
            return {
                "type": "text",
                "body": f"{cuerpo}\n\n1️⃣ Volver al menú\n2️⃣ Salir\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body=cuerpo,
                buttons=[
                    {"id": "c_menu", "title": "📋 Volver al menú"},
                    {"id": "c_salir", "title": "❌ Salir"}
                ],
                footer="🏠 Dante Propiedades · Tu lugar ideal 🗝️"
            )
            
            

def manejar_tasacion_estado(text_lower, estado_usuario, user_id):
    """Finaliza la recolección de datos y muestra la tasación"""
    estados = {
        "1": "Excelente",
        "2": "Muy bueno",
        "3": "Bueno",
        "4": "Regular",
        "5": "A refaccionar"
    }
    
    # Detectar plataforma
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if text_lower in estados:
        if 'datos_tasacion' not in estado_usuario['data']:
            log(f"❌ Error: datos_tasacion no encontrado en estado_usuario['data']")
            return "⚠️ Ocurrió un error en el flujo. Por favor, enviá 'Hola' para comenzar de nuevo."
            
        # Validar que todos los datos requeridos estén presentes
        datos = estado_usuario['data']['datos_tasacion']
        campos_requeridos = ['barrio', 'tipo', 'm2', 'ambientes']
        
        for campo in campos_requeridos:
            if campo not in datos or datos[campo] is None or str(datos[campo]).strip() == '':
                log(f"❌ Error: Campo '{campo}' faltante o vacío en datos_tasacion: {datos}")
                return f"⚠️ Error: Falta información en el campo '{campo}'. Por favor, iniciá nuevamente con 'Hola'."
        
        # Convertir m2 y ambientes a números si es necesario
        try:
            datos['m2'] = float(datos['m2'])
            datos['ambientes'] = int(datos['ambientes'])
        except (ValueError, TypeError) as e:
            log(f"❌ Error al convertir m2 o ambientes: {e}, datos: {datos}")
            return f"⚠️ Error al procesar los datos. Por favor, iniciá nuevamente con 'Hola'."
        
        # Agregar el estado
        estado_usuario['data']['datos_tasacion']['estado'] = estados[text_lower]
        actualizar_estado_usuario(user_id, estado_usuario)
        
        log(f"✅ Datos de tasación completos: {estado_usuario['data']['datos_tasacion']}")
        return _finalizar_tasacion_y_responder(user_id, estado_usuario, estado_usuario['data']['datos_tasacion'])
    else:
        # Opción inválida: mostrar nuevamente la lista de estados (adaptada para FB/IG)
        if es_fb_ig:
            return {
                "type": "text",
                "body": "⚠️ Opción no válida.\n\n🏗️ *¿En qué estado se encuentra la propiedad?*\n\n1️⃣ Excelente / A estrenar\n2️⃣ Muy bueno\n3️⃣ Bueno\n4️⃣ Regular\n5️⃣ A refaccionar\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return {
                "type": "interactive_list",
                "body": "⚠️ Opción no válida.\n\n🏗️ *¿En qué estado se encuentra la propiedad?*",
                "button_text": "Estado",
                "sections": [
                    {
                        "title": "Condición",
                        "rows": [
                            {"id": "1", "title": "Excelente / A estrenar"},
                            {"id": "2", "title": "Muy bueno"},
                            {"id": "3", "title": "Bueno"},
                            {"id": "4", "title": "Regular"},
                            {"id": "5", "title": "A refaccionar"}
                        ]
                    }
                ],
                "footer": "Selecciona una opción 👇"
            }
            
            
            

def _finalizar_tasacion_y_responder(user_id, estado_usuario, datos):
    """Lógica compartida para calcular tasación, registrar lead y responder"""
    try:
        # 1. Obtener tasación
        tasacion = obtener_tasacion_ia(
            datos['barrio'], 
            datos['tipo'], 
            datos['m2'], 
            datos['ambientes'], 
            datos['estado'],
            datos.get('operacion', 'venta')
        )
        
        # Validar que tasacion no sea None
        if not tasacion:
            log(f"⚠️ tasacion_ia retornó None para los datos: {datos}")
            # Retornar un mensaje de error más descriptivo
            return WhatsAppResponse.buttons(
                header="⚠️ ERROR EN LA TASACIÓN",
                body="Ocurrió un error al procesar tu solicitud. Por favor, intenta de nuevo o contacta a un asesor.",
                buttons=[
                    {"id": "10", "title": "📈 Reintentar Tasación"},
                    {"id": "5", "title": "👤 Hablar con Asesor"},
                    {"id": "m", "title": "🔙 Volver al Menú"}
                ]
            )
        
        # 2. Registrar Lead
        detalles = f"Tasación solicitada: {datos['tipo']} en {datos['barrio']}, {datos['m2']}m2, {datos['ambientes']} amb, estado {datos['estado']}."
        if tasacion:
            detalles += f" Resultado IA: {tasacion['valor_estimado']:,.0f} {tasacion['moneda']}"
            
        registrar_lead(user_id, "TASACION_VIRTUAL", "tasacion", detalles)
        notificar_agente(f"📈 *NUEVO LEAD DE TASACIÓN*\n📞 Tel: +{user_id}\n📝 {detalles}")
        
        # 3. Respuesta al usuario - Preparar variables
        intro_mercado = f"Basado en el análisis estadístico de mercado para *{datos['barrio']}*:"
        if tasacion.get("is_fallback") and tasacion.get("muestra", 0) <= 1:
            intro_mercado = "Basado en el promedio general del mercado inmobiliario (estamos recolectando más datos específicos de tu zona):"
            
        # 4. Info de Fuentes
        fuentes_str = ", ".join(tasacion.get("fuentes", ["Mercado Local"]))
        muestra = tasacion.get("muestra", 0)
        info_fuentes = f"\n🔍 *Análisis:* basado en {muestra} propiedades de {fuentes_str}."

        mensaje_body = f"""📊 *RESULTADO DE TU TASACIÓN VIRTUAL*

{intro_mercado}

🏠 *Propiedad:* {datos['tipo']}
📏 *Superficie:* {datos['m2']} m²
💰 *Valor estimado:* {tasacion['moneda']} ${tasacion['valor_estimado']:,.0f}
📈 *Precio promedio m²:* {tasacion['moneda']} ${tasacion['precio_m2']:,.0f}
{info_fuentes}

⚠️ *Nota:* Esta es una estimación orientativa basada en datos de mercado. Para una tasación profesional, un asesor debe visitar la propiedad.

¿Qué deseas hacer?"""
        
        estado_usuario['paso'] = 'tasacion_esperando_contacto'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Detectar plataforma
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
        
        if es_fb_ig:
            # Facebook/Instagram: texto con números
            return {
                "type": "text",
                "body": f"{mensaje_body}\n\n1️⃣ ✅ Deseas una Tasación profesional con visita\n2️⃣ ⏭️ No por ahora\n3️⃣ 🔙 Menú Principal\n4️⃣ ❌ Salir\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            # WhatsApp: menú de lista interactivo
            return WhatsAppResponse.list_menu(
                body=mensaje_body,
                button_text="Opciones",
                sections=[
                    {
                        "title": "Acciones",
                        "rows": [
                            {"id": "1", "title": "✅ Deseas una Tasación", "description": "Profesional con visita"},
                            {"id": "2", "title": "⏭️ No por ahora", "description": "Continuar explorando"},
                            {"id": "m", "title": "🔙 Menú Principal", "description": "Ir al inicio"},
                            {"id": "s", "title": "❌ Salir", "description": "Terminar sesión"}
                        ]
                    }
                ],
                footer="Selecciona una opción 👇"
            )
    except Exception as e:
        log(f"🔥 Error en _finalizar_tasacion_y_responder: {e}")
        import traceback
        log(traceback.format_exc())
        return "❌ Ocurrió un error al procesar la tasación. Por favor contacta a un asesor enviando '5'."
    
    


def manejar_tasacion_contacto(text_lower, estado_usuario, user_id):
    """Maneja la respuesta final del flujo de tasación"""
    # Mapear IDs de botones del menú interactivo
    mapeo_botones = {
        "1": "1",
        "2": "2",
        "m": "menu",
        "s": "salir"
    }
    
    comando = mapeo_botones.get(text_lower, text_lower)
    
    if comando == "1":
        notificar_agente(f"📞 *SOLICITUD DE TASACIÓN PROFESIONAL*\n📞 Tel: +{user_id}\nEl cliente solicitó contacto humano después de la tasación virtual.")
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "✅ ¡Perfecto! Un asesor se pondrá en contacto con vos a la brevedad para coordinar la visita."
    
    elif comando == "menu":
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "WELCOME_FLOW_TRIGGER"
    
    elif comando == "salir":
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "🏠¡Gracias por confiar en Dante Propiedades! 🗝️"
    
    else:
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "🏠 Entendido. Si necesitás algo más, acá estoy 🗝️. 😊"
        
