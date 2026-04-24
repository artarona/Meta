from utils import *
from database import *
from whatsapp_api import *
from tasaciones import *
from citas import *
from config import *
import time
import os
import json
from datetime import datetime
from database import *
from logic.response_builder import WhatsAppResponse
from logic.ai_prioritization import obtener_prioridad_lead

def manejar_menu_principal(text_lower, estado_usuario, user_id):
    """Maneja las opciones del menú principal"""
    if text_lower == "1":
        # INMUEBLES EN VENTA
        return procesar_opcion_venta(estado_usuario, user_id)
        
    elif text_lower == "2":
        # INMUEBLES EN ALQUILER
        return procesar_opcion_alquiler(estado_usuario, user_id)
        
    elif text_lower == "7":
        # TODOS LOS INMUEBLES
        return procesar_opcion_todas(estado_usuario, user_id)
        
    elif text_lower == "3":
        # Visitar sitio web
        return WhatsAppResponse.buttons(
            header="🌐 SITIO WEB OFICIAL",
            body="👉 https://www.dantepropiedades.com.ar\n\nVisitá nuestro sitio para ver todas las propiedades y novedades.",
            buttons=[
                {"id": "m", "title": "Volver al menú"},
                {"id": "s", "title": "Salir"}
            ]
        )

    elif text_lower == "4":
        # Ver mis citas
        return procesar_opcion_mis_citas(user_id)

    elif text_lower == "5":
        # Hablar con asesor
        estado_usuario['paso'] = 'submenu_asesor'
        actualizar_estado_usuario(user_id, estado_usuario)
        return WhatsAppResponse.buttons(
            body="¿Cómo querés comunicarte con un asesor?",
            header="👤 HABLAR CON UN ASESOR",
            buttons=[
                {"id": "asesor_mensaje", "title": "Enviar mensaje"},
                {"id": "asesor_llamada", "title": "Solicitar llamada"},
                {"id": "m", "title": "Volver al menú"}
            ]
        )

    elif text_lower == "6":
        # FAQs
        estado_usuario['paso'] = 'submenu_faqs'
        actualizar_estado_usuario(user_id, estado_usuario)
        return WhatsAppResponse.buttons(
            body="❓ *REQUISITOS Y PREGUNTAS FRECUENTES*\n\nElige una opción, o enviá 'M' para Menú / 'S' para Salir:",
            buttons=[
                {"id": "req_alquiler", "title": "Requisitos Alquiler"},
                {"id": "mascotas", "title": "¿Aceptan Mascotas?"},
                {"id": "permutas", "title": "¿Permutas?"}
            ]
        )

    elif text_lower == "m":
        # Volver al menú
        return "WELCOME_FLOW_TRIGGER"
        
    elif text_lower == "s":
        # Salir
        return "¡Gracias por confiar en Dante Propiedades! 🏠🗝️"

    elif text_lower == "8" and user_id == ADMIN_NUMBER.lstrip('549'):
        # Panel admin (solo para número autorizado)
        print("[ADMIN] Solicitud de panel admin")
        return mostrar_panel_admin()
    
    elif text_lower == "10":
        # TASACION VIRTUAL
        return manejar_menu_tasacion(text_lower, estado_usuario, user_id)
    
    else:
        return """No pude identificar esa opción. Por favor elegí un número del menú.

1️⃣ *Inmuebles en Venta* 🏠
2️⃣ *Inmuebles en Alquiler* 🔑
7️⃣ *Todos los Inmuebles* 🏢
3️⃣ *Visitar nuestro sitio web* 🌐
4️⃣ *Ver mis citas programadas* 📋
5️⃣ *Hablar con un asesor* 👤
6️⃣ *Requisitos y FAQs* ❓

Ⓜ️ *Envía 'M' para volver al menú principal*
❌ *Envía 'S' para salir del chat*"""


def manejar_submenu_consultar(text_lower, estado_usuario, user_id):
    """Maneja las opciones del submenú de consulta"""
    if text_lower == "1":
        return "🔎 *Búsqueda por código*\n\nPor favor, enviá el código de la propiedad (ej: UF002).\n\nⓂ️ Volver al menú principal\n❌ Salir (Envía 'S')"
    elif text_lower == "2":
        return "📍 *Búsqueda por zona*\n\n¿En qué zona estás buscando? (ej: Palermo, Belgrano, Tigre...)\n\nⓂ️ Volver al menú principal\n❌ Salir (Envía 'S')"
    elif text_lower == "3":
        return procesar_opcion_todas(estado_usuario, user_id)
    else:
        return """No pude identificar esa opción. Por favor elegí un número del menú.

Ⓜ️ *Envía 'M' para volver al menú principal*
❌ *Envía 'S' para salir del chat*"""


def manejar_submenu_visita(text_lower, estado_usuario, user_id):
    """Maneja las opciones del submenú de visitas"""
    if text_lower == "1":
        return procesar_opcion_todas(estado_usuario, user_id)
    elif text_lower == "2":
        return "📅 *Días y horarios disponibles*\n\nNuestros horarios generales son de Lunes a Viernes de 9 a 18:30 hs.\n\nⓂ️ Volver al menú principal\n❌ Salir (Envía 'S')"
    elif text_lower == "3":
        return "✅ *Confirmar visita*\n\nPara confirmar una visita, primero debemos seleccionar una propiedad. \n\n1️⃣ Ver propiedades\nⓂ️ Volver al menú principal\n❌ Salir (Envía 'S')"
    else:
        return """No pude identificar esa opción. Por favor elegí un número del menú.

Ⓜ️ *Envía 'M' para volver al menú principal*
❌ *Envía 'S' para salir del chat*"""


def manejar_submenu_asesor(text_lower, estado_usuario, user_id):
    """Maneja las opciones del submenú de asesor"""
    if text_lower in ["1", "asesor_mensaje", "enviar mensaje"]:
        notificar_agente(f"👤 *SOLICITUD DE ASESOR*\n📞 Tel: +{user_id}\n📝 El cliente desea enviar un mensaje.")
        return WhatsAppResponse.buttons(
            header="✅ MENSAJE ENVIADO",
            body="Un asesor se pondrá en contacto con vos a la brevedad.",
            buttons=[
                {"id": "m", "title": "Volver al menú"},
                {"id": "s", "title": "Salir"}
            ]
        )
    elif text_lower in ["2", "asesor_llamada", "solicitar llamada"]:
        notificar_agente(f"📞 *SOLICITUD DE LLAMADA*\n📞 Tel: +{user_id}\n📝 El cliente solicita ser llamado.")
        return WhatsAppResponse.buttons(
            header="📞 LLAMADA SOLICITADA",
            body=f"Te llamaremos en el horario más conveniente.\n\n📱 *Contacto directo:*\nwa.me/{AGENT_NUMBER.lstrip('+')}",
            buttons=[
                {"id": "m", "title": "Volver al menú"},
                {"id": "s", "title": "Salir"}
            ]
        )
    else:
        return WhatsAppResponse.buttons(
            header="👤 HABLAR CON UN ASESOR",
            body="¿Cómo querés comunicarte con un asesor?",
            buttons=[
                {"id": "asesor_mensaje", "title": "Enviar mensaje"},
                {"id": "asesor_llamada", "title": "Solicitar llamada"},
                {"id": "m", "title": "Volver al menú"}
            ]
        )


def manejar_submenu_faqs(text_lower, estado_usuario, user_id):
    """Maneja las opciones del submenú de FAQs"""

    BTNS_FAQS = [
        {"id": "faqs", "title": "Ver más FAQs"},
        {"id": "m", "title": "Volver al menú"},
        {"id": "s", "title": "Salir"}
    ]

    if text_lower in ["req_alquiler", "faqs"]:
        return WhatsAppResponse.buttons(
            header="📋 REQUISITOS ALQUILER",
            body="• Mes de adelanto\n• Mes de depósito (en USD)\n• Garantía propietaria (CABA/GBA) o Seguro de Caución (Finaer)\n• Demostración de ingresos (últimos 3 recibos)",
            buttons=BTNS_FAQS
        )
    elif text_lower == "mascotas":
        return WhatsAppResponse.buttons(
            header="🐾 ¿ACEPTAN MASCOTAS?",
            body="Depende estrictamente de la propiedad y el consorcio. Consultalo en el detalle de cada departamento.",
            buttons=BTNS_FAQS
        )
    elif text_lower == "permutas":
        return WhatsAppResponse.buttons(
            header="🔄 ¿PERMUTAS / PARTE DE PAGO?",
            body="Sí, evaluamos permutas caso por caso. Escribinos para tasación.",
            buttons=BTNS_FAQS
        )
    elif text_lower == "m":
        # Volver a FAQs
        estado_usuario['paso'] = 'submenu_faqs'
        actualizar_estado_usuario(user_id, estado_usuario)
        return WhatsAppResponse.buttons(
            header="❓ REQUISITOS Y PREGUNTAS FRECUENTES",
            body="Elegí el tema sobre el que querés informarte:",
            buttons=[
                {"id": "req_alquiler", "title": "Requisitos Alquiler"},
                {"id": "mascotas", "title": "¿Aceptan Mascotas?"},
                {"id": "permutas", "title": "¿Permutas?"}
            ]
        )
    elif text_lower == "s":
        return "¡Gracias por confiar en Dante Propiedades! 🏠🗝️"
    else:
        return WhatsAppResponse.buttons(
            header="❓ PREGUNTAS FRECUENTES",
            body="No pude identificar esa opción. ¿Sobre qué querés consultar?",
            buttons=[
                {"id": "req_alquiler", "title": "Requisitos Alquiler"},
                {"id": "mascotas", "title": "¿Aceptan Mascotas?"},
                {"id": "permutas", "title": "¿Permutas?"}
            ]
        )


def manejar_filtro_tipo(text_lower, estado_usuario, user_id):
    """Maneja el filtro de tipo de propiedad"""
    tipos = {
        "1": "departamento",
        "2": "casa",
        "3": "ph",
        "4": "oficina",
        "5": "terreno"
    }
    
    if text_lower in tipos:
        tipo_seleccionado = tipos[text_lower]
        estado_usuario['tipo_seleccionado'] = tipo_seleccionado
        estado_usuario['paso'] = 'filtro_ambientes'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Verificar rápido si hay propiedades antes de preguntar ambientes
        operacion = estado_usuario.get('operacion_seleccionada', '')
        todas = cargar_propiedades_cached()
        
        # Filtrado laxo temporal para chequear disponibilidad
        filtradas_temp = []
        for p in todas:
            if str(p.get('operacion', '')).lower() == operacion.lower():
                tipo_bd = str(p.get('tipo', '')).lower()
                if tipo_seleccionado == 'oficina' and 'oficina' in tipo_bd:
                    filtradas_temp.append(p)
                elif tipo_seleccionado == 'terreno' and ('terreno' in tipo_bd or 'lote' in tipo_bd):
                    filtradas_temp.append(p)
                elif tipo_seleccionado == tipo_bd or (tipo_seleccionado == 'departamento' and 'departam' in tipo_bd):
                    filtradas_temp.append(p)
                    
        if not filtradas_temp:
             estado_usuario['paso'] = 'listado_propiedades'
           # 🛡️ MANTENIMIENTO: Asegurar que propiedades_filtradas sea una lista
    # (Para evitar errores de 'NoneType' or 'str' if JSON parsed incorrectly)
             estado_usuario['propiedades_filtradas'] = []
             actualizar_estado_usuario(user_id, estado_usuario)
             return f"📭 Lo siento, no tenemos {tipo_seleccionado}s disponibles para {operacion} en este momento.\n\nⓂ️ *🔙 VOLVER AL MENÚ PRINCIPAL (Envía 'M')*\n❌ *SALIR (Envía 'S')*"

        return WhatsAppResponse.list_menu(
            body="🔢 *¿CUÁNTOS AMBIENTES?*\n\nPor favor, elegí la cantidad de ambientes:",
            button_text="Ambientes",
            sections=[
                {
                    "title": "Cantidad",
                    "rows": [
                        {"id": "1", "title": "1 Ambiente"},
                        {"id": "2", "title": "2 Ambientes"},
                        {"id": "3", "title": "3 Ambientes"},
                        {"id": "4", "title": "4 o más Ambientes"},
                        {"id": "5", "title": "Cualquiera"}
                    ]
                }
            ],
            footer="Selecciona una opción 👇"
        )
    else:
        return "⚠️ Por favor, elegí una opción válida o usá el menú."


def manejar_filtro_ambientes(text_lower, estado_usuario, user_id):
    """Maneja el filtro de cantidad de ambientes y muestra el resultado final"""
    ambientes_map = {
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4, # 4 o más
        "5": None # Cualquiera
    }
    
    if text_lower in ambientes_map:
        ambientes_sel = ambientes_map[text_lower]
        operacion = estado_usuario.get('operacion_seleccionada', '')
        tipo = estado_usuario.get('tipo_seleccionado', '')
        
        todas = cargar_propiedades_cached()
        propiedades_filtradas = []
        
        for p in todas:
            # 1. Filtro Operación
            if str(p.get('operacion', '')).lower() != operacion.lower():
                continue
            
            # 2. Filtro Tipo
            tipo_bd = str(p.get('tipo', '')).lower()
            if tipo == 'oficina' and 'oficina' not in tipo_bd:
                continue
            elif tipo == 'terreno' and 'terreno' not in tipo_bd and 'lote' not in tipo_bd:
                continue
            elif tipo in ['departamento', 'casa', 'ph']:
                if tipo == 'departamento' and 'departam' not in tipo_bd:
                    continue
                elif tipo != 'departamento' and tipo != tipo_bd:
                    continue
            
            # 3. Filtro Ambientes
            if ambientes_sel is not None:
                try:
                    amb_bd = int(p.get('ambientes', 0))
                except:
                    amb_bd = 0
                    
                if ambientes_sel == 4 and amb_bd < 4:
                    continue
                elif ambientes_sel != 4 and amb_bd != ambientes_sel:
                    continue
                    
            propiedades_filtradas.append(p)
            
    estado_usuario.update({
            'paso': 'listado_propiedades',
            'ambientes_seleccionados': ambientes_sel,
            'propiedades_filtradas': propiedades_filtradas,
            'ultima_accion': 'mostrar_listado'
        })
    actualizar_estado_usuario(user_id, estado_usuario)
        
        # 👇 AGREGÁ ESTE PRINT AQUÍ 👇
    log(f"[DEBUG] FILTRO AMBIENTES - Propiedades encontradas: {len(propiedades_filtradas)}")
        
    if not propiedades_filtradas:
        # OPTIMIZACIÓN: Si no hay resultados exactos por ambientes, ofrecer ver todas del mismo tipo
        estado_usuario.update({
            'paso': 'listado_propiedades',
            'ambientes_seleccionados': None,
            'propiedades_filtradas': [p for p in todas if str(p.get('operacion', '')).lower() == operacion.lower() and tipo in str(p.get('tipo', '')).lower()],
            'ultima_accion': 'mostrar_listado'
        })
        actualizar_estado_usuario(user_id, estado_usuario)
            
        texto = f"📭 No encontramos {tipo}s de {ambientes_sel} ambientes en {operacion}.\n\n🔍 *Pero tenemos otras opciones de {tipo} que te pueden interesar:* \n\n" + generar_listado_propiedades(estado_usuario['propiedades_filtradas'])
        return [texto, _nav_listado_buttons()]
    
    else:
         return "⚠️ Por favor, elegí una opción válida (1 al 5) o enviá 'M' para volver al menú."



def restaurar_listado_si_es_necesario(estado_usuario):
    # Si no hay propiedades pero hay contexto, reconstruye la lista
    if not estado_usuario.get('propiedades_filtradas') and estado_usuario.get('ultimo_contexto'):
        contexto = estado_usuario['ultimo_contexto']
        if contexto['tipo'] == 'venta':
            nuevas_props = [p for p in cargar_propiedades_cached() if p.get('operacion') == 'venta']
            estado_usuario['propiedades_filtradas'] = nuevas_props
            return nuevas_props
    return estado_usuario.get('propiedades_filtradas', [])


def _nav_listado_buttons():
    """Botones de navegación estándares para el listado de propiedades (Opción A)."""
    return WhatsAppResponse.buttons(
        # header="📍 NAVEGAR",
        # body="¿Qué querés hacer?",
        header="📍Selecciona la propiedad",
        body="o selecciona 👇",
        buttons=[
            {"id": "m", "title": "Volver al menú"},
            {"id": "s", "title": "Salir"}
        ]
    )


def procesar_opcion_venta(estado_usuario, user_id):
    """Procesa la opción de venta listando todas directamente"""
    todas = cargar_propiedades_cached()
    filtradas = [p for p in todas if str(p.get('operacion', '')).lower() == 'venta']
    
    # 👇 AGREGÁ ESTE PRINT AQUÍ 👇
    log(f"[DEBUG] VENTA - Total propiedades filtradas: {len(filtradas)}")
    
    estado_usuario.update({
        'paso': 'listado_propiedades',
        'operacion_seleccionada': 'venta',
        'propiedades_filtradas': filtradas,
        'ultima_accion': 'mostrar_listado'
    })

    
    actualizar_estado_usuario(user_id, estado_usuario)
    
    if not filtradas:
        return WhatsAppResponse.buttons(
            header="📭 SIN PROPIEDADES EN VENTA",
            body="Actualmente no tenemos propiedades en venta. Probá con otra categoría.",
            buttons=[
                {"id": "opcion_2", "title": "Ver Alquileres"},
                {"id": "m", "title": "Volver al menú"}
            ]
        )
    
    texto = "💰 *INMUEBLES EN VENTA*\n\n" + generar_listado_propiedades(filtradas)
    return [texto, _nav_listado_buttons()]


def procesar_opcion_alquiler(estado_usuario, user_id):
    """Procesa la opción de alquiler listando todas directamente"""
    todas = cargar_propiedades_cached()
    filtradas = [p for p in todas if str(p.get('operacion', '')).lower() == 'alquiler']
    
    # 👇 AGREGÁ ESTE PRINT AQUÍ 👇
    log(f"[DEBUG] ALQUILER - Total propiedades filtradas: {len(filtradas)}")
    
    estado_usuario.update({
        'paso': 'listado_propiedades',
        'operacion_seleccionada': 'alquiler',
        'propiedades_filtradas': filtradas,
        'ultima_accion': 'mostrar_listado'
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    
    if not filtradas:
        return WhatsAppResponse.buttons(
            header="📭 SIN PROPIEDADES EN ALQUILER",
            body="Actualmente no tenemos propiedades en alquiler. Probá con otra categoría.",
            buttons=[
                {"id": "opcion_1", "title": "Ver Ventas"},
                {"id": "m", "title": "Volver al menú"}
            ]
        )
    
    texto = "🔑 *INMUEBLES EN ALQUILER*\n\n" + generar_listado_propiedades(filtradas)
    return [texto, _nav_listado_buttons()]


def procesar_opcion_todas(estado_usuario, user_id):
    """Procesa la opción de ver todas las propiedades"""
    estado_usuario.update({
        'paso': 'listado_propiedades',
        'operacion_seleccionada': 'todas',
        'propiedades_filtradas': cargar_propiedades_cached(),
        'ultima_accion': 'mostrar_listado'
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    texto = "📋 *TODAS LAS PROPIEDADES*\n\n" + generar_listado_propiedades(estado_usuario['propiedades_filtradas'])
    return [texto, _nav_listado_buttons()]


def procesar_opcion_mis_citas(user_id):
    """Procesa la opción de ver mis citas consultando DB y JSON con normalización"""
    # 1. Intentar obtener de PostgreSQL (fuente primaria)
    citas_usuario = obtener_todas_citas_usuario(user_id)
    
    # 2. Si no hay en DB, buscar en JSON con normalización de números
    if not citas_usuario:
        citas_json = cargar_citas()
        if citas_json:
            citas_usuario = [
                c for c in citas_json 
                if (son_numeros_identicos(c.get('telefono'), user_id) or son_numeros_identicos(c.get('user_id'), user_id))
                and c.get('estado', '').lower() != 'cancelada'
                and c.get('estado', '').lower() != 'finalizada'
            ]
    
    if not citas_usuario:
        return WhatsAppResponse.buttons(
            header="📅 SIN CITAS AGENDADAS",
            body="Para agendar una cita, seleccioná una propiedad del catálogo y presiona *'Me interesa'* (letra I).",
            buttons=[
                {"id": "opcion_7", "title": "Ver propiedades"},
                {"id": "m", "title": "Volver al menú"}
            ]
        )
    
    estado_usuario = obtener_estado_usuario(user_id)
    
    # 🔥 SI HAY SOLO 1 CITA, ENTRAR DIRECTAMENTE A MODIFICAR
    if len(citas_usuario) == 1:
        # Guardar la cita seleccionada y pasar a opciones
        cita_seleccionada = citas_usuario[0]
        log(f"🔍 DEBUG CITA: {cita_seleccionada}")  # 👈 Agregar este log
        # Obtener información de la propiedad
        todas_propiedades = cargar_propiedades_cached()
        props_dict = {p.get('id_temporal', ''): p for p in todas_propiedades}
        propiedad_id_cita = cita_seleccionada.get('propiedad_id', '')
        propiedad = props_dict.get(propiedad_id_cita, {})
        titulo = propiedad.get('titulo', propiedad_id_cita if propiedad_id_cita else 'Propiedad N/A')
        
        # Guardar en estado
        cita_seleccionada['propiedad_titulo'] = titulo
        estado_usuario['cita_seleccionada_modificar'] = cita_seleccionada
        estado_usuario['paso'] = 'opciones_modificar_cita'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        # Formatear la información de la cita
        try:
            fecha_obj = datetime.strptime(cita_seleccionada.get('fecha', ''), "%Y-%m-%d")
            fecha_formateada = fecha_obj.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            fecha_formateada = cita_seleccionada.get('fecha', 'Sin fecha')
        
        # Mostrar solo los botones de Meta sin duplicar opciones de texto
        nav_buttons = WhatsAppResponse.buttons(
            header=f"🔧 CITA: {titulo}",
            body=f"📅 {fecha_formateada} - ⏰ {cita_seleccionada.get('hora', 'Sin hora')} hs\n\n¿Qué deseás hacer?",
            buttons=[
                {"id": "opcion_cambiar_fecha", "title": "Cambiar fecha/hora"},
                {"id": "opcion_cancelar_cita", "title": "Cancelar cita"},
                {"id": "m", "title": "Volver"}
            ]
        )
        
        return nav_buttons
    
    # Si hay 2 o más citas, mostrar lista para elegir
    estado_usuario['citas_para_modificar'] = citas_usuario
    estado_usuario['paso'] = 'seleccionar_cita_modificar'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    mensaje = f"📅 *TUS CITAS AGENDADAS*\n\nTienes *{len(citas_usuario)}* cita(s) activa(s):\n\n"
    
    # Cargar todas las propiedades para poder buscar por ID
    todas_propiedades = cargar_propiedades_cached()
    # Crear un diccionario para búsqueda rápida por id_temporal
    props_dict = {p.get('id_temporal', ''): p for p in todas_propiedades}
    
    for i, cita in enumerate(citas_usuario, 1):
        try:
            fecha_obj = datetime.strptime(cita.get('fecha', ''), "%Y-%m-%d")
            fecha_formateada = fecha_obj.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            fecha_formateada = cita.get('fecha', 'Sin fecha')
        
        # 🔧 CORREGIDO: Obtener la propiedad usando el propiedad_id de la cita
        propiedad_id_cita = cita.get('propiedad_id', '')
        propiedad = props_dict.get(propiedad_id_cita, {})
        titulo = propiedad.get('titulo', propiedad_id_cita if propiedad_id_cita else 'Propiedad N/A')
        
        mensaje += f"{i}. *{titulo}*\n"
        mensaje += f"   📅 {fecha_formateada} - ⏰ {cita.get('hora', 'Sin hora')}\n"
        mensaje += f"   📍 Estado: {cita.get('estado', 'Pendiente').upper()}\n"
        
        if cita.get('notas') and cita['notas'] not in ('Sin notas', 'Sin notas adicionales', ''):
            mensaje += f"   📝 Notas: {cita['notas'][:50]}...\n"
        
        mensaje += "   ───────────────\n"
    
    # Opción A: enviar texto rico + botones como 2 mensajes
    nav_buttons = WhatsAppResponse.buttons(
        header="📅 TUS CITAS",
        body="¿Qué deseás hacer? Escribí el número de la cita para modificarla (ej: '1', '2', etc.)",
        buttons=[
            {"id": "opcion_modificar_cita", "title": "Modificar cita"},
            {"id": "m", "title": "Volver al menú"},
            {"id": "s", "title": "Salir"}
        ]
    )
    return nav_buttons

def manejar_seleccion_cita_modificar(text_lower, user_id):
    """Maneja la selección de una cita para modificarla desde el menú de citas"""

    # Manejar navegación
    if text_lower in ["m", "volver"]:
        estado_usuario = obtener_estado_usuario(user_id)
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['cita_seleccionada_modificar'] = None
        estado_usuario['citas_para_modificar'] = []
        actualizar_estado_usuario(user_id, estado_usuario)
        return "WELCOME_FLOW_TRIGGER"
    
    if text_lower in ["s", "salir"]:
        return "¡Gracias por confiar en Dante Propiedades! 🏠🗝️"
    
    # Validar número
    try:
        numero_cita = int(text_lower)
    except ValueError:
        return "❌ *Entrada inválida*. Escribí el número de la cita.\n\nⓂ️ *VOLVER AL MENÚ* (Envía 'M')"
    
    # Obtener citas
    estado_usuario = obtener_estado_usuario(user_id)
    citas_usuario = estado_usuario.get('citas_para_modificar', [])

    if not citas_usuario:
        citas_usuario = obtener_todas_citas_usuario(user_id)
        if not citas_usuario:
            citas_json = cargar_citas()
            if citas_json:
                citas_usuario = [
                    c for c in citas_json 
                    if (son_numeros_identicos(c.get('telefono'), user_id) or son_numeros_identicos(c.get('user_id'), user_id))
                    and c.get('estado', '').lower() not in ['cancelada', 'finalizada']
                ]
    
    # Validar rango
    if numero_cita < 1 or numero_cita > len(citas_usuario):
        return f"❌ *Número inválido*. Seleccioná entre 1 y {len(citas_usuario)}.\n\nⓂ️ *VOLVER AL MENÚ* (Envía 'M')"
    
    # Seleccionar cita
    cita_seleccionada = citas_usuario[numero_cita - 1]
    estado_usuario['cita_seleccionada_modificar'] = cita_seleccionada
    estado_usuario['paso'] = 'opciones_modificar_cita'
    actualizar_estado_usuario(user_id, estado_usuario)

    # Botones (único menú)
    nav_buttons = WhatsAppResponse.buttons(
        header="🔧 MODIFICAR CITA",
        body="Seleccioná qué acción deseás realizar con esta cita.",
        buttons=[
            {"id": "opcion_cambiar_fecha", "title": "Cambiar fecha/hora"},
            {"id": "opcion_cancelar_cita", "title": "Cancelar cita"},
            {"id": "m", "title": "Volver"}
        ]
    )

    return nav_buttons



def manejar_opciones_modificar_cita(text_lower, estado_usuario, user_id):
    """Maneja las opciones de modificación de una cita seleccionada"""
    cita_seleccionada = estado_usuario.get('cita_seleccionada_modificar', {})
    
    text_lower = text_lower.lower().strip()
    
    # 👇 RECONOCER EL ID EXACTO DEL BOTÓN
    if text_lower in ["opcion_cambiar_fecha", "1", "cambiar fecha", "cambiar fecha/hora", "modificar fecha"]:
        # Opción: Cambiar fecha/hora
        log(f"🔄 Usuario {user_id} solicita cambiar fecha de cita")
        
        # Preparar el estado para solicitar nueva fecha
        estado_usuario['paso'] = 'solicitar_fecha_actualizacion_cita'
        estado_usuario['cita_id_a_modificar'] = cita_seleccionada.get('id')
        actualizar_estado_usuario(user_id, estado_usuario)
        
        return "🔄 *Perfecto! Vamos a cambiar la fecha de tu visita.*\n\n📅 Enviá la nueva fecha que prefieras (ej: 'mañana 10am', 'jueves 14:30'):"
    
    # 👇 RECONOCER EL ID EXACTO DEL BOTÓN
    elif text_lower in ["opcion_cancelar_cita", "2", "cancelar cita", "cancelar", "anular"]:
        # Opción: Cancelar cita
        log(f"❌ Usuario {user_id} solicita cancelar cita")
        
        cita_id = cita_seleccionada.get('id')
        try:
            actualizar_cita_db(cita_id, nuevo_estado='cancelada')
            log(f"✅ Cita {cita_id} cancelada exitosamente")
            
            guardar_en_postgresql(
                telefono=user_id,
                nombre=estado_usuario.get('nombre_cliente', 'Cliente'),
                accion="cita_cancelada",
                detalles=f"Cita {cita_id} cancelada por el usuario desde 'Modificar cita'"
            )
            
            try:
                titulo_propiedad = cita_seleccionada.get('propiedad_titulo', 'Propiedad N/A')
                fecha_cita = cita_seleccionada.get('fecha', 'Sin fecha')
                hora_cita = cita_seleccionada.get('hora', 'Sin hora')
                notificar_agente(f"❌ *CITA CANCELADA*\n👤 {estado_usuario.get('nombre_cliente', 'Cliente')}\n📞 +{user_id}\n🏠 {titulo_propiedad}\n📅 {fecha_cita} {hora_cita}")
            except:
                pass
            
            estado_usuario['paso'] = 'menu_principal'
            estado_usuario['cita_seleccionada_modificar'] = None
            estado_usuario['citas_para_modificar'] = []
            actualizar_estado_usuario(user_id, estado_usuario)
            
            return WhatsAppResponse.buttons(
                header="✅ CITA CANCELADA",
                body="Tu cita ha sido cancelada exitosamente. Si en otro momento deseas agendar una visita, podés volver a empezar desde el catálogo.",
                buttons=[
                    {"id": "opcion_7", "title": "Ver propiedades"},
                    {"id": "m", "title": "Volver al menú"},
                    {"id": "s", "title": "Salir"}
                ]
            )
        except Exception as e:
            log(f"❌ Error cancelando cita: {e}")
            return "❌ *Error al cancelar la cita*\n\nPor favor, intentá nuevamente o contactá a un asesor.\n\nⓜ️ *VOLVER AL MENÚ* (Envía 'M')"
    
    elif text_lower in ["m", "volver"]:
        # Volver a la lista de citas
        log(f"↩️ Usuario {user_id} volviendo a lista de citas")
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['cita_seleccionada_modificar'] = None
        actualizar_estado_usuario(user_id, estado_usuario)
        
        return procesar_opcion_mis_citas(user_id)
    
    else:
        # Solo llegar acá si realmente no se reconoce nada
        return """❌ *Operación no reconocida.*

Por favor elegí una de las siguientes opciones:

1️⃣ *Cambiar fecha/hora* 📅
2️⃣ *Cancelar cita* ❌
Ⓜ️ *Volver* (Envía 'M')
"""


def manejar_solicitar_fecha_actualizacion_cita(text_lower, estado_usuario, user_id):
    """Maneja la solicitud de nueva fecha para actualizar una cita existente"""
    
    if text_lower in ["ver fechas", "disponibles", "fechas"]:
        return mostrar_fechas_disponibles(estado_usuario)
    
    # 1. Analizar Fecha
    fecha_ingresada = analizar_fecha(text_lower)
    
    if not fecha_ingresada:
        return """❌ *No entendí la fecha*
Por favor, probá con:
✅ "Mañana a las 10"
✅ "El jueves por la tarde"
✅ "25-10-2026"

1️⃣ *Ver fechas* (Ver disponibilidad)
Ⓜ️ *Volver* (Ir al menú - Envía 'M')"""

    # Validaciones de fecha
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if fecha_ingresada < hoy and fecha_ingresada.date() != hoy.date():
        return "❌ *Fecha pasada*\nPor favor elige una fecha futura."
    
    # 2. Analizar Hora (si el usuario la incluyó)
    hora_ingresada = analizar_hora(text_lower)
    
    fecha_str = fecha_ingresada.strftime("%Y-%m-%d")
    fecha_display = fecha_ingresada.strftime("%d-%m-%Y")
    
    # Obtener ID de la propiedad de la cita a modificar
    cita_seleccionada = estado_usuario.get('cita_seleccionada_modificar', {})
    propiedad_id = cita_seleccionada.get('propiedad_id')
        
    horarios_disponibles = obtener_horarios_disponibles(fecha_str, propiedad_id)
    
    if not horarios_disponibles:
        return f"""❌ *Sin disponibilidad*
No hay horarios para el {fecha_display}.

1️⃣ *Ver fechas* (Elegir otro día)
Ⓜ️ *Volver* (Ir al menú - Envía 'M')"""

    # 👇 IMPORTANTE: Guardar la fecha en MÚLTIPLES lugares
    estado_usuario['fecha_cita_actualizacion'] = fecha_str
    
    # También guardar en la cita seleccionada para respaldo
    if 'cita_seleccionada_modificar' in estado_usuario:
        estado_usuario['cita_seleccionada_modificar']['nueva_fecha'] = fecha_str
    
    # CASO A: Usuario indicó fecha Y hora ("mañana a las 10")
    if hora_ingresada:
        if hora_ingresada in horarios_disponibles:
            # Hora válida -> Confirmar la actualización
            estado_usuario['hora_cita_actualizacion'] = hora_ingresada
            estado_usuario['paso'] = 'confirmar_actualizacion_cita'
            actualizar_estado_usuario(user_id, estado_usuario)
            
            return f"""✅ *NUEVA FECHA SELECCIONADA*

📅 *Fecha:* {fecha_display}
⏰ *Hora:* {hora_ingresada} hs

¿Confirmás este cambio?

1️⃣ *SÍ, CAMBIAR* ✅
2️⃣ *NO, ELEGIR OTRA FECHA* 🔄
Ⓜ️ *CANCELAR* (Envía 'M')
"""
        else:
            # Hora inválida o ocupada
            return f"""❌ *Horario no disponible*
El horario {hora_ingresada} no está disponible para el {fecha_display}.

⏰ *Horarios libres:*
{", ".join(horarios_disponibles)}

Por favor, escribí uno de los horarios disponibles."""

    # CASO B: Solicitó solo fecha -> Pedir hora
    estado_usuario['paso'] = 'seleccionar_hora_actualizacion_cita'
    estado_usuario['horarios_disponibles'] = horarios_disponibles
    actualizar_estado_usuario(user_id, estado_usuario)
    
    return mostrar_seleccion_horarios(fecha_display, horarios_disponibles)


def manejar_seleccionar_hora_actualizacion_cita(text, estado_usuario, user_id):
    """Maneja la selección de hora para actualizar una cita"""
    
    text_lower = text.lower().strip()
    
    # Opción para volver
    if text_lower in ["m", "volver", "atrás"]:
        estado_usuario['paso'] = 'opciones_modificar_cita'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "↩️ *Volviendo a opciones de cita..."
    
    # Intentar analizar la hora del texto
    hora_ingresada = analizar_hora(text_lower)
    
    if not hora_ingresada:
        # Si no encuentra una hora, intenta buscar en las opciones numeradas
        try:
            opcion = int(text_lower)
            horarios_disponibles = estado_usuario.get('horarios_disponibles', [])
            if 1 <= opcion <= len(horarios_disponibles):
                hora_ingresada = horarios_disponibles[opcion - 1]
            else:
                return f"❌ *Opción inválida*. Por favor, seleccioná entre 1 y {len(horarios_disponibles)}."
        except ValueError:
            horarios = estado_usuario.get('horarios_disponibles', [])
            return f"""❌ *No entendí esa hora*

Por favor, escribí la hora en formato HH:MM (ej: 14:30) o seleccioná una opción:

{", ".join(horarios)}"""
    
    # 👇 CORREGIDO: Obtener la fecha DIRECTAMENTE de la cita seleccionada
    cita_seleccionada = estado_usuario.get('cita_seleccionada_modificar', {})
    fecha_str = cita_seleccionada.get('fecha', '')
    
    log(f"🔍 DEBUG: fecha_str obtenida de cita_seleccionada_modificar: '{fecha_str}'")
    
    # Si no tiene fecha, es un error grave
    if not fecha_str:
        log(f"❌ ERROR: La cita seleccionada no tiene fecha")
        estado_usuario['paso'] = 'opciones_modificar_cita'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "❌ *Error interno*: No se encontró la fecha de la cita. Por favor, intentá nuevamente desde el menú de modificación."
    
    try:
        fecha_display = datetime.strptime(fecha_str, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception as e:
        log(f"❌ Error parseando fecha '{fecha_str}': {e}")
        fecha_display = fecha_str
    
    # Guardar la hora (pero NO la fecha, ya la tenemos en la cita)
    estado_usuario['hora_cita_actualizacion'] = hora_ingresada
    estado_usuario['paso'] = 'confirmar_actualizacion_cita'
    actualizar_estado_usuario(user_id, estado_usuario)
    
    return f"""✅ *NUEVA FECHA SELECCIONADA*

📅 *Fecha:* {fecha_display}
⏰ *Hora:* {hora_ingresada} hs

¿Confirmás este cambio?

1️⃣ *SÍ, CAMBIAR* ✅
2️⃣ *NO, ELEGIR OTRA FECHA* 🔄
Ⓜ️ *CANCELAR* (Envía 'M')
"""

def manejar_confirmar_actualizacion_cita(text_lower, estado_usuario, user_id):
    """Confirma la actualización de una cita existente"""
    
    if text_lower in ["1", "si", "sí", "cambiar", "confirmar"]:
        # Confirmar cambio
        cita_id = estado_usuario.get('cita_id_a_modificar')
        nueva_fecha = estado_usuario.get('fecha_cita_actualizacion')
        nueva_hora = estado_usuario.get('hora_cita_actualizacion')
        
        try:
            # Usar la función única para actualizar la cita
            actualizar_cita_db(cita_id, nueva_fecha=nueva_fecha, nueva_hora=nueva_hora)
            
            log(f"✅ Cita {cita_id} actualizada: {nueva_fecha} {nueva_hora}")
            
            # Notificar al agente
            try:
                cita_seleccionada = estado_usuario.get('cita_seleccionada_modificar', {})
                titulo_propiedad = cita_seleccionada.get('propiedad_titulo', 'Propiedad N/A')
                fecha_formateada = datetime.strptime(nueva_fecha, "%Y-%m-%d").strftime("%d/%m/%Y")
                notificar_agente(f"🔄 *CITA ACTUALIZADA*\n👤 {estado_usuario.get('nombre_cliente', 'Cliente')}\n📞 +{user_id}\n🏠 {titulo_propiedad}\n📅 Nueva fecha: {fecha_formateada} a las {nueva_hora} hs")
            except:
                pass
            
            # Resetear estado
            estado_usuario['paso'] = 'menu_principal'
            estado_usuario['cita_seleccionada_modificar'] = None
            estado_usuario['citas_para_modificar'] = []
            estado_usuario['fecha_cita_actualizacion'] = None
            estado_usuario['hora_cita_actualizacion'] = None
            actualizar_estado_usuario(user_id, estado_usuario)
            
            fecha_formateada = datetime.strptime(nueva_fecha, "%Y-%m-%d").strftime("%d/%m/%Y")
            
            return WhatsAppResponse.buttons(
                header="✅ CITA ACTUALIZADA",
                body=f"Tu cita ha sido actualizada exitosamente para el {fecha_formateada} a las {nueva_hora} hs.",
                buttons=[
                    {"id": "opcion_4", "title": "Ver mis citas"},
                    {"id": "m", "title": "Volver al menú"},
                    {"id": "s", "title": "Salir"}
                ]
            )
        except Exception as e:
            log(f"❌ Error actualizando cita: {e}")
            return "❌ *Error al actualizar la cita*\n\nPor favor, intentá nuevamente o contactá a un asesor.\n\nⓜ️ *VOLVER AL MENÚ* (Envía 'M')"
    
    elif text_lower in ["2", "no", "elegir", "otra"]:
        # Volver a elegir fecha
        estado_usuario['paso'] = 'solicitar_fecha_actualizacion_cita'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "🔄 *Perfecto! Enviá una nueva fecha para tu cita*\n\n📅 (ej: 'mañana 10am', 'jueves 14:30'):"
    
    elif text_lower in ["m", "cancelar", "volver"]:
        # Cancelar la actualización
        estado_usuario['paso'] = 'opciones_modificar_cita'
        estado_usuario['fecha_cita_actualizacion'] = None
        estado_usuario['hora_cita_actualizacion'] = None
        actualizar_estado_usuario(user_id, estado_usuario)
        
        return """❌ *Actualización cancelada*

¿Qué deseás hacer?

1️⃣ *Modificar fecha/hora* 📅
2️⃣ *Cancelar cita* ❌
3️⃣ *Ver detalles* 📋
Ⓜ️ *Volver* (Envía 'M')
"""
    
    else:
        return """❌ *Opción no válida*

Por favor elegí una de las siguientes opciones:

1️⃣ *SÍ, CAMBIAR* ✅
2️⃣ *NO, ELEGIR OTRA FECHA* 🔄
Ⓜ️ *CANCELAR* (Envía 'M')
"""


def devolver_detalle_propiedad_menu(propiedad):
    """Devuelve el detalle de propiedad con menú de lista interactivo optimizado"""
    # Generar el cuerpo con la información de la propiedad (sin los botones al final)
    titulo = propiedad.get('titulo', 'Propiedad Destacada').strip()
    operacion = propiedad.get('operacion', '')
    
    # Crear resumen compacto para el body del menú
    barrio = propiedad.get('barrio', '')
    precio = propiedad.get('precio', 0)
    moneda = propiedad.get('moneda_precio', 'USD')
    simbolo = "USD$" if moneda == 'USD' else "$"
    expensas = propiedad.get('expensas', 0)
    ambientes = propiedad.get('ambientes', 0)
    m2 = propiedad.get('metros_cuadrados', 0)
    
    # Body más compacto para el menú de lista
    body = f"""✨ *{titulo}* ✨

📍 {barrio}
💵 {simbolo} {precio:,.0f}"""
    
    if expensas > 0:
        moneda_exp = propiedad.get('moneda_expensas', 'ARS')
        simb_exp = "USD$" if moneda_exp == 'USD' else "$"
        body += f" | 🏢 {simb_exp} {expensas:,.0f}"
    
    body += f"\n📐 {ambientes} amb. en {m2} m²"
    
    # Amenities
    amenities = []
    if str(propiedad.get('balcon', 'No')).lower() in ['si', 'sí', '1', 'true', 'x']:
        amenities.append("🌆 Balcón")
    if str(propiedad.get('cochera', 'No')).lower() in ['si', 'sí', '1', 'true', 'x']:
        amenities.append("🚗 Cochera")
    if str(propiedad.get('acepta_mascotas', 'No')).lower() in ['si', 'sí', '1', 'true']:
        amenities.append("🐾 Pet Friendly")
    if str(propiedad.get('pileta', 'No')).lower() in ['si', 'sí', '1', 'true']:
        amenities.append("🏊 Pileta")
    if str(propiedad.get('aire_acondicionado', 'No')).lower() in ['si', 'sí', '1', 'true']:
        amenities.append("❄️ Aire")
        
    if amenities:
        body += f"\n⭐ {' • '.join(amenities)}"
    
    body += "\n\n¿Qué deseas hacer?"
    
    # Crear las secciones del menú
    sections = [
        {
            "title": "Ver Información",
            "rows": [
                {"id": "ver_fotos", "title": "📷 Ver Fotos", "description": "Galería de imágenes"},
                {"id": "ver_pdf", "title": "📄 Ver Ficha Técnica", "description": "Descargar PDF completo"},
            ]
        },
        {
            "title": "Acciones",
            "rows": [
                {"id": "me_interesa", "title": "👁️ Me Interesa", "description": "Agendar visita"},
                {"id": "requisitos", "title": "📋 Ver Requisitos", "description": "Condiciones de ingreso"},
            ]
        },
        {
            "title": "Navegación",
            "rows": [
                {"id": "ver_listado", "title": "📋 Más Propiedades", "description": "Ver otras opciones"},
                {"id": "m", "title": "Ⓜ️ Menú Principal", "description": "Ir al inicio"},
                {"id": "s", "title": "❌ Salir", "description": "Terminar sesión"}
            ]
        }
    ]
    
    return WhatsAppResponse.list_menu(
        body=body,
        button_text="Opciones",
        sections=sections,
        footer="Selecciona una opción del menú 👇"
    )


def manejar_listado_propiedades(text_lower, estado_usuario, user_id):
    """Maneja la selección de propiedades del listado"""
    log(f"[DEBUG] manejar_listado_propiedades: text_lower='{text_lower}', paso={estado_usuario.get('paso')}, ultimo_indice={estado_usuario.get('ultimo_indice_preguntado')}, propiedades_count={len(estado_usuario.get('propiedades_filtradas', []))}, operacion={estado_usuario.get('operacion_seleccionada')}")
    
    # 👇 NUEVO: Comandos de navegación en LETRAS (prioritarios)
    text_lower_clean = text_lower.lower().strip()
    
    # Comando para volver al menú principal
    if text_lower_clean in ["menu", "volver", "hola", "menu principal"]:
        log(f"[DEBUG] Usuario solicitó volver al MENÚ principal")
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['operacion_seleccionada'] = None
        estado_usuario['propiedades_filtradas'] = []
        estado_usuario['ultimo_indice_preguntado'] = None
        estado_usuario['ultima_accion'] = None
        actualizar_estado_usuario(user_id, estado_usuario)
        return "WELCOME_FLOW_TRIGGER"
    
    # Comando para salir completamente
    if text_lower_clean in ["salir", "chau", "adios", "exit", "0"]:
        log(f"[DEBUG] Usuario solicitó SALIR")
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['propiedades_filtradas'] = []
        actualizar_estado_usuario(user_id, estado_usuario)
        return "¡Gracias por confiar en Dante Propiedades! 🏠🗝️"
    
    # Si NO es un número, mostrar ayuda (pero ya manejamos los comandos arriba)
    if not text_lower.isdigit():
        propiedades_count = len(estado_usuario.get('propiedades_filtradas', []))
        return f"""❌ No entendí '{text_lower}'

📌 *Comandos válidos ahora:*
• Enviá el *NÚMERO de la propiedad* (1 al {propiedades_count}) para ver detalles
• Enviá *M* para volver al menú principal
• Enviá *S* para terminar la conversación

💡 *Ejemplo:* Si querés la propiedad 9, enviá '9' (sin comillas)"""
    
    # A partir de acá, text_lower ES un número
    indice = int(text_lower)
    propiedades = estado_usuario.get('propiedades_filtradas', [])
    
    log(f"[DEBUG] Propiedades encontradas en estado: {len(propiedades)} propiedades")
    
    if not propiedades:
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['ultima_accion'] = None
        actualizar_estado_usuario(user_id, estado_usuario)
        return "⚠️ No hay propiedades para mostrar o la sesión expiró.\n\n📱 Enviá *MENU* para volver al inicio."
    
    # NOTA: Ya NO tratamos el "0" como número especial porque "0" se captura arriba como "salir"
    # Si el usuario envía "0" (cero), va a entrar en el comando SALIR
    
    if 1 <= indice <= len(propiedades):
        propiedad = propiedades[indice - 1]
        log(f"[DEBUG] Usuario seleccionó propiedad {indice}: {propiedad.get('titulo')}")
        
        estado_usuario.update({
            'paso': 'detalle_propiedad',
            'ultimo_indice_preguntado': indice,
            'ultima_accion': None
        })
        actualizar_estado_usuario(user_id, estado_usuario)
        
        registrar_lead(user_id, propiedad.get('id_temporal', 'N/A'), "ver_detalle", f"Título: {propiedad.get('titulo')}")
        
        # Retornar menú interactivo optimizado
        return devolver_detalle_propiedad_menu(propiedad)
    else:
        return f"❌ El número {indice} está fuera de rango (1-{len(propiedades)}).\n\n📱 Enviá *MENU* para volver al inicio o *SALIR* para terminar."

def manejar_nombre_lead(text, estado_usuario, user_id):
    """Maneja la captura del nombre del lead"""
    nombre_cliente = text.strip()
    
    if len(nombre_cliente) < 2:
        return WhatsAppResponse.buttons(
            header="❌ ERROR EN EL NOMBRE",
            body="Por favor, ingresá tu nombre completo (mínimo 2 caracteres).",
            buttons=[
                {"id": "m", "title": "Volver al menú"},
                {"id": "s", "title": "Salir"}
            ]
        )
    
    estado_usuario['nombre_cliente'] = nombre_cliente
    
    indice = estado_usuario.get('ultimo_indice_preguntado')
    propiedades = estado_usuario.get('propiedades_filtradas', [])
    
    if indice and 1 <= indice <= len(propiedades):
        propiedad = propiedades[indice - 1]
        propiedad_id = propiedad.get('id_temporal', 'N/A')
        propiedad_titulo = propiedad.get('titulo', 'Propiedad sin título')
        
        registrar_lead(user_id, propiedad_id, "lead_completo", f"Nombre: {nombre_cliente}")
        
        # Análisis de IA de prioridad (Phase 7)
        historial = estado_usuario.get('data', {}).get('mensajes_recientes', [])
        analisis = obtener_prioridad_lead(user_id, historial, propiedad)
        
        prioridad_msg = f"\n\n🤖 *VEREDICTO IA*\n🌡️ Temperatura: {analisis['label_emoji']} (Score: {analisis['score']}/10)\n💡 Razón: _{analisis['razonamiento']}_"
        
        notificar_agente(f"🔥 *NUEVO INTERESADO*\n👤 Cliente: {nombre_cliente}\n📞 Tel: +{user_id}\n🏠 Propiedad: {propiedad_titulo}{prioridad_msg}")
        
        estado_usuario['paso'] = 'ofrecer_cita'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        return f"OFFER_MEETING_TRIGGER|{propiedad_titulo}"
    else:
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return WhatsAppResponse.buttons(
            header="❌ ERROR AL PROCESAR",
            body="Hubo un error al procesar tu interés. Por favor, volvé a buscar la propiedad.",
            buttons=[
                {"id": "opcion_7", "title": "Ver propiedades"},
                {"id": "m", "title": "Volver al menú"}
            ]
        )



def manejar_respuesta_feedback(text, estado_usuario, user_id):
    """Maneja la respuesta del usuario al mensaje de feedback"""
    # Defensive: data might be a string if parsing failed elsewhere
    data_obj = estado_usuario.get('data', {})
    if isinstance(data_obj, str):
        try:
            data_obj = json.loads(data_obj)
        except:
            data_obj = {}
            
    propiedad = data_obj.get('propiedad_feedback', 'la propiedad')
    nombre = estado_usuario.get('nombre_cliente', 'Cliente')
    
    log(f"📩 FEEDBACK RECIBIDO de {user_id}: {text}")
    
    # Notificar al agente
    mensaje_agente = f"🚩 *NUEVO FEEDBACK RECIBIDO*\n\n"
    mensaje_agente += f"👤 *Cliente:* {nombre} ({user_id})\n"
    mensaje_agente += f"🏠 *Propiedad:* {propiedad}\n"
    mensaje_agente += f"💬 *Respuesta:* {text}"
    
    try:
        notificar_agente(mensaje_agente)
    except Exception as e:
        log(f"⚠️ Error notificando feedback al agente: {e}")
    
    # Reset estado a menú principal
    estado_usuario.update({
        'paso': 'menu_principal',
        'operacion_seleccionada': None,
        'timestamp': datetime.now().isoformat()
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    
    return WhatsAppResponse.buttons(
        header="🙌 GRACIAS POR TU RESPUESTA",
        body=f"¡Muchas gracias *{nombre}*! Ya le pasé tus comentarios al asesor responsable. Se va a estar contactando con vos a la brevedad. 😊",
        buttons=[
            {"id": "opcion_7", "title": "Ver propiedades"},
            {"id": "m", "title": "Volver al menú"}
        ]
    )


def mostrar_panel_admin():
    """Muestra el panel administrativo para Dante"""
    return f"""🔐 *PANEL ADMINISTRATIVO*

Hola Dante 👋

Opciones disponibles:

📊 *1. Ver dashboard principal*
📅 *2. Gestionar citas*
👥 *3. Ver leads*
🏠 *4. Gestionar propiedades*
📈 *5. Ver estadísticas*

📱 *Envía 'M' para volver al menú principal*"""


def manejar_busqueda_keywords(termino, estado_usuario, user_id):
    """Busca propiedades por palabras clave y actualiza el estado"""
    # global propiedades # No es necesario el global aquí si usamos cargar_propiedades_cached
    propiedades_list = cargar_propiedades_cached()
        
    terminos = termino.lower().split()
    resultados = []
    
    for p in propiedades_list:
        match_score = 0
        texto_busqueda = f"{p.get('titulo', '')} {p.get('descripcion', '')} {p.get('barrio', '')} {p.get('tipo', '')}".lower()
        
        for t in terminos:
            if t in texto_busqueda:
                match_score += 1
        
        if match_score >= len(terminos): # Deben coincidir todas las palabras clave
            resultados.append(p)
            
    if not resultados:
        return f"🔍 No encontré propiedades que coincidan con *'{termino}*. \n\nIntentá con otras palabras (ej: 'casa parque') o enviá 'M' para ver todo.\n❌ *Envía 'S' para SALIR*"
        
    estado_usuario.update({
        'paso': 'listado_propiedades',
        'propiedades_filtradas': resultados,
        'operacion_seleccionada': 'busqueda'
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    
    mensaje = f"🔎 *Resultados para: {termino}* ({len(resultados)})\n\n"
    for i, p in enumerate(resultados[:5]):
        mensaje += f"*{i+1}️⃣ {p.get('titulo')}*\n📍 {p.get('barrio', 'S/D')} - ${p.get('precio', 'S/D')}\n\n"
    
    if len(resultados) > 5:
        mensaje += "📝 _Mostrando los primeros 5 resultados..._\n"
        
    mensaje += "\n👉 *Respondé con el número* (1, 2, 3...) para ver más detalle.\n"
    mensaje += "❌ *Envía 'S' para SALIR*"
    return mensaje

def manejar_detalle_propiedad(text_lower, estado_usuario, user_id):
    """Maneja las interacciones cuando el usuario está viendo el detalle de una propiedad"""
    
    # Mapear IDs de botones del menú interactivo a comandos
    mapeo_botones = {
        "ver_fotos": "f",
        "ver_pdf": "p",
        "me_interesa": "i",
        "ver_listado": "l",
        "m": "m",
        "s": "s",
        "requisitos": "req"
    }
    
    # Convertir ID de botón a comando si es necesario
    comando = mapeo_botones.get(text_lower, text_lower)
    
    # Comandos de navegación
    if comando in ["menu", "volver", "hola", "m"]:
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['propiedades_filtradas'] = []
        estado_usuario['ultimo_indice_preguntado'] = None
        actualizar_estado_usuario(user_id, estado_usuario)
        return "WELCOME_FLOW_TRIGGER"
    
    if comando in ["salir", "chau", "adios", "0", "s"]:
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['propiedades_filtradas'] = []
        actualizar_estado_usuario(user_id, estado_usuario)
        return "¡Gracias por confiar en Dante Propiedades! 🏠🗝️"
    
    # Comando para volver al listado de propiedades
    if comando in ["listado", "l", "listado propiedades"]:
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        if propiedades:
            estado_usuario['paso'] = 'listado_propiedades'
            actualizar_estado_usuario(user_id, estado_usuario)
            return generar_listado_propiedades(propiedades)
        else:
            estado_usuario['paso'] = 'menu_principal'
            actualizar_estado_usuario(user_id, estado_usuario)
            return "⚠️ No hay propiedades en el listado. Envía 'MENU' para volver al inicio."
    
    # Comando "I" o "me_interesa" - Me interesa
    if comando in ["i", "interesa", "me interesa"]:
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        
        if indice and 1 <= indice <= len(propiedades):
            propiedad = propiedades[indice - 1]
            estado_usuario['paso'] = 'esperando_nombre_lead'
            actualizar_estado_usuario(user_id, estado_usuario)
            
            try:
                registrar_lead(user_id, propiedad.get('id_temporal'), 'click_me_interesa', f"Interés expresado en Propiedad: {propiedad.get('titulo')}")
                notificar_agente(f"👀 *INTERÉS INICIAL*\n📞 Tel: +{user_id}\n🏠 Propiedad: {propiedad.get('titulo')}\n_(Esperando que el usuario ingrese su nombre...)_")
            except Exception as e:
                log(f"⚠️ Error registrando lead inicial: {e}")
                
            return f"✅ ¡Genial! Me interesa la propiedad: *{propiedad.get('titulo')}*.\n\nPor favor, decime tu *Nombre y Apellido* para que un asesor te contacte."
        else:
            return "⚠️ Error: No se pudo identificar la propiedad. Por favor, volvé al listado y seleccioná la propiedad nuevamente."
    
    # Comando "f" o "ver_fotos" - Ver fotos
    if comando == "f":
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        if indice and 1 <= indice <= len(propiedades):
            propiedad = propiedades[indice - 1]
            return f"PHOTOS_TRIGGER|{propiedad.get('id_temporal')}"
        else:
            return "⚠️ Error: No se pudo identificar la propiedad para mostrar las fotos."
    
    # Comando "p" o "ver_pdf" - Descargar PDF
    if comando == "p":
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        if indice and 1 <= indice <= len(propiedades):
            propiedad = propiedades[indice - 1]
            prop_id = propiedad.get('id_temporal')
            BASE_URL = os.environ.get("BASE_URL", "https://meta-rjpb.onrender.com")
            return f"📄 *Aquí tenés la ficha técnica oficial de {prop_id} para descargar:*\n{BASE_URL}/fichas/{prop_id}"
        else:
            return "⚠️ Error: No se pudo identificar la propiedad para generar el PDF."
    
    # Comando "req" o "requisitos" - Ver requisitos
    if comando == "req":
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        if indice and 1 <= indice <= len(propiedades):
            propiedad = propiedades[indice - 1]
            operacion = propiedad.get('operacion', 'alquiler')
            
            if operacion == 'alquiler':
                return """📋 *REQUISITOS PARA ALQUILER*

Para poder alquilar esta propiedad necesitas:

📝 *Documentación:*
• DNI vigente
• CUIL/CUIT
• Comprobante de ingresos (últimos 3 recibos)

💼 *Laborales:*
• Constancia de trabajo (con sueldo mínimo 3x la renta)
• Antiguedad en el trabajo: mín 1 año
• Referencias laborales

🏠 *Personales:*
• 2 referencias personales
• Comprobante de domicilio actual

💰 *Económicos:*
• Depósito caución: 2 meses de renta
• 1er mes de renta adelantado
• Gastos de gestión (según inmobiliaria)

¿Necesitás ayuda para completar la documentación? 📞"""
            else:
                return """📋 *REQUISITOS PARA COMPRA*

Para poder comprar esta propiedad necesitas:

📝 *Documentación:*
• DNI vigente
• CUIL/CUIT
• Comprobante de origen de fondos
• Estado patrimonial

💼 *Financieros:*
• Capacidad de financiamiento
• Certificado de no adeudar impuestos
• Comprobantes de ingresos

🏦 *Bancarios:*
• Pre-aprobación de crédito (si aplica)
• Referencias bancarias

¿Necesitás ayuda para la gestión? 📞"""
        else:
            return "⚠️ Error: No se pudo identificar la propiedad."
    
    # Si no se reconoce el comando, mostrar opciones con botones
    return WhatsAppResponse.buttons(
        header="🏠 ACCIONES DISPONIBLES",
        body="Seleccioná qué querés hacer con esta propiedad:",
        buttons=[
            {"id": "i", "title": "Me interesa ❤️"},
            {"id": "f", "title": "Ver fotos 📷"},
            {"id": "p", "title": "Descargar PDF 📄"}
        ],
        footer="L = Listado | M = Menú | S = Salir"
    )