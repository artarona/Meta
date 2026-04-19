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
            
        return f"📭 No encontramos {tipo}s de {ambientes_sel} ambientes en {operacion}.\n\n🔍 *Pero tenemos otras opciones de {tipo} que te pueden interesar:* \n\n" + generar_listado_propiedades(estado_usuario['propiedades_filtradas'])
        
        titulo_op = "💰 *VENTA*" if operacion == "venta" else "🔑 *ALQUILER*"
        tipo_str = tipo.title()
        amb_str = f"de {ambientes_sel} amb." if ambientes_sel else ""
        if ambientes_sel == 4: amb_str = "de 4+ amb."
        
        return f"{titulo_op}\nBuscando: {tipo_str} {amb_str}\nEncontramos *{len(propiedades_filtradas)}* opciones:\n\n" + generar_listado_propiedades(propiedades_filtradas)
    
    else:
         return "⚠️ Por favor, elegí una opción válida (1 al 5) o enviá 'M' para volver al menú."



def restaurar_listado_si_es_necesario(estado_usuario):
    # Si no hay propiedades pero hay contexto, reconstruye la lista
    if not estado_usuario.get('propiedades_filtradas') and estado_usuario.get('ultimo_contexto'):
        contexto = estado_usuario['ultimo_contexto']
        if contexto['tipo'] == 'venta':
            # Vuelve a filtrar por venta
            nuevas_props = [p for p in cargar_propiedades_cached() if p.get('operacion') == 'venta']
            estado_usuario['propiedades_filtradas'] = nuevas_props
            return nuevas_props
    return estado_usuario.get('propiedades_filtradas', [])


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
        return "📭 Actualmente no tenemos propiedades en *venta*.\n\nⓂ️ *VOLVER AL MENÚ (Envía 'M')*\n❌ *SALIR (Envía 'S')*"
    
    return "💰 *INMUEBLES EN VENTA*\n\n" + generar_listado_propiedades(filtradas)


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
        return "📭 Actualmente no tenemos propiedades en *alquiler*.\n\nⓂ️ *VOLVER AL MENÚ (Envía 'M')*\n❌ *SALIR (Envía 'S')*"
    
    return "🔑 *INMUEBLES EN ALQUILER*\n\n" + generar_listado_propiedades(filtradas)


def procesar_opcion_todas(estado_usuario, user_id):
    """Procesa la opción de ver todas las propiedades"""
    estado_usuario.update({
        'paso': 'listado_propiedades',
        'operacion_seleccionada': 'todas',
        'propiedades_filtradas': cargar_propiedades_cached(),
        'ultima_accion': 'mostrar_listado'
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    return "📋 *TODAS LAS PROPIEDADES*\n\n" + generar_listado_propiedades(estado_usuario['propiedades_filtradas'])


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
            body="Para agendar una cita, seleccioná una propiedad del catálogo y presã *'Me interesa'* (letra I).",
            buttons=[
                {"id": "opcion_7", "title": "Ver propiedades"},
                {"id": "m", "title": "Volver al menú"}
            ]
        )
    
    mensaje = f"📅 *TUS CITAS AGENDADAS*\n\nTienes *{len(citas_usuario)}* cita(s) activa(s):\n\n"
    
    for i, cita in enumerate(citas_usuario, 1):
        try:
            fecha_obj = datetime.strptime(cita.get('fecha', ''), "%Y-%m-%d")
            fecha_formateada = fecha_obj.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            fecha_formateada = cita.get('fecha', 'Sin fecha')
        
        mensaje += f"{i}. *{cita.get('propiedad_id', 'Propiedad')}*\n"
        mensaje += f"   📅 {fecha_formateada} - ⏰ {cita.get('hora', 'Sin hora')}\n"
        mensaje += f"   📍 Estado: {cita.get('estado', 'Pendiente').upper()}\n"
        
        if cita.get('notas') and cita['notas'] not in ('Sin notas', 'Sin notas adicionales', ''):
            mensaje += f"   📝 Notas: {cita['notas'][:50]}...\n"
        
        mensaje += "   ───────────────\n"
    
    # Opción A: enviar texto rico + botones como 2 mensajes
    nav_buttons = WhatsAppResponse.buttons(
        header="📅 TUS CITAS",
        body="Para consultar o modificar una cita, contactá al administrador.",
        buttons=[
            {"id": "opcion_4", "title": "Ver mis citas"},
            {"id": "m", "title": "Volver al menú"},
            {"id": "s", "title": "Salir"}
        ]
    )
    return [mensaje, nav_buttons]


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
        
        operacion = propiedad.get('operacion', '')
        titulo_op = "💰 VENTA" if operacion == 'venta' else "🔑 ALQUILER" if operacion == 'alquiler' else "🏠 PROPIEDAD"
        return f"{titulo_op}\n" + "─" * 30 + "\n" + formatear_detalle_propiedad(propiedad)
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
    
    # Comandos de navegación
    if text_lower in ["menu", "volver", "hola"]:
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['propiedades_filtradas'] = []
        estado_usuario['ultimo_indice_preguntado'] = None
        actualizar_estado_usuario(user_id, estado_usuario)
        return "WELCOME_FLOW_TRIGGER"
    
    if text_lower in ["salir", "chau", "adios", "0"]:
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['propiedades_filtradas'] = []
        actualizar_estado_usuario(user_id, estado_usuario)
        return "¡Gracias por confiar en Dante Propiedades! 🏠🗝️"
    
    # Comando para volver al listado de propiedades
    if text_lower in ["listado", "l", "listado propiedades"]:
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        if propiedades:
            estado_usuario['paso'] = 'listado_propiedades'
            actualizar_estado_usuario(user_id, estado_usuario)
            return generar_listado_propiedades(propiedades)
        else:
            estado_usuario['paso'] = 'menu_principal'
            actualizar_estado_usuario(user_id, estado_usuario)
            return "⚠️ No hay propiedades en el listado. Envía 'MENU' para volver al inicio."
    
    # Comando "I" - Me interesa
    if text_lower in ["i", "interesa", "me interesa"]:
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
    
    # Comando "f" - Ver fotos
    if text_lower == "f":
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        if indice and 1 <= indice <= len(propiedades):
            propiedad = propiedades[indice - 1]
            return f"PHOTOS_TRIGGER|{propiedad.get('id_temporal')}"
        else:
            return "⚠️ Error: No se pudo identificar la propiedad para mostrar las fotos."
    
    # Comando "p" - Descargar PDF
    if text_lower == "p":
        indice = estado_usuario.get('ultimo_indice_preguntado')
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        if indice and 1 <= indice <= len(propiedades):
            propiedad = propiedades[indice - 1]
            prop_id = propiedad.get('id_temporal')
            BASE_URL = os.environ.get("BASE_URL", "https://meta-rjpb.onrender.com")
            return f"📄 *Aquí tenés la ficha técnica oficial de {prop_id} para descargar:*\n{BASE_URL}/fichas/{prop_id}"
        else:
            return "⚠️ Error: No se pudo identificar la propiedad para generar el PDF."
    
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