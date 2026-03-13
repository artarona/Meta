import os
import json
from fpdf import FPDF
from datetime import datetime

class PropertyPDF(FPDF):
    def header(self):
        # Logo o Título de la Inmobiliaria
        self.set_font('helvetica', 'B', 15)
        self.set_text_color(44, 62, 80)
        self.cell(0, 10, 'DANTE INMOBILIARIA - Ficha de Propiedad', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()} - Generado el {datetime.now().strftime("%d/%m/%Y")}', 0, 0, 'C')

def generar_pdf_propiedad(propiedad, output_path):
    """
    Genera un PDF profesional para una propiedad.
    propiedad: dict con los datos de la propiedad
    output_path: ruta donde se guardará el PDF
    """
    # Usar 'latin-1' por defecto ya que las fuentes estándar de FPDF solo soportan eso.
    # Reemplazamos caracteres problemáticos.
    def clean_text(text):
        if not text: return ""
        if not isinstance(text, str): text = str(text)
        # Reemplazos comunes
        replacements = {
            '²': '2',
            '•': '-',
            '–': '-',
            '—': '-',
            '’': "'",
            '“': '"',
            '”': '"',
            '…': '...',
            '°': 'o'
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        # Intentar codificar a latin-1 para ver si quedan caracteres raros
        try:
            text.encode('latin-1')
            return text
        except UnicodeEncodeError:
            # Si falla, forzar a latin-1 ignorando errores
            return text.encode('latin-1', 'ignore').decode('latin-1')

    pdf = PropertyPDF()
    pdf.add_page()
    
    # Título y Operación
    pdf.set_font('helvetica', 'B', 20)
    pdf.set_text_color(44, 62, 80)
    titulo = clean_text(propiedad.get('titulo', 'Sin Titulo'))
    pdf.multi_cell(0, 10, titulo, align='L')
    
    operacion = clean_text(propiedad.get('operacion', '').capitalize())
    pdf.set_font('helvetica', 'B', 14)
    pdf.set_text_color(231, 76, 60)
    pdf.cell(0, 10, f"En {operacion}", 0, 1)
    
    pdf.ln(5)
    
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
    barrio = clean_text(propiedad.get('barrio', 'N/A'))
    direccion = clean_text(propiedad.get('direccion', ''))
    pdf.cell(0, 8, f"Ubicacion: {barrio} - {direccion}", 0, 1)
    
    pdf.ln(5)
    
    # Características principales
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(95, 10, " Caracteristica", 1, 0, 'L', True)
    pdf.cell(95, 10, " Detalle", 1, 1, 'L', True)
    
    pdf.set_font('helvetica', '', 11)
    m2 = clean_text(f"{propiedad.get('metros_cuadrados', 'N/A')} m2")
    estado = clean_text(propiedad.get('estado', 'N/A').capitalize())
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
        pdf.cell(95, 8, f" {label}", 1)
        pdf.cell(95, 8, f" {value}", 1, 1)
    
    pdf.ln(10)
    
    # Descripción
    pdf.set_font('helvetica', 'B', 14)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, "Descripcion:", 0, 1)
    pdf.set_font('helvetica', '', 11)
    pdf.set_text_color(0)
    descripcion = clean_text(propiedad.get('descripcion', 'Sin descripcion detallada.'))
    pdf.multi_cell(0, 6, descripcion)
    
    pdf.ln(10)
    
    # Comodidades
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
        pdf.cell(95, 7, f"- {col1}", 0, 0)
        pdf.cell(95, 7, f"- {col2}", 0, 1)
        
    fotos = propiedad.get('fotos', [])
    if fotos:
        pdf.ln(10)
        # Buscar la primera foto que realmente exista
        found_foto = None
        for f in fotos:
            if os.path.exists(f):
                found_foto = f
                break
        
        if found_foto:
            pdf.set_font('helvetica', 'B', 12)
            pdf.cell(0, 10, "Referencia Visual:", 0, 1)
            try:
                # Intentar calcular proporciones para que no se pase de largo
                # fpdf.image hace auto-scaling si solo pones w o h
                pdf.image(found_foto, w=180)
            except Exception as e:
                pass
    
    pdf.ln(5)
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, "Para mas informacion, contactanos por WhatsApp al +54 9 11 5151-1579", 0, 1, 'C')

    pdf.output(output_path)
    return True

if __name__ == "__main__":
    # Prueba rápida
    if os.path.exists('propiedades.json'):
        with open('propiedades.json', 'r', encoding='utf-8') as f:
            props = json.load(f)
            if props:
                os.makedirs('fichas', exist_ok=True)
                generar_pdf_propiedad(props[0], 'fichas/prueba.pdf')
                print("PDF de prueba generado en fichas/prueba.pdf")
