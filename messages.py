# ========== MENSAJES Y PLANTILLAS ==========
"""
Todos los mensajes del chatbot inmobiliario
"""

from config import (
    OPERACIONES, TIPOS_INMUEBLE, ZONAS, AMBIENTES,
    PRESUPUESTO_COMPRA, PRESUPUESTO_ALQUILER, URGENCIA,
    CARACTERISTICAS, INMOBILIARIA
)

# ========== MENSAJE DE BIENVENIDA ==========
def msg_bienvenida(nombre_usuario: str = None) -> str:
    saludo = f"¡Hola{' ' + nombre_usuario if nombre_usuario else ''}! 👋"
    return f"""{saludo}

Soy el asistente virtual de *{INMOBILIARIA['nombre']}*.

Para ayudarte mejor, respondé con el *número* de tu objetivo:

1️⃣ Comprar
2️⃣ Alquilar (largo plazo)
3️⃣ Alquiler vacacional
4️⃣ Tasar mi propiedad

¿Cuál es tu objetivo hoy?"""

# ========== MENSAJE OPERACIÓN SELECCIONADA ==========
def msg_operacion_seleccionada(operacion: dict) -> str:
    return f"""✅ Perfecto, buscás *{operacion['nombre'].lower()}*.

Ahora decime, ¿qué tipo de inmueble te interesa?

1️⃣ Apartamento/Departamento
2️⃣ Casa/Chalet
3️⃣ Terreno
4️⃣ Local comercial
5️⃣ Oficina

Respondé con el número."""

# ========== MENSAJE TIPO INMUEBLE SELECCIONADO ==========
def msg_tipo_seleccionado(tipo: dict) -> str:
    return f"""🏠 Excelente, *{tipo['nombre'].lower()}*.

¿En qué zona de Buenos Aires preferís?

1️⃣ San Telmo
2️⃣ Palermo
3️⃣ Recoleta
4️⃣ Belgrano
5️⃣ Puerto Madero
6️⃣ Caballito
7️⃣ Núñez
8️⃣ Villa Crespo
9️⃣ Otra zona

Respondé con el número."""

# ========== MENSAJE ZONA OTRA ==========
def msg_zona_otra() -> str:
    return """📍 ¿Qué zona te interesa?

Escribí el nombre del barrio o zona que buscás.

_Ejemplo: Villa Urquiza, Almagro, Flores, etc._"""

# ========== MENSAJE ZONA SELECCIONADA ==========
def msg_zona_seleccionada(zona_nombre: str, tipo_inmueble: str) -> str:
    # Ajustar pregunta según tipo de inmueble
    if tipo_inmueble in ["terreno"]:
        return f"""📍 Zona: *{zona_nombre}*

¿Cuántos metros cuadrados aproximadamente?

1️⃣ Hasta 200 m²
2️⃣ 200 - 500 m²
3️⃣ 500 - 1000 m²
4️⃣ Más de 1000 m²"""

    return f"""📍 Perfecto, *{zona_nombre}*.

¿Cuántos ambientes necesitás?

1️⃣ Monoambiente
2️⃣ 2 ambientes
3️⃣ 3 ambientes
4️⃣ 4 o más ambientes

Respondé con el número."""

# ========== MENSAJE AMBIENTES SELECCIONADOS ==========
def msg_ambientes_seleccionados(ambientes: str, es_compra: bool) -> str:
    emoji = "🛏️" if "mono" not in ambientes.lower() else "🏠"

    if es_compra:
        return f"""{emoji} *{ambientes}*, anotado.

¿Cuál es tu presupuesto aproximado?

1️⃣ Hasta USD 50.000
2️⃣ USD 50.000 - 100.000
3️⃣ USD 100.000 - 150.000
4️⃣ USD 150.000 - 250.000
5️⃣ Más de USD 250.000

Respondé con el número."""
    else:
        return f"""{emoji} *{ambientes}*, anotado.

¿Cuál es tu presupuesto mensual aproximado?

1️⃣ Hasta $300.000/mes
2️⃣ $300.000 - $500.000/mes
3️⃣ $500.000 - $800.000/mes
4️⃣ Más de $800.000/mes

Respondé con el número."""

# ========== MENSAJE PRESUPUESTO SELECCIONADO ==========
def msg_presupuesto_seleccionado(presupuesto: str) -> str:
    return f"""💰 Presupuesto: *{presupuesto}*

¿Para cuándo lo necesitás?

1️⃣ 🔥 Inmediato (este mes)
2️⃣ 📅 En 1-3 meses
3️⃣ 🗓️ En 3-6 meses
4️⃣ 🔍 Solo estoy explorando

Respondé con el número."""

# ========== MENSAJE URGENCIA SELECCIONADA ==========
def msg_urgencia_seleccionada(urgencia: str) -> str:
    return f"""⏰ Tiempo: *{urgencia}*

Por último, ¿alguna característica especial que busques?

Podés elegir *varias* separadas por coma (ej: 1,3,4) o una sola:

1️⃣ 🚗 Cochera/Parking
2️⃣ 🏊 Piscina
3️⃣ 🔥 Quincho/Parrilla
4️⃣ 🌅 Terraza/Balcón
5️⃣ 🏋️ Amenities (gym, SUM)
6️⃣ 🐕 Acepta mascotas
7️⃣ 🛋️ Amueblado
0️⃣ ➡️ Ninguna en particular

Respondé con los números."""

# ========== MENSAJE RESUMEN ==========
def msg_resumen(datos: dict) -> str:
    caracteristicas_str = ", ".join(datos.get("caracteristicas", [])) or "Sin preferencia específica"

    return f"""📋 *RESUMEN DE TU BÚSQUEDA*
━━━━━━━━━━━━━━━━━━━━━

🎯 *Operación:* {datos.get('operacion', 'N/A')}
🏠 *Tipo:* {datos.get('tipo_inmueble', 'N/A')}
📍 *Zona:* {datos.get('zona_nombre', 'N/A')}
🛏️ *Ambientes:* {datos.get('ambientes', 'N/A')}
💰 *Presupuesto:* {datos.get('presupuesto_rango', 'N/A')}
⏰ *Plazo:* {datos.get('urgencia', 'N/A')}
✨ *Extras:* {caracteristicas_str}

━━━━━━━━━━━━━━━━━━━━━

¿Es correcta esta información?

1️⃣ ✅ Sí, buscar opciones
2️⃣ ✏️ Modificar algo
3️⃣ 🔄 Empezar de nuevo"""

# ========== MENSAJE CONFIRMACIÓN ==========
def msg_confirmacion_final() -> str:
    return f"""🎉 *¡Excelente!*

Hemos registrado tu búsqueda. Un asesor de *{INMOBILIARIA['nombre']}* te contactará pronto con las mejores opciones.

📞 Si preferís hablar ahora, llamanos al {INMOBILIARIA['telefono_agente']}

🕐 Horario de atención: {INMOBILIARIA['horario']}

¿Hay algo más en lo que pueda ayudarte?

Escribí *"hola"* para iniciar una nueva búsqueda."""

# ========== MENSAJES DE TASACIÓN ==========
def msg_tasacion_inicio() -> str:
    return """📊 *TASACIÓN DE PROPIEDAD*

Para darte una estimación, necesito algunos datos.

Primero, ¿cuál es la *dirección* de la propiedad?

_Escribí la dirección completa (calle, número, barrio)_"""

def msg_tasacion_tipo() -> str:
    return """📍 Dirección registrada.

¿Qué tipo de propiedad es?

1️⃣ Departamento
2️⃣ Casa
3️⃣ PH
4️⃣ Local comercial
5️⃣ Oficina
6️⃣ Terreno

Respondé con el número."""

def msg_tasacion_m2() -> str:
    return """🏠 Tipo registrado.

¿Cuántos *metros cuadrados* tiene la propiedad?

_Escribí solo el número (ej: 65)_"""

def msg_tasacion_antiguedad() -> str:
    return """📐 Metros registrados.

¿Cuál es la *antigüedad* aproximada?

1️⃣ A estrenar
2️⃣ Hasta 10 años
3️⃣ 10-30 años
4️⃣ Más de 30 años

Respondé con el número."""

def msg_tasacion_resumen(datos: dict) -> str:
    return f"""📊 *SOLICITUD DE TASACIÓN*
━━━━━━━━━━━━━━━━━━━━━

📍 *Dirección:* {datos.get('tasacion_direccion', 'N/A')}
🏠 *Tipo:* {datos.get('tasacion_tipo', 'N/A')}
📐 *Superficie:* {datos.get('tasacion_m2', 'N/A')} m²
📅 *Antigüedad:* {datos.get('tasacion_antiguedad', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━

Un tasador profesional de *{INMOBILIARIA['nombre']}* analizará tu propiedad y te contactará con una valuación.

📞 Contacto: {INMOBILIARIA['telefono_agente']}

¿Los datos son correctos?

1️⃣ ✅ Sí, enviar solicitud
2️⃣ ✏️ Corregir datos
3️⃣ 🔄 Cancelar"""

# ========== MENSAJES DE ERROR ==========
def msg_opcion_invalida(opciones_validas: str = "1-4") -> str:
    return f"""⚠️ No entendí tu respuesta.

Por favor, respondé con un número válido ({opciones_validas}).

Si querés empezar de nuevo, escribí *"reiniciar"*."""

def msg_error_generico() -> str:
    return """😅 Ups, algo salió mal.

Escribí *"hola"* para empezar de nuevo o *"ayuda"* para ver las opciones."""

# ========== MENSAJES DE AYUDA ==========
def msg_ayuda() -> str:
    return f"""📚 *AYUDA - {INMOBILIARIA['nombre']}*

Comandos disponibles:
• *hola* - Iniciar nueva búsqueda
• *reiniciar* - Volver a empezar
• *estado* - Ver tu búsqueda actual
• *ayuda* - Ver este mensaje
• *agente* - Hablar con una persona

📞 Teléfono: {INMOBILIARIA['telefono_agente']}
🌐 Web: {INMOBILIARIA['web']}"""

def msg_agente_humano() -> str:
    return f"""👤 *ATENCIÓN PERSONALIZADA*

Un asesor te contactará en breve.

Si preferís comunicarte ahora:
📞 {INMOBILIARIA['telefono_agente']}
📧 {INMOBILIARIA['email']}

🕐 {INMOBILIARIA['horario']}"""
