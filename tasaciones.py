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


# ============================================================
# HELPERS: Lectura dinámica de precios_barrios.json
# ============================================================

def cargar_precios_barrios():
    """Carga precios_barrios.json completo. Devuelve {} si falla."""
    try:
        path = os.path.join(os.path.dirname(__file__), "precios_barrios.json")
        if not os.path.exists(path):
            log(f"⚠️ precios_barrios.json no encontrado en {path}")
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(f"⚠️ Error cargando precios_barrios.json: {e}")
        return {}


def obtener_barrios_disponibles(operacion='venta'):
    """
    Devuelve lista de barrios (lowercase) que tienen datos para esa operación.
    Ejemplo: ['balvanera', 'belgrano', 'palermo', 'recoleta']
    """
    data = cargar_precios_barrios()
    barrios = set()
    op = operacion.lower().strip()
    for entry in data.values():
        if entry.get('operacion', '').lower().strip() == op:
            zona = entry.get('zona', '').lower().strip()
            if zona:
                barrios.add(zona)
    return sorted(barrios)


def obtener_tipos_disponibles(barrio, operacion='venta'):
    """
    Devuelve lista de tipos (lowercase) disponibles para ese barrio+operación.
    Ejemplo: ['casa', 'departamento', 'ph']
    """
    data = cargar_precios_barrios()
    b = barrio.lower().strip()
    op = operacion.lower().strip()
    tipos = set()
    for entry in data.values():
        if (entry.get('zona', '').lower().strip() == b and
            entry.get('operacion', '').lower().strip() == op):
            tipo = entry.get('tipo', '').lower().strip()
            if tipo:
                tipos.add(tipo)
    return sorted(tipos)


def capitalizar_barrio(barrio_lower):
    """Convierte 'balvanera' → 'Balvanera' (para mostrar bonito)."""
    return barrio_lower.replace('_', ' ').title()


def capitalizar_tipo(tipo_lower):
    """Mapea tipos internos a etiquetas amigables."""
    mapa = {
        'departamento': 'Departamento',
        'casa': 'Casa',
        'ph': 'PH',
        'oficina': 'Oficina / Local',
        'local': 'Oficina / Local',
        'terreno': 'Terreno',
        'lote': 'Terreno',
        'monoambiente': 'Monoambiente',
    }
    return mapa.get(tipo_lower, tipo_lower.title())


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

def obtener_tasacion_precios_barrios(barrio, tipo, estado, operacion='venta'):
    """
    Lee precios_barrios.json y devuelve el precio/m2 YA ajustado por estado.
    
    Reglas:
    - Excelente / A estrenar → precio_nuevo_m2
    - Muy bueno             → precio_nuevo_m2 * 0.80
    - Bueno                 → precio_usado_m2
    - Regular               → precio_usado_m2 * 0.80
    - A refaccionar         → precio_usado_m2 * 0.60
    """
    try:
        path = os.path.join(os.path.dirname(__file__), "precios_barrios.json")
        if not os.path.exists(path):
            log(f"🚫 precios_barrios.json no encontrado en {path}")
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Normalizar claves de búsqueda
        barrio_key = barrio.lower().strip()
        op_key = operacion.lower().strip()
        tipo_key = tipo.lower().strip()
        
        # Mapeo de tipo: el código usa "Departamento", "Casa", "PH", "Oficina", "Terreno"
        # en el JSON probablemente "departamento", "casa", "ph", "oficina", "terreno"
        tipo_variantes = {
            'departamento': ['departamento', 'departamentos', 'depto'],
            'casa': ['casa', 'casas'],
            'ph': ['ph'],
            'oficina': ['oficina', 'oficinas', 'local', 'locales'],
            'terreno': ['terreno', 'terrenos', 'lote', 'lotes']
        }
        
        # Intentar con cada variante de tipo
        candidatos = []
        for variante in tipo_variantes.get(tipo_key, [tipo_key]):
            clave = f"{barrio_key}_{op_key}_{variante}"
            if clave in data:
                candidatos.append((variante, data[clave]))
        
        if not candidatos:
            log(f"❌ No hay entrada en precios_barrios para: {barrio_key}_{op_key}_{tipo_key}")
            return None
        
        # Usar el primer candidato encontrado
        variante_usada, entry = candidatos[0]
        precio_usado = entry.get('precio_usado_m2', 0)
        precio_nuevo = entry.get('precio_nuevo_m2', 0)
        
        if precio_usado <= 0 and precio_nuevo <= 0:
            log(f"⚠️ Entrada sin precios válidos: {entry}")
            return None
        
        # Aplicar factor según estado elegido
        estado_norm = estado.strip() if estado else "Bueno"
        
        ajustes = {
            "Excelente": ("nuevo", 1.00),
            "A estrenar": ("nuevo", 1.00),
            "Muy bueno": ("nuevo", 0.80),
            "Bueno": ("usado", 1.00),
            "Regular": ("usado", 0.80),
            "A refaccionar": ("usado", 0.60),
        }
        
        base, factor = ajustes.get(estado_norm, ("usado", 1.00))
        precio_base = precio_nuevo if base == "nuevo" else precio_usado
        precio_final_m2 = precio_base * factor
        
        log(f"✅ precios_barrios: {barrio_key}/{op_key}/{tipo_key} → "
            f"nuevo={precio_nuevo:.2f}, usado={precio_usado:.2f}, "
            f"estado='{estado_norm}' ({base} × {factor}) = {precio_final_m2:.2f}")
        
        return {
            "precio_m2": precio_final_m2,
            "precio_usado_m2": precio_usado,
            "precio_nuevo_m2": precio_nuevo,
            "moneda": "USD" if op_key == 'venta' else "ARS",
            "is_fallback": False,
            "estado_aplicado": True,   # ← CLAVE: evita doble multiplicación
            "estado": estado_norm,
            "fuentes": [f"Análisis de Mercado (Precios {base.capitalize()})"],
            "muestra": entry.get('cantidad_usados', 0) + entry.get('cantidad_nuevos', 0),
            "fecha_datos": entry.get('fecha', 'Sin fecha')
        }
    except Exception as e:
        log(f"⚠️ Error leyendo precios_barrios.json: {e}")
        import traceback
        log(traceback.format_exc())
        return None




def obtener_tasacion_ia(barrio, tipo, m2, ambientes, estado, operacion='venta'):
    """Obtiene una valoración estimada usando la cascada:
    1. precios_barrios.json (con factor de estado aplicado)
    2. Backend IA externo
    3. market_valuation_map.json
    4. propiedades.json
    5. Valores hardcoded
    """
    try:
        # ===== 1. PRIORIDAD MÁXIMA: precios_barrios.json =====
        resultado_barrios = obtener_tasacion_precios_barrios(barrio, tipo, estado, operacion)
        if resultado_barrios and not resultado_barrios.get("is_fallback"):
            valor = resultado_barrios['precio_m2'] * float(m2)
            return {
                "valor_estimado": round(valor, -2),
                "precio_m2": resultado_barrios['precio_m2'],
                "precio_usado_m2": resultado_barrios.get('precio_usado_m2'),
                "precio_nuevo_m2": resultado_barrios.get('precio_nuevo_m2'),
                "moneda": resultado_barrios.get('moneda', 'USD'),
                "is_fallback": False,
                "estado_aplicado": True,
                "fuentes": resultado_barrios.get("fuentes", []),
                "muestra": resultado_barrios.get("muestra", 0),
                "fuente": "Precios de Barrios (Análisis de Mercado)",
                "estado": resultado_barrios.get('estado')
            }
        
        # ===== 2. Backend IA externo =====
        data_ia = None
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
            log(f"📡 Backend IA no alcanzable, usando fallback local: {conn_err}")
        
        if data_ia and not data_ia.get("is_fallback"):
            return {
                "valor_estimado": data_ia.get("valor_estimado"),
                "precio_m2": data_ia.get("precio_m2_referencia"),
                "moneda": data_ia.get("moneda", "USD"),
                "is_fallback": False,
                "estado_aplicado": True,  # IA ya aplicó ajustes
                "fuentes": data_ia.get("fuentes", []),
                "muestra": data_ia.get("muestra_size", 0),
                "fuente": "Dante AI Valuation",
                "detalles": data_ia.get("detalles", {})
            }
        
        # ===== 3. Fallback: market_valuation_map.json o propiedades.json =====
        local_data = obtener_tasacion_local(barrio, tipo, estado, operacion)
        
        if local_data and not local_data.get("is_fallback"):
            ajustes = {"Excelente": 1.10, "Muy bueno": 1.05, "Bueno": 1.00, 
                       "Regular": 0.85, "A refaccionar": 0.70}
            factor = ajustes.get(estado, 1.0)
            valor = local_data['precio_m2'] * float(m2) * factor
            return {
                "valor_estimado": round(valor, -2),
                "precio_m2": local_data['precio_m2'],
                "moneda": local_data.get('moneda', 'USD'),
                "is_fallback": False,
                "estado_aplicado": True,
                "fuentes": local_data.get("fuentes", []),
                "muestra": local_data.get("muestra", 0),
                "fuente": "Mapa de Valoración Local"
            }
        
        # ===== 4. Último recurso: valor por defecto =====
        if not local_data:
            local_data = {
                "precio_m2": 2150.0 if operacion == 'venta' else 8500.0,
                "moneda": "USD" if operacion == 'venta' else "ARS",
                "is_fallback": True,
                "fuentes": [f"Promedio General CABA ({operacion.upper()})"],
                "muestra": 0
            }
        
        ajustes = {"Excelente": 1.10, "Muy bueno": 1.05, "Bueno": 1.00, 
                   "Regular": 0.85, "A refaccionar": 0.70}
        factor = ajustes.get(estado, 1.0)
        valor = local_data['precio_m2'] * float(m2) * factor
        
        return {
            "valor_estimado": round(valor, -2),
            "precio_m2": local_data['precio_m2'],
            "moneda": local_data.get('moneda', 'USD'),
            "is_fallback": local_data.get("is_fallback", True),
            "estado_aplicado": True,
            "fuentes": local_data.get("fuentes", []),
            "muestra": local_data.get("muestra", 0),
            "fuente": local_data.get("fuente", "Statistical Fallback")
        }
    except Exception as e:
        log(f"⚠️ Error crítico en obtención de tasación: {e}")
        import traceback
        log(traceback.format_exc())
        return None


def manejar_menu_tasacion(text_lower, estado_usuario, user_id):
    """Inicia el flujo de tasación preguntando Venta o Alquiler primero"""
    if 'data' not in estado_usuario or not isinstance(estado_usuario['data'], dict):
        estado_usuario['data'] = {}
    
    # Inicializar datos vacíos, sin forzar operación
    estado_usuario['data']['datos_tasacion'] = {}
    estado_usuario['paso'] = 'tasacion_operacion'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": "📈 *TASACIÓN VIRTUAL*\n\n¿Qué querés hacer con la propiedad?\n\n1️⃣ Vender\n2️⃣ Alquilar\n\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        return WhatsAppResponse.buttons(
            header="📈 Tasación Virtual",
            body="¿Qué querés hacer con la propiedad?",
            buttons=[
                {"id": "1", "title": "💰 Vender"},
                {"id": "2", "title": "🔑 Alquilar"}
            ],
            footer="Selecciona una opción 👇"
        )

def mostrar_lista_barrios(estado_usuario, user_id):
    """Muestra la lista de barrios con datos reales según la operación elegida"""
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    # Obtener la operación elegida
    operacion = estado_usuario.get('data', {}).get('datos_tasacion', {}).get('operacion', 'venta')
    
    # 🔑 Barrios DINÁMICOS desde precios_barrios.json
    barrios_lower = obtener_barrios_disponibles(operacion)
    
    if not barrios_lower:
        log(f"⚠️ No hay barrios en precios_barrios.json para operación '{operacion}'")
        if es_fb_ig:
            return {
                "type": "text",
                "body": f"⚠️ No hay datos de tasación disponibles para *{operacion}* en este momento.\n\n1️⃣ Volver al menú\n2️⃣ Salir",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                header="⚠️ Sin datos",
                body=f"No hay datos de tasación disponibles para *{operacion}* en este momento.",
                buttons=[
                    {"id": "m", "title": "Volver al menú"},
                    {"id": "s", "title": "Salir"}
                ]
            )
    
    # Convertir a display
    barrios_display = [capitalizar_barrio(b) for b in barrios_lower]
    
    if es_fb_ig:
        barrios_texto = ""
        for i, barrio in enumerate(barrios_display, 1):
            barrios_texto += f"{i}. {barrio}\n"
        return {
            "type": "text",
            "body": f"📍 *Seleccioná el barrio de tu propiedad:*\n\n{barrios_texto}\n💡 *Envía el número o el nombre del barrio*\n\n1️⃣ Volver al menú\n2️⃣ Salir",
            "preview": False
        }
    else:
        # WhatsApp: lista interactiva (máx 10 filas por sección)
        rows = [{"id": b, "title": capitalizar_barrio(b)} for b in barrios_lower[:10]]
        
        sections = [{
            "title": f"Barrios con datos ({len(barrios_lower)})",
            "rows": rows
        }]
        
        # Si hay más de 10, agregar una segunda sección
        if len(barrios_lower) > 10:
            sections.append({
                "title": "Más barrios",
                "rows": [{"id": b, "title": capitalizar_barrio(b)} for b in barrios_lower[10:20]]
            })
        
        return WhatsAppResponse.list_menu(
            header="📍 Selección de Barrio",
            body=f"*¿En qué barrio se encuentra tu propiedad?*\n\n_{len(barrios_lower)} barrios con datos disponibles para {operacion}_",
            button_text="Ver barrios",
            sections=sections,
            footer="Selecciona tu barrio 👇"
        )

def manejar_tasacion_operacion(text_lower, estado_usuario, user_id):
    """Guarda la operación y muestra la lista de barrios (con validación dinámica)"""
    ops = {"1": "venta", "2": "alquiler"}
    
    # Normalizar texto: aceptar "venta", "vender", "1", etc.
    text_norm = text_lower.strip().lower()
    if text_norm in ["venta", "vender"]:
        text_norm = "1"
    elif text_norm in ["alquiler", "alquilar"]:
        text_norm = "2"
    
    if text_norm in ops:
        operacion = ops[text_norm]
        
        # 🔑 VALIDACIÓN: ¿hay barrios con datos para esta operación?
        barrios = obtener_barrios_disponibles(operacion)
        
        if not barrios:
            # No hay datos → avisar al usuario y ofrecer la otra opción
            platform = estado_usuario.get('platform', 'whatsapp')
            es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
            
            otra_op = "alquiler" if operacion == "venta" else "venta"
            otra_barrios = obtener_barrios_disponibles(otra_op)
            
            if otra_barrios:
                msg = (
                    f"⚠️ *Sin datos de {operacion}*\n\n"
                    f"No tenemos datos de tasación para *{operacion}* en este momento.\n"
                    f"Pero sí tenemos para *{otra_op}*. ¿Qué querés hacer?"
                )
            else:
                msg = (
                    f"⚠️ *Sin datos disponibles*\n\n"
                    f"No tenemos datos de tasación cargados en este momento. "
                    f"Por favor intentá más tarde o contactá a un asesor."
                )
            
            if es_fb_ig:
                return {
                    "type": "text",
                    "body": f"{msg}\n\n1️⃣ Vender\n2️⃣ Alquilar\n\n💡 *Envía el número de la opción deseada*",
                    "preview": False
                }
            else:
                return WhatsAppResponse.buttons(
                    header="📈 Tasación Virtual",
                    body=msg,
                    buttons=[
                        {"id": "1", "title": "💰 Vender"},
                        {"id": "2", "title": "🔑 Alquilar"}
                    ],
                    footer="Selecciona una opción 👇"
                )
        
        # Guardar la operación elegida
        if 'data' not in estado_usuario or not isinstance(estado_usuario['data'], dict):
            estado_usuario['data'] = {}
        if 'datos_tasacion' not in estado_usuario['data']:
            estado_usuario['data']['datos_tasacion'] = {}
        
        estado_usuario['data']['datos_tasacion']['operacion'] = operacion
        estado_usuario['paso'] = 'tasacion_barrio_seleccion'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Mostrar lista dinámica de barrios (solo los que tienen datos)
        return mostrar_lista_barrios(estado_usuario, user_id)
    
    else:
        # Opción inválida → mostrar botones Vender/Alquilar de nuevo
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
        
        if es_fb_ig:
            return {
                "type": "text",
                "body": "⚠️ Opción no válida.\n\n📈 *¿Qué querés hacer con la propiedad?*\n\n1️⃣ Vender\n2️⃣ Alquilar\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.buttons(
                body="⚠️ Por favor, elegí una opción válida:",
                buttons=[
                    {"id": "1", "title": "💰 Vender"},
                    {"id": "2", "title": "🔑 Alquilar"}
                ],
                footer="Selecciona una opción 👇"
            )


def manejar_tasacion_barrio_seleccion(text, estado_usuario, user_id):
    """Maneja la selección de barrio desde la lista — solo barrios con datos"""
    text_stripped = text.strip()
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
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
    
    operacion = estado_usuario.get('data', {}).get('datos_tasacion', {}).get('operacion', 'venta')
    barrios_lower = obtener_barrios_disponibles(operacion)
    
    # Buscar barrio por número o nombre
    barrio_seleccionado = None
    
    if text_stripped.isdigit():
        idx = int(text_stripped) - 1
        if 0 <= idx < len(barrios_lower):
            barrio_seleccionado = barrios_lower[idx]
    
    if not barrio_seleccionado:
        for b in barrios_lower:
            if b.lower() == text_stripped.lower():
                barrio_seleccionado = b
                break
    
    if not barrio_seleccionado:
        for b in barrios_lower:
            if b.lower().startswith(text_stripped.lower()) or text_stripped.lower() in b.lower():
                barrio_seleccionado = b
                break
    
    if not barrio_seleccionado:
        # Barrio no válido o sin datos
        return WhatsAppResponse.buttons(
            body=f"⚠️ *{text_stripped}* no está entre los barrios con datos disponibles.\n\nPor favor, elegí uno de la lista o envía *'M'* para volver al menú.",
            buttons=botones_navegacion(),
            footer="Selecciona una opción 👇"
        )
    
    # 🔑 Tipos DINÁMICOS desde precios_barrios.json
    tipos_disponibles = obtener_tipos_disponibles(barrio_seleccionado, operacion)
    
    if not tipos_disponibles:
        # No debería pasar porque el barrio salió de la lista, pero por las dudas
        return WhatsAppResponse.buttons(
            body=f"⚠️ No hay tipos de propiedad con datos para *{capitalizar_barrio(barrio_seleccionado)}*.",
            buttons=botones_navegacion(),
            footer="Selecciona una opción 👇"
        )
    
    # Guardar barrio
    if 'datos_tasacion' not in estado_usuario['data']:
        estado_usuario['data']['datos_tasacion'] = {}
    estado_usuario['data']['datos_tasacion']['barrio'] = capitalizar_barrio(barrio_seleccionado)
    estado_usuario['data']['datos_tasacion']['tipos_disponibles'] = tipos_disponibles
    estado_usuario['paso'] = 'tasacion_tipo'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    # Mostrar tipos dinámicos
    if es_fb_ig:
        tipos_texto = ""
        for i, t in enumerate(tipos_disponibles, 1):
            tipos_texto += f"{i}. {capitalizar_tipo(t)}\n"
        return {
            "type": "text",
            "body": f"📍 Barrio seleccionado: *{capitalizar_barrio(barrio_seleccionado)}* ✅\n\n🏠 *¿Qué tipo de propiedad es?*\n\n{tipos_texto}\n💡 *Envía el número de la opción deseada*",
            "preview": False
        }
    else:
        rows = [
            {"id": t, "title": capitalizar_tipo(t)} 
            for t in tipos_disponibles
        ]
        return WhatsAppResponse.list_menu(
            body=f"📍 Barrio: *{capitalizar_barrio(barrio_seleccionado)}* ✅\n\n🏠 *¿Qué tipo de propiedad es?*",
            button_text="Ver tipos",
            sections=[{
                "title": "Tipos con datos disponibles",
                "rows": rows
            }],
            footer="Selecciona una opción 👇"
        )

def manejar_tasacion_tipo(text_lower, estado_usuario, user_id):
    """Guarda el tipo (validado contra precios_barrios.json) e inicia carga de m2"""
    platform = estado_usuario.get('platform', 'whatsapp')
    es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
    
    # Tipos disponibles guardados en el paso anterior
    tipos_disponibles = estado_usuario.get('data', {}).get('datos_tasacion', {}).get('tipos_disponibles', [])
    
    if not tipos_disponibles:
        log(f"⚠️ No hay tipos_disponibles en el estado — volviendo a barrio")
        estado_usuario['paso'] = 'tasacion_barrio_seleccion'
        actualizar_estado_usuario(user_id, estado_usuario)
        return mostrar_lista_barrios(estado_usuario, user_id)
    
    # Mapeo textual para aceptar "departamento" o "Departamento"
    text_norm = text_lower.strip().lower()
    
    tipo_seleccionado = None
    
    # 1. Por número (1, 2, 3, ...)
    if text_norm.isdigit():
        idx = int(text_norm) - 1
        if 0 <= idx < len(tipos_disponibles):
            tipo_seleccionado = tipos_disponibles[idx]
    
    # 2. Por nombre
    if not tipo_seleccionado:
        for t in tipos_disponibles:
            if t.lower() == text_norm:
                tipo_seleccionado = t
                break
    
    # 3. Coincidencia parcial
    if not tipo_seleccionado:
        for t in tipos_disponibles:
            if t.lower().startswith(text_norm) or text_norm in t.lower():
                tipo_seleccionado = t
                break
    
    if not tipo_seleccionado:
        # Tipo no válido
        if es_fb_ig:
            tipos_texto = "\n".join([f"{i}. {capitalizar_tipo(t)}" for i, t in enumerate(tipos_disponibles, 1)])
            return {
                "type": "text",
                "body": f"⚠️ Opción no válida.\n\n🏠 *¿Qué tipo de propiedad es?*\n\n{tipos_texto}\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            rows = [{"id": t, "title": capitalizar_tipo(t)} for t in tipos_disponibles]
            return WhatsAppResponse.list_menu(
                body="⚠️ Opción no válida.\n\n🏠 *¿Qué tipo de propiedad es?*",
                button_text="Ver tipos",
                sections=[{
                    "title": "Tipos con datos disponibles",
                    "rows": rows
                }],
                footer="Selecciona una opción 👇"
            )
    
    # Guardar tipo
    estado_usuario['data']['datos_tasacion']['tipo'] = capitalizar_tipo(tipo_seleccionado)
    estado_usuario['paso'] = 'tasacion_m2'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    cuerpo = "📏 *¿Cuántos m² cubiertos tiene la propiedad?*\n_(Ingresá solo el número, ej: 65)_"
    
    if es_fb_ig:
        return {
            "type": "text",
            "body": f"{cuerpo}\n\n1️⃣ Volver al menú\n2️⃣ Salir",
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
        detalles = f"Tasación solicitada: {datos['tipo']} en {datos['barrio']}, {datos['m2']}m2, {datos['ambientes']} amb, estado {datos['estado']}, operación {datos.get('operacion', 'venta')}."
        if tasacion:
            detalles += f" Resultado: {tasacion['valor_estimado']:,.0f} {tasacion['moneda']}"
            
        registrar_lead(user_id, "TASACION_VIRTUAL", "tasacion", detalles)
        notificar_agente(f"📈 *NUEVO LEAD DE TASACIÓN*\n📞 Tel: +{user_id}\n📝 {detalles}")
        
        # 3. Preparar intro
        operacion = datos.get('operacion', 'venta')
        verbo_operacion = "venta" if operacion == 'venta' else "alquiler"
        
        intro_mercado = f"Basado en el análisis estadístico de mercado para *{datos['barrio']}*:"
        if tasacion.get("is_fallback") and tasacion.get("muestra", 0) <= 1:
            intro_mercado = "Basado en el promedio general del mercado inmobiliario (estamos recolectando más datos específicos de tu zona):"
        
        # 4. Info de fuentes y muestra
        fuentes_str = ", ".join(tasacion.get("fuentes", ["Mercado Local"]))
        muestra = tasacion.get("muestra", 0)
        info_fuentes = f"🔍 *Análisis:* {muestra} propiedades en {fuentes_str}"
        
        # 5. Moneda y símbolo
        moneda = tasacion.get('moneda', 'USD')
        simbolo = "USD$" if moneda == 'USD' else "$"
        
        # 6. Formatear valores
        valor_estimado = tasacion.get('valor_estimado', 0)
        precio_m2_aplicado = tasacion.get('precio_m2', 0)
        precio_usado = tasacion.get('precio_usado_m2')
        precio_nuevo = tasacion.get('precio_nuevo_m2')
        
        # 7. Construir mensaje principal
        mensaje_body = f"""📊 *RESULTADO DE TU TASACIÓN VIRTUAL*

{intro_mercado}

🏠 *Propiedad:* {datos['tipo']} en {datos['barrio']}
📏 *Superficie:* {datos['m2']} m²
🏗️ *Estado:* {datos['estado']}
🎯 *Operación:* {verbo_operacion.title()}

━━━━━━━━━━━━━━━━━━━━
💰 *VALOR ESTIMADO:* {simbolo} {valor_estimado:,.0f}
📈 *Precio aplicado:* {simbolo} {precio_m2_aplicado:,.0f} / m²
━━━━━━━━━━━━━━━━━━━━"""
        
        # 8. Agregar referencia de precios usados/nuevos si están disponibles
        if precio_usado and precio_nuevo and precio_usado > 0 and precio_nuevo > 0:
            mensaje_body += f"""

📌 *Referencias del mercado:*
• Propiedades usadas: {simbolo} {precio_usado:,.0f} / m²
• Propiedades a estrenar: {simbolo} {precio_nuevo:,.0f} / m²"""
        
        mensaje_body += f"""

{info_fuentes}

⚠️ *Nota:* Esta es una estimación orientativa. Para una tasación profesional, un asesor debe visitar la propiedad.

¿Qué deseas hacer?"""
        
        estado_usuario['paso'] = 'tasacion_esperando_contacto'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Detectar plataforma
        platform = estado_usuario.get('platform', 'whatsapp')
        es_fb_ig = platform in ("messenger", "facebook", "instagram") if platform else False
        
        if es_fb_ig:
            return {
                "type": "text",
                "body": f"{mensaje_body}\n\n1️⃣ ✅ Deseas una Tasación profesional con visita\n2️⃣ ⏭️ No por ahora\n3️⃣ 🔙 Menú Principal\n4️⃣ ❌ Salir\n\n💡 *Envía el número de la opción deseada*",
                "preview": False
            }
        else:
            return WhatsAppResponse.list_menu(
                body=mensaje_body,
                button_text="Opciones",
                sections=[
                    {
                        "title": "Acciones",
                        "rows": [
                            {"id": "1", "title": "✅ Tasación profesional", "description": "Coordinar visita con asesor"},
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
        
