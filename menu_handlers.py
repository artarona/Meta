from utils import *
from database import *
from whatsapp_api import *
from citas import *
from config import *
import time
import os
import json
from datetime import datetime

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
        return "🌐 *Visita nuestra web oficial:*\n\n👉 https://www.dantepropiedades.com.ar\n\nEnvía 'Hola' para volver al menú.\n0️⃣ *❌ SALIR*"

    elif text_lower == "4":
        # Ver mis citas
        return procesar_opcion_mis_citas(user_id)

    elif text_lower == "5":
        # Hablar con asesor
        estado_usuario['paso'] = 'submenu_asesor'
        actualizar_estado_usuario(user_id, estado_usuario)
        return """👤 *HABLAR CON UN ASESOR*

1️⃣ Enviar mensaje al asesor
2️⃣ Solicitar llamada

9️⃣ Volver al menú principal
0️⃣ Salir"""

    elif text_lower == "6":
        # FAQs
        return """❓ *REQUISITOS Y PREGUNTAS FRECUENTES*

*Para Alquilar:*
• Mes de adelanto
• Mes de depósito (en USD)
• Garantía propietaria (CABA/GBA) o Seguro de Caución (Finaer)
• Demostración de ingresos (últimos 3 recibos)

*¿Aceptan Mascotas?*
Depende estrictamente de la propiedad y el consorcio. Consultalo en el detalle de cada departamento.

*¿Toman propiedades en parte de pago?*
Sí, evaluamos permutas caso por caso. Escribinos para tasación.

9️⃣ *🔙 VOLVER AL MENÚ PRINCIPAL*
0️⃣ *❌ SALIR*"""

    elif text_lower == "9":
        # Volver al menú
        return "WELCOME_FLOW_TRIGGER"
        
    elif text_lower == "0":
        # Salir
        return "¡Gracias por confiar en Dante Propiedades! 🏠🗝️"

    elif text_lower == "8" and user_id == ADMIN_NUMBER.lstrip('549'):
        # Panel admin (solo para número autorizado)
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

9️⃣ *Volver al menú principal*
0️⃣ *Salir del chat*"""


def manejar_submenu_consultar(text_lower, estado_usuario, user_id):
    """Maneja las opciones del submenú de consulta"""
    if text_lower == "1":
        return "🔎 *Búsqueda por código*\n\nPor favor, enviá el código de la propiedad (ej: UF002).\n\n9️⃣ Volver al menú principal\n0️⃣ Salir"
    elif text_lower == "2":
        return "📍 *Búsqueda por zona*\n\n¿En qué zona estás buscando? (ej: Palermo, Belgrano, Tigre...)\n\n9️⃣ Volver al menú principal\n0️⃣ Salir"
    elif text_lower == "3":
        return procesar_opcion_todas(estado_usuario, user_id)
    else:
        return """No pude identificar esa opción. Por favor elegí un número del menú.

9️⃣ *Volver al menú principal*
0️⃣ *Salir del chat*"""


def manejar_submenu_visita(text_lower, estado_usuario, user_id):
    """Maneja las opciones del submenú de visitas"""
    if text_lower == "1":
        return procesar_opcion_todas(estado_usuario, user_id)
    elif text_lower == "2":
        return "📅 *Días y horarios disponibles*\n\nNuestros horarios generales son de Lunes a Viernes de 9 a 18:30 hs.\n\n9️⃣ Volver al menú principal\n0️⃣ Salir"
    elif text_lower == "3":
        return "✅ *Confirmar visita*\n\nPara confirmar una visita, primero debemos seleccionar una propiedad. \n\n1️⃣ Ver propiedades\n9️⃣ Volver al menú principal\n0️⃣ Salir"
    else:
        return """No pude identificar esa opción. Por favor elegí un número del menú.

9️⃣ *Volver al menú principal*
0️⃣ *Salir del chat*"""


def manejar_submenu_asesor(text_lower, estado_usuario, user_id):
    """Maneja las opciones del submenú de asesor"""
    if text_lower == "1":
        notificar_agente(f"👤 *SOLICITUD DE ASESOR*\n📞 Tel: +{user_id}\n📝 El cliente desea enviar un mensaje.")
        return "✅ *Mensaje enviado!*\n\nUn asesor se pondrá en contacto con vos a la brevedad.\n\n9️⃣ Volver al menú principal\n0️⃣ Salir"
    elif text_lower == "2":
        notificar_agente(f"📞 *SOLICITUD DE LLAMADA*\n📞 Tel: +{user_id}\n📝 El cliente solicita ser llamado.")
        return "✅ *Solicitud registrada!*\n\nTe llamaremos en el horario más conveniente.\n\n9️⃣ Volver al menú principal\n0️⃣ Salir"
    else:
        return """No pude identificar esa opción. Por favor elegí un número del menú.

9️⃣ *Volver al menú principal*
0️⃣ *Salir del chat*"""


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
             estado_usuario['propiedades_filtradas'] = []
             actualizar_estado_usuario(user_id, estado_usuario)
             return f"📭 Lo siento, no tenemos {tipo_seleccionado}s disponibles para {operacion} en este momento.\n\n9️⃣ *🔙 VOLVER AL MENÚ PRINCIPAL*\n0️⃣ *❌ SALIR*"

        return f"""🔢 *¿CUÁNTOS AMBIENTES?*

Por favor, elegí la cantidad de ambientes:
1️⃣ 1 Ambiente
2️⃣ 2 Ambientes
3️⃣ 3 Ambientes
4️⃣ 4 o más Ambientes
5️⃣ Cualquiera / Sin preferencia

9️⃣ *🔙 VOLVER AL MENÚ PRINCIPAL*
0️⃣ *❌ SALIR*"""
    else:
        return "⚠️ Por favor, elegí una opción válida (1 al 5) o enviá 9 para volver al menú."


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
            'propiedades_filtradas': propiedades_filtradas
        })
        actualizar_estado_usuario(user_id, estado_usuario)
        
        if not propiedades_filtradas:
            return f"📭 No encontramos propiedades con esas características exactas.\n\n9️⃣ *🔙 VOLVER AL MENÚ PRINCIPAL*\n0️⃣ *❌ SALIR*"
        
        titulo_op = "💰 *VENTA*" if operacion == "venta" else "🔑 *ALQUILER*"
        tipo_str = tipo.title()
        amb_str = f"de {ambientes_sel} amb." if ambientes_sel else ""
        if ambientes_sel == 4: amb_str = "de 4+ amb."
        
        return f"{titulo_op}\nBuscando: {tipo_str} {amb_str}\nEncontramos *{len(propiedades_filtradas)}* opciones:\n\n" + generar_listado_propiedades(propiedades_filtradas)
    
    else:
         return "⚠️ Por favor, elegí una opción válida (1 al 5) o enviá 9 para volver al menú."


def procesar_opcion_venta(estado_usuario, user_id):
    """Procesa la opción de venta preguntando el tipo de propiedad"""
    estado_usuario.update({
        'paso': 'filtro_tipo',
        'operacion_seleccionada': 'venta'
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    
    return """🏡 *¿QUÉ TIPO DE PROPIEDAD BUSCÁS?*

Por favor, elegí un número:
1️⃣ Departamento
2️⃣ Casa
3️⃣ PH
4️⃣ Oficina / Local
5️⃣ Terreno / Lote

9️⃣ *🔙 VOLVER AL MENÚ PRINCIPAL*
0️⃣ *❌ SALIR*"""


def procesar_opcion_alquiler(estado_usuario, user_id):
    """Procesa la opción de alquiler preguntando el tipo de propiedad"""
    estado_usuario.update({
        'paso': 'filtro_tipo',
        'operacion_seleccionada': 'alquiler'
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    
    return """🔑 *¿QUÉ TIPO DE PROPIEDAD BUSCÁS?*

Por favor, elegí un número:
1️⃣ Departamento
2️⃣ Casa
3️⃣ PH
4️⃣ Oficina / Local
5️⃣ Terreno / Lote

9️⃣ *🔙 VOLVER AL MENÚ PRINCIPAL*
0️⃣ *❌ SALIR*"""


def procesar_opcion_todas(estado_usuario, user_id):
    """Procesa la opción de ver todas las propiedades"""
    estado_usuario.update({
        'paso': 'listado_propiedades',
        'operacion_seleccionada': 'todas',
        'propiedades_filtradas': cargar_propiedades_cached()
    })
    actualizar_estado_usuario(user_id, estado_usuario)
    return "📋 *TODAS LAS PROPIEDADES*\n\n" + generar_listado_propiedades(estado_usuario['propiedades_filtradas'])


def procesar_opcion_mis_citas(user_id):
    """Procesa la opción de ver mis citas"""
    citas = cargar_citas()
    citas_usuario = [c for c in citas if c['telefono'] == user_id and c['estado'] != 'cancelada']
    
    if not citas_usuario:
        return "📅 *No tienes citas agendadas*\n\nPara agendar una cita, primero selecciona una propiedad y haz clic en 'Me interesa' (8).\n\n1️⃣ *VOLVER AL MENÚ* 🏠\n0️⃣ *❌ SALIR*"
    
    mensaje = f"📅 *TUS CITAS AGENDADAS*\n\nTienes *{len(citas_usuario)}* cita(s) activa(s):\n\n"
    
    for i, cita in enumerate(citas_usuario, 1):
        fecha_obj = datetime.strptime(cita['fecha'], "%Y-%m-%d")
        fecha_formateada = fecha_obj.strftime("%d/%m/%Y")
        
        mensaje += f"{i}. *{cita['propiedad_id']}*\n"
        mensaje += f"   📅 {fecha_formateada} - ⏰ {cita['hora']}\n"
        mensaje += f"   📍 Estado: {cita['estado'].upper()}\n"
        
        if cita.get('notas') and cita['notas'] != 'Sin notas adicionales':
            mensaje += f"   📝 Notas: {cita['notas'][:50]}...\n"
        
        mensaje += "   ───────────────\n"
    
    mensaje += f"\nPara consultar o modificar una cita, contacta al administrador.\n\n"
    mensaje += f"Envía 'Hola' para volver al menú.\n0️⃣ *❌ SALIR*"
    
    return mensaje


def manejar_listado_propiedades(text_lower, estado_usuario, user_id):
    """Maneja la selección de propiedades del listado"""
    if not text_lower.isdigit():
        return "Por favor, elegí un número del listado o enviá 'Hola' para volver.\n0️⃣ *❌ SALIR*"
    
    indice = int(text_lower)
    propiedades = estado_usuario.get('propiedades_filtradas', [])
    
    if not propiedades:
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "⚠️ No hay propiedades para mostrar. Envía 'Hola' para volver al menú.\n0️⃣ *❌ SALIR*"
    
    if indice == 0:
        estado_usuario['paso'] = 'menu_principal'
        estado_usuario['operacion_seleccionada'] = None
        estado_usuario['propiedades_filtradas'] = []
        estado_usuario['ultimo_indice_preguntado'] = None
        actualizar_estado_usuario(user_id, estado_usuario)
        return "WELCOME_FLOW_TRIGGER"
    
    if 1 <= indice <= len(propiedades):
        propiedad = propiedades[indice - 1]
        estado_usuario.update({
            'paso': 'detalle_propiedad',
            'ultimo_indice_preguntado': indice
        })
        actualizar_estado_usuario(user_id, estado_usuario)
        
        registrar_lead(user_id, propiedad.get('id_temporal', 'N/A'), "ver_detalle", f"Título: {propiedad.get('titulo')}")
        
        operacion = propiedad.get('operacion', '')
        titulo_op = "💰 VENTA" if operacion == 'venta' else "🔑 ALQUILER" if operacion == 'alquiler' else "🏠 PROPIEDAD"
        return f"{titulo_op}\n" + "─" * 30 + "\n" + formatear_detalle_propiedad(propiedad)
    else:
        return f"❌ El número {indice} está fuera de rango (1-{len(propiedades)}). Elige uno o envía 9 para volver.\n0️⃣ *Salir*"


def manejar_detalle_propiedad(text_lower, estado_usuario, user_id):
    """Maneja las opciones en el detalle de propiedad"""
    if text_lower == "1":
        estado_usuario.update({
            'paso': 'menu_principal',
            'operacion_seleccionada': None,
            'propiedades_filtradas': [],
            'ultimo_indice_preguntado': None
        })
        actualizar_estado_usuario(user_id, estado_usuario)
        return "WELCOME_FLOW_TRIGGER"
    
    if text_lower.isdigit():
        indice = int(text_lower)
        propiedades = estado_usuario.get('propiedades_filtradas', [])
        if 1 <= indice <= len(propiedades):
            propiedad = propiedades[indice - 1]
            estado_usuario['ultimo_indice_preguntado'] = indice
            actualizar_estado_usuario(user_id, estado_usuario)
            
            registrar_lead(user_id, propiedad.get('id_temporal', 'N/A'), "ver_detalle", f"Título: {propiedad.get('titulo')}")
            
            operacion = propiedad.get('operacion', '')
            titulo_op = "💰 VENTA" if operacion == 'venta' else "🔑 ALQUILER" if operacion == 'alquiler' else "🏠 PROPIEDAD"
            return f"{titulo_op}\n" + "─" * 30 + "\n" + formatear_detalle_propiedad(propiedad)
    
    return "📷 'F' Fotos | 8️⃣ '8' Me interesa\n9️⃣ Volver al menú | 0️⃣ *Salir*"


def manejar_nombre_lead(text, estado_usuario, user_id):
    """Maneja la captura del nombre del lead"""
    nombre_cliente = text.strip()
    
    if len(nombre_cliente) < 2:
        return "❌ Por favor, ingresa tu nombre completo (mínimo 2 caracteres).\n\n9️⃣ *Volver al menú principal*\n0️⃣ *Salir*"
    
    estado_usuario['nombre_cliente'] = nombre_cliente
    
    indice = estado_usuario.get('ultimo_indice_preguntado')
    propiedades = estado_usuario.get('propiedades_filtradas', [])
    
    if indice and 1 <= indice <= len(propiedades):
        propiedad = propiedades[indice - 1]
        propiedad_id = propiedad.get('id_temporal', 'N/A')
        propiedad_titulo = propiedad.get('titulo', 'Propiedad sin título')
        
        registrar_lead(user_id, propiedad_id, "lead_completo", f"Nombre: {nombre_cliente}")
        
        notificar_agente(f"🔥 *NUEVO INTERESADO*\n👤 Cliente: {nombre_cliente}\n📞 Tel: +{user_id}\n🏠 Propiedad: {propiedad_titulo}")
        
        estado_usuario['paso'] = 'ofrecer_cita'
        actualizar_estado_usuario(user_id, estado_usuario)
        
        return f"OFFER_MEETING_TRIGGER|{propiedad_titulo}"
    else:
        estado_usuario['paso'] = 'menu_principal'
        actualizar_estado_usuario(user_id, estado_usuario)
        return "❌ Hubo un error al procesar tu interés. Por favor, volvé a buscar la propiedad.\n\n9️⃣ Volver al menú principal\n0️⃣ *Salir*"


