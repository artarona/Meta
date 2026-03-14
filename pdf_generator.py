import os
import json
from fpdf import FPDF
from datetime import datetime

class PropertyPDF(FPDF):
    def header(self):
        # Logo de la empresa
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_dir, 'llave.png')
        
        if os.path.exists(logo_path):
            try:
                self.image(logo_path, 10, 8, h=10) 
                self.set_x(32)
            except Exception as e:
                print(f"⚠️ Error cargando logo PDF: {e}")
        else:
            print(f"⚠️ Logo no encontrado en: {logo_path}")
        
        # Título de la Inmobiliaria
        self.set_font('helvetica', 'B', 15)
        self.set_text_color(44, 62, 80)
        self.cell(0, 10, 'DANTE INMOBILIARIA - Ficha de Propiedad', 0, 1, 'L')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Pagina {self.page_no()} - Generado el {datetime.now().strftime("%d/%m/%Y")}', 0, 0, 'C')

def clean_text(text):
    if not text: return ""
    if not isinstance(text, str): text = str(text)
    # Reemplazos comunes y caracteres acentuados para Latin-1
    replacements = {
        '²': '2', '•': '-', '–': '-', '—': '-', '’': "'", '“': '"', '”': '"', '…': '...', '°': 'o'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    
    # FPDF con fuentes estándar (Helvetica, etc) prefiere latin-1
    # Pero si hay algo que latin-1 no soporta, lo ignoramos
    return text.encode('latin-1', 'ignore').decode('latin-1')

def generar_pdf_propiedad(propiedad, output_path, datos_entorno=None):
    """
    Genera un PDF profesional para una propiedad incluyendo datos del entorno.
    """
    pdf = PropertyPDF()
    pdf.add_page()
    
    # Título
    pdf.set_font('helvetica', 'B', 20)
    pdf.set_text_color(44, 62, 80)
    titulo = clean_text(propiedad.get('titulo', 'Sin Titulo'))
    pdf.multi_cell(0, 10, titulo, align='L')
    
    # Operación
    pdf.ln(2)
    operacion = clean_text(propiedad.get('operacion', '').upper())
    pdf.set_font('helvetica', 'B', 14)
    pdf.set_text_color(231, 76, 60)
    pdf.multi_cell(0, 10, f"EN {operacion}", align='L')
    
    pdf.ln(2)
    
    # Precio y Ubicación
    pdf.set_font('helvetica', 'B', 16)
    pdf.set_text_color(39, 174, 96)
    moneda_precio = clean_text(propiedad.get('moneda_precio', 'USD'))
    try:
        precio_val = propiedad.get('precio', 0)
        precio_str = f"{moneda_precio} {int(precio_val):,}" if precio_val > 0 else "Consultar Precio"
    except:
        precio_str = "Consultar Precio"
        
    pdf.cell(0, 10, f"Precio: {precio_str}", 0, 1)
    
    pdf.set_font('helvetica', '', 12)
    pdf.set_text_color(52, 73, 94)
    barrio_nombre = propiedad.get('barrio', 'N/A')
    barrio_clean = clean_text(barrio_nombre)
    direccion = clean_text(propiedad.get('direccion', ''))
    pdf.cell(0, 8, f"Ubicacion: {barrio_clean} - {direccion}", 0, 1)
    
    pdf.ln(5)
    
    # Características principales
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(90, 10, " Caracteristica", 1, 0, 'L', True)
    pdf.cell(90, 10, " Detalle", 1, 1, 'L', True)
    
    pdf.set_font('helvetica', '', 11)
    m2 = clean_text(f"{propiedad.get('metros_cuadrados', 'N/A')} m2")
    estado = clean_text(str(propiedad.get('estado', 'N/A')).capitalize())
    moneda_exp = clean_text(propiedad.get('moneda_expensas', 'ARS'))
    try:
        exp_val = propiedad.get('expensas', 0)
        exp_str = f"{moneda_exp} {int(exp_val):,}" if exp_val > 0 else "Sin expensas"
    except:
        exp_str = "Consultar"

    caracteristicas = [
        ("Metros Cuadrados", m2),
        ("Ambientes", str(propiedad.get('ambientes', 'N/A'))),
        ("Antiguedad", f"{propiedad.get('antiguedad', 'N/A')} anos"),
        ("Estado", estado),
        ("Expensas", exp_str),
    ]
    
    for label, value in caracteristicas:
        pdf.cell(90, 8, f" {label}", 1)
        pdf.cell(90, 8, f" {value}", 1, 1)
    
    # Comodidades y Servicios
    pdf.ln(5)
    pdf.set_font('helvetica', 'B', 14)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, "Comodidades y Servicios:", 0, 1)
    
    pdf.set_font('helvetica', '', 11)
    pdf.set_text_color(52, 73, 94)
    otros = [
        clean_text(f"Cochera: {propiedad.get('cochera', 'No')}"),
        clean_text(f"Balcon: {propiedad.get('balcon', 'No')}"),
        clean_text(f"Pileta: {propiedad.get('pileta', 'No')}"),
        clean_text(f"Acepta Mascotas: {propiedad.get('acepta_mascotas', 'No')}"),
        clean_text(f"Aire Acondicionado: {propiedad.get('aire_acondicionado', 'No')}"),
        clean_text(f"Amenities: {propiedad.get('amenities', 'No')}")
    ]
    
    for i in range(0, len(otros), 2):
        col1 = otros[i]
        col2 = otros[i+1] if i+1 < len(otros) else ""
        pdf.cell(90, 7, f"- {col1}", 0, 0)
        pdf.cell(90, 7, f"- {col2}", 0, 1)

    # Descripción
    pdf.ln(5)
    pdf.set_font('helvetica', 'B', 14)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, "Descripcion:", 0, 1)
    pdf.set_font('helvetica', '', 11)
    pdf.set_text_color(0)
    descripcion = clean_text(propiedad.get('descripcion', 'Sin descripcion detallada.'))
    pdf.multi_cell(0, 6, descripcion)
    
    # Fotos (Soporte para múltiples fotos)
    fotos = propiedad.get('fotos', [])
    valid_fotos = [f for f in fotos if os.path.exists(f)]
    
    if valid_fotos:
        pdf.add_page()
        pdf.set_font('helvetica', 'B', 16)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 10, "Galeria de Fotos", 0, 1, 'C')
        pdf.ln(5)
        
        # Mostrar hasta 6 fotos, 2 por página o ajustado
        for i, foto_path in enumerate(valid_fotos[:6]):
            try:
                # Si es la 3ra o 5ta foto, podríamos necesitar nueva página o espacio
                if i > 0 and i % 2 == 0:
                    pdf.add_page()
                
                # Calcular posición para centrar un poco
                pdf.image(foto_path, x=15, w=180)
                pdf.ln(5)
            except Exception as e:
                print(f"Error insertando imagen {foto_path}: {e}")

    # Información del Barrio (Entorno)
    if datos_entorno:
        # Buscar el barrio en los datos de entorno (normalizar a minúsculas y sin espacios raros)
        nombre_barrio_lookup = barrio_nombre.lower().strip()
        # Manejo simple de mapeos si es necesario, o buscar coincidencia parcial
        info_barrio = None
        for key in datos_entorno:
            if key in nombre_barrio_lookup or nombre_barrio_lookup in key:
                info_barrio = datos_entorno[key]
                break
        
        if info_barrio:
            pdf.add_page()
            pdf.set_font('helvetica', 'B', 18)
            pdf.set_text_color(44, 62, 80)
            pdf.cell(0, 12, f"Conoce el Barrio: {clean_text(info_barrio.get('nombre', barrio_nombre))}", 0, 1, 'C')
            pdf.ln(5)
            
            # Descripción General del Barrio
            pdf.set_font('helvetica', 'B', 14)
            pdf.cell(0, 10, "Descripcion del Entorno:", 0, 1)
            pdf.set_font('helvetica', '', 11)
            pdf.set_text_color(52, 73, 94)
            desc_barrio = clean_text(info_barrio.get('descripcion_general', ''))
            pdf.multi_cell(0, 6, desc_barrio)
            pdf.ln(5)
            
            # Puntajes
            pdf.set_font('helvetica', 'B', 14)
            pdf.set_text_color(44, 62, 80)
            pdf.cell(0, 10, "Calificaciones del Barrio:", 0, 1)
            
            # Tabla de puntajes
            pdf.set_font('helvetica', 'B', 11)
            pdf.set_fill_color(230, 230, 230)
            pdf.cell(60, 8, " Item", 1, 0, 'L', True)
            pdf.cell(30, 8, " Puntaje", 1, 0, 'C', True)
            pdf.cell(90, 8, " Detalle", 1, 1, 'L', True)
            
            pdf.set_font('helvetica', '', 10)
            items_evaluar = [
                ("Gastronomia", info_barrio.get('gastronomia', {})),
                ("Transporte", info_barrio.get('transporte', {})),
                ("Comercio", info_barrio.get('comercio', {})),
                ("Seguridad", info_barrio.get('seguridad', {})),
                ("Educacion", info_barrio.get('educacion', {})),
                ("Salud", info_barrio.get('salud', {})),
                ("Espacios Verdes", info_barrio.get('espacios_verdes', {})),
            ]
            
            for label, data in items_evaluar:
                score = str(data.get('puntuacion', 'N/A'))
                detalle = clean_text(data.get('descripcion', 'N/A'))
                
                # Check for page break before each row if near bottom
                if pdf.get_y() > 250:
                    pdf.add_page()
                    # Repetir cabecera si se desea, o solo seguir
                
                pdf.cell(60, 8, f" {label}", 1)
                pdf.cell(30, 8, f" {score}/100", 1, 0, 'C')
                # Usar multi_cell para el detalle por si es largo, pero complica la tabla
                # Una alternativa es truncar o usar un alto fijo
                pdf.cell(90, 8, f" {detalle[:45]}...", 1, 1)

            # Conclusión del Barrio
            pdf.ln(10)
            pdf.set_font('helvetica', 'B', 14)
            pdf.cell(0, 10, "Conclusion del Experto:", 0, 1)
            pdf.set_font('helvetica', 'I', 11)
            conclusion = clean_text(info_barrio.get('conclusion', ''))
            pdf.multi_cell(0, 6, conclusion)

    # Footer de contacto final
    pdf.ln(10)
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, "Para mas informacion, contactanos por WhatsApp al +54 9 11 5151-1579", 0, 1, 'C')

    pdf.output(output_path)
    return True

def actualizar_fichas_todas():
    """
    Lee propiedades.json, genera todos los PDFs y actualiza el campo 'documentos'.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path_propiedades = os.path.join(base_dir, 'propiedades.json')
    path_entorno = os.path.join(base_dir, 'entorno.json')
    output_dir = os.path.join(base_dir, 'fichas')
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Cargar datos
    try:
        with open(path_propiedades, 'r', encoding='utf-8') as f:
            propiedades = json.load(f)
    except Exception as e:
        print(f"Error cargando propiedades: {e}")
        return
        
    datos_entorno = None
    if os.path.exists(path_entorno):
        try:
            with open(path_entorno, 'r', encoding='utf-8') as f:
                datos_entorno = json.load(f)
        except Exception as e:
            print(f"Error cargando entorno: {e}")

    # Procesar cada propiedad
    for prop in propiedades:
        id_prop = prop.get('id_temporal', 'SN_ID')
        pdf_filename = f"FICHA_{id_prop}.pdf"
        pdf_path_full = os.path.join(output_dir, pdf_filename)
        pdf_path_relative = f"fichas/{pdf_filename}"
        
        print(f"Generando {pdf_filename}...")
        generar_pdf_propiedad(prop, pdf_path_full, datos_entorno)
        
        # Actualizar campo documentos
        docs = prop.get('documentos', [])
        if pdf_path_relative not in docs:
            # Mantener otros documentos y agregar la ficha al principio
            docs = [pdf_path_relative] + [d for d in docs if "FICHA_" not in d]
            prop['documentos'] = docs

    # Guardar cambios en propiedades.json
    try:
        with open(path_propiedades, 'w', encoding='utf-8') as f:
            json.dump(propiedades, f, indent=2, ensure_ascii=False)
        print("\n✅ Propiedades.json actualizado con éxito.")
    except Exception as e:
        print(f"Error guardando propiedades.json: {e}")

if __name__ == "__main__":
    actualizar_fichas_todas()
