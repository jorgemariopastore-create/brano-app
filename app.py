
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import re

# --- 1. MOTOR DE EXTRACCIÓN MEJORADO ---
def extraer_datos_finales(archivo_pdf):
    archivo_pdf.seek(0)
    pdf_bytes = archivo_pdf.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    texto_completo = ""
    for pagina in doc:
        texto_completo += pagina.get_text()
    
    # Limpieza de texto para evitar errores de saltos de línea
    t = " ".join(texto_completo.split())
    
    def buscar_en_tabla(etiqueta, cadena):
        # Busca la etiqueta y el número que le sigue entre comillas y comas
        patron = rf'\"{etiqueta}\n?\"\s*,\s*\"?(\d+)\"?'
        m = re.search(patron, cadena, re.I)
        return m.group(1).strip() if m else ""

    # Extracción de Datos de Cabecera
    nombre = re.search(r"Paciente:\s*([A-Z\s,]+)(?=Fecha|OSDE|$)", t, re.I)
    fecha = re.search(r"Fecha de estudio:\s*(\d{2}/\d{2}/\d{4})", t, re.I)
    peso = re.search(r"Peso \(kg\):\s*(\d+\.?\d*)", t, re.I)
    altura = re.search(r"Altura \(cm\):\s*(\d+\.?\d*)", t, re.I)

    res = {
        "pac": nombre.group(1).strip() if nombre else "No detectado",
        "fec": fecha.group(1).strip() if fecha else "19/02/2026",
        "peso": peso.group(1).strip() if peso else "",
        "alt": altura.group(1).strip() if altura else "",
        "ddvi": buscar_en_tabla("DDVI", texto_completo),
        "dsvi": buscar_en_tabla("DSVI", texto_completo),
        "siv": buscar_en_tabla("DDSIV", texto_completo),
        "pp": buscar_en_tabla("DDPP", texto_completo),
        "fa": buscar_en_tabla("FA", texto_completo)
    }

    fotos = []
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            pix = doc.extract_image(img[0])
            if pix["size"] > 15000: fotos.append(io.BytesIO(pix["image"]))
    doc.close()
    return res, fotos

# --- 2. INTERFAZ ---
st.set_page_config(page_title="CardioReport Pastore v39", layout="wide")
st.title("🏥 Sistema de Informes - Dr. Pastore")

archivo = st.file_uploader("Cargue el PDF de su ecógrafo", type=["pdf"])

if archivo:
    # Procesamiento inmediato al cargar
    datos, fotos = extraer_datos_finales(archivo)
    
    with st.form("validador"):
        st.subheader(f"Datos del Estudio: {datos['pac']}")
        c1, c2, c3, c4 = st.columns(4)
        v_pac = c1.text_input("Paciente", value=datos['pac'])
        v_fec = c2.text_input("Fecha Informe", value=datos['fec'])
        v_peso = c3.text_input("Peso (kg)", value=datos['peso'])
        v_alt = c4.text_input("Altura (cm)", value=datos['alt'])
        
        st.write("---")
        st.markdown("**Cavidades y Función**")
        d1, d2, d3, d4, d5 = st.columns(5)
        v_ddvi = d1.text_input("DDVI", value=datos['ddvi'])
        v_dsvi = d2.text_input("DSVI", value=datos['dsvi'])
        v_siv = d3.text_input("SIV", value=datos['siv'])
        v_pp = d4.text_input("PP", value=datos['pp'])
        v_fa = d5.text_input("FA %", value=datos['fa'])
        
        generar = st.form_submit_button("🚀 GENERAR INFORME WORD")

    if generar:
        # CONSTRUCCIÓN DEL DOCUMENTO
        doc = Document()
        doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        p = doc.add_paragraph()
        p.add_run(f"PACIENTE: {v_pac}").bold = True
        p.add_run(f"\nFECHA: {v_fec} | PESO: {v_peso} kg | ALTURA: {v_alt} cm")
        
        doc.add_heading('VALORES TÉCNICOS', 1)
        doc.add_paragraph(f"DDVI: {v_ddvi} mm | DSVI: {v_dsvi} mm | SIV: {v_siv} mm | PP: {v_pp} mm | FA: {v_fa} %")
        
        doc.add_heading('CONCLUSIÓN Y DIAGNÓSTICO', 1)
        doc.add_paragraph("\n\n(Escriba su conclusión médica aquí...)\n\n")

        if fotos:
            doc.add_page_break()
            doc.add_heading('ANEXO DE IMÁGENES', 1)
            tabla = doc.add_table(rows=(len(fotos)+1)//2, cols=2)
            for i, f in enumerate(fotos):
                run = tabla.rows[i//2].cells[i%2].paragraphs[0].add_run()
                run.add_picture(f, width=Inches(3.0))

        # Descarga
        target = io.BytesIO()
        doc.save(target)
        st.session_state.informe = target.getvalue()
        st.session_state.nombre = v_pac

if "informe" in st.session_state:
    st.markdown("---")
    st.download_button(f"⬇️ DESCARGAR INFORME: {st.session_state.nombre}", 
                      st.session_state.informe, 
                      f"Informe_{st.session_state.nombre}.docx")
