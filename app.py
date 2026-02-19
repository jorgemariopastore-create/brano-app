
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import re

# --- 1. MOTOR DE EXTRACCIÓN DE ALTA PRECISIÓN ---
def extraer_datos_v42(archivo_pdf):
    archivo_pdf.seek(0)
    pdf_bytes = archivo_pdf.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    texto_completo = ""
    for pagina in doc:
        texto_completo += pagina.get_text("text") + "\n"
    
    # Limpiamos el texto de ruidos de tabla para el nombre
    lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]
    
    nombre_det = "NOMBRE NO DETECTADO"
    fecha_det = "13/02/2026"
    
    for i, linea in enumerate(lineas):
        if "Paciente:" in linea:
            # El nombre suele estar en la misma línea o la siguiente
            nombre_det = linea.replace("Paciente:", "").strip()
        if "Fecha de estudio:" in linea:
            fecha_det = lineas[i+1].strip() if i+1 < len(lineas) else "13/02/2026"

    # Buscador de valores en formato de tabla "ETIQUETA","VALOR"
    def buscar_en_comillas(etiqueta, texto):
        # Busca: "DDVI ","40 "
        patron = rf'\"{etiqueta}\s*\"\s*,\s*\"(\d+)'
        match = re.search(patron, texto, re.I)
        return match.group(1) if match else ""

    res = {
        "pac": nombre_det,
        "fec": fecha_det,
        "peso": re.search(r"Peso\s*\(kg\):\s*(\d+\.?\d*)", texto_completo, re.I).group(1) if re.search(r"Peso\s*\(kg\):\s*(\d+\.?\d*)", texto_completo, re.I) else "",
        "alt": re.search(r"Altura\s*\(cm\):\s*(\d+\.?\d*)", texto_completo, re.I).group(1) if re.search(r"Altura\s*\(cm\):\s*(\d+\.?\d*)", texto_completo, re.I) else "",
        "ddvi": buscar_en_comillas("DDVI", texto_completo),
        "dsvi": buscar_en_comillas("DSVI", texto_completo),
        "siv": buscar_en_comillas("DDSIV", texto_completo),
        "pp": buscar_en_comillas("DDPP", texto_completo),
        "fa": buscar_en_comillas("FA", texto_completo)
    }

    fotos = []
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            pix = doc.extract_image(img[0])
            if pix["size"] > 15000:
                fotos.append(io.BytesIO(pix["image"]))
    doc.close()
    return res, fotos

# --- 2. INTERFAZ ---
st.set_page_config(page_title="CardioReport Pastore v42", layout="wide")
st.title("🏥 Asistente de Informes - Dr. Pastore")

archivo = st.file_uploader("Subir PDF del Ecógrafo", type=["pdf"])

if archivo:
    datos, fotos = extraer_datos_v42(archivo)
    
    with st.form("panel_final"):
        st.subheader(f"Paciente: {datos['pac']}")
        
        c1, c2, c3, c4 = st.columns(4)
        v_pac = c1.text_input("Nombre Completo", value=datos['pac'])
        v_fec = c2.text_input("Fecha de Estudio", value=datos['fec'])
        v_peso = c3.text_input("Peso (kg)", value=datos['peso'])
        v_alt = c4.text_input("Altura (cm)", value=datos['alt'])
        
        st.write("---")
        st.markdown("**Valores de Cavidades (Extraídos Automáticamente)**")
        d1, d2, d3, d4, d5 = st.columns(5)
        v_ddvi = d1.text_input("DDVI", value=datos['ddvi'])
        v_dsvi = d2.text_input("DSVI", value=datos['dsvi'])
        v_siv = d3.text_input("SIV", value=datos['siv'])
        v_pp = d4.text_input("PP", value=datos['pp'])
        v_fa = d5.text_input("FA %", value=datos['fa'])
        
        # Botón de proceso
        btn_preparar = st.form_submit_button("✅ GENERAR DOCUMENTO WORD")

    if btn_preparar:
        doc = Document()
        # Formato Senior
        doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        p = doc.add_paragraph()
        p.add_run(f"PACIENTE: {v_pac}").bold = True
        p.add_run(f"\nFECHA: {v_fec} | PESO: {v_peso} kg | ALTURA: {v_alt} cm")
        
        doc.add_heading('VALORES OBTENIDOS', 1)
        doc.add_paragraph(f"DDVI: {v_ddvi} mm | DSVI: {v_dsvi} mm | SIV: {v_siv} mm | PP: {v_pp} mm | FA: {v_fa} %")
        
        doc.add_heading('HALLAZGOS Y CONCLUSIONES', 1)
        doc.add_paragraph("\n\n(Escriba su diagnóstico aquí...)\n\n")

        if fotos:
            doc.add_page_break()
            doc.add_heading('ANEXO DE IMÁGENES', 1)
            tabla = doc.add_table(rows=(len(fotos)+1)//2, cols=2)
            for i, f in enumerate(fotos):
                run = tabla.rows[i//2].cells[i%2].paragraphs[0].add_run()
                run.add_picture(f, width=Inches(3.0))

        buf = io.BytesIO()
        doc.save(buf)
        st.session_state.file_final = buf.getvalue()
        st.session_state.name_final = v_pac

# BOTÓN DE DESCARGA
if "file_final" in st.session_state:
    st.markdown("---")
    st.download_button(f"⬇️ DESCARGAR INFORME: {st.session_state.name_final}", 
                      st.session_state.file_final, 
                      f"Informe_{st.session_state.name_final}.docx")
