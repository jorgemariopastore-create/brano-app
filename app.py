
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import re

# --- 1. MOTOR DE EXTRACCIÓN (AJUSTADO AL PDF REAL) ---
def extraer_datos_doctor(archivo_pdf):
    archivo_pdf.seek(0)
    pdf_bytes = archivo_pdf.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    texto = " ".join([p.get_text() for p in doc])
    t = " ".join(texto.split())
    
    def buscar(patron, cadena):
        m = re.search(patron, cadena, re.I)
        return m.group(1).strip() if m else ""

    # Extracción de biometría y cavidades según su PDF
    datos = {
        "pac": buscar(r"Paciente:\s*([A-Z\s,]+)", t),
        "fec": buscar(r"Fecha de estudio:\s*(\d{2}/\d{2}/\d{4})", t),
        "peso": buscar(r"Peso \(kg\):\s*(\d+\.?\d*)", t),
        "alt": buscar(r"Altura \(cm\):\s*(\d+\.?\d*)", t),
        "bsa": buscar(r"BSA\(m\^2\):\s*(\d+\.?\d*)", t),
        "ddvi": buscar(r"DDVI\s*\",\s*\"(\d+)", t),
        "dsvi": buscar(r"DSVI\s*\",\s*\"(\d+)", t),
        "siv": buscar(r"DDSIV\s*\",\s*\"(\d+)", t),
        "pp": buscar(r"DDPP\s*\",\s*\"(\d+)", t),
        "fa": buscar(r"FA\s*\",\s*\"(\d+)", t)
    }

    fotos = []
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            pix = doc.extract_image(img[0])
            if pix["size"] > 15000: fotos.append(io.BytesIO(pix["image"]))
    doc.close()
    return datos, fotos

# --- 2. INTERFAZ ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Sistema de Informes Médicos - Dr. Pastore")

archivo = st.file_uploader("Cargar PDF del Ecógrafo", type=["pdf"])

if archivo:
    datos, fotos = extraer_datos_doctor(archivo)
    
    with st.form("panel_edicion"):
        st.subheader(f"Informe: {datos['pac']}")
        
        # Fila 1: Biometría
        c1, c2, c3, c4 = st.columns(4)
        pac = c1.text_input("Paciente", value=datos['pac'])
        fec = c2.text_input("Fecha", value=datos['fec'])
        peso = c3.text_input("Peso (kg)", value=datos['peso'])
        alt = c4.text_input("Altura (cm)", value=datos['alt'])
        
        # Fila 2: Cavidades
        st.markdown("**Parámetros Ecocardiográficos**")
        d1, d2, d3, d4, d5 = st.columns(5)
        v_ddvi = d1.text_input("DDVI", value=datos['ddvi'])
        v_dsvi = d2.text_input("DSVI", value=datos['dsvi'])
        v_siv = d3.text_input("SIV", value=datos['siv'])
        v_pp = d4.text_input("PP", value=datos['pp'])
        v_fa = d5.text_input("FA %", value=datos['fa'])
        
        st.info("Al generar el Word, el sistema dejará el espacio listo para su diagnóstico.")
        
        if st.form_submit_button("🚀 GENERAR INFORME PROFESIONAL"):
            # CREACIÓN DEL WORD CON ESTILO SENIOR
            doc = Document()
            
            # Encabezado con formato
            title = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            p_head = doc.add_paragraph()
            p_head.add_run(f"PACIENTE: {pac}").bold = True
            p_head.add_run(f"\nFECHA: {fec} | PESO: {peso} kg | ALTURA: {alt} cm")
            
            doc.add_heading('VALORES OBTENIDOS', 1)
            p_vals = doc.add_paragraph()
            p_vals.add_run(f"DDVI: {v_ddvi} mm | DSVI: {v_dsvi} mm | SIV: {v_siv} mm | PP: {v_pp} mm | FA: {v_fa} %")
            
            # ESPACIO PARA EL DOCTOR (SIN SUGERENCIAS)
            doc.add_heading('HALLAZGOS Y CONCLUSIONES', 1)
            p_conc = doc.add_paragraph("\n\n(Escriba aquí su conclusión médica...)\n\n")
            p_conc.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            
            # GRILLA DE IMÁGENES 2xN
            if fotos:
                doc.add_page_break()
                doc.add_heading('ANEXO DE IMÁGENES', 1)
                tabla = doc.add_table(rows=(len(fotos)+1)//2, cols=2)
                for i, f in enumerate(fotos):
                    run = tabla.rows[i//2].cells[i%2].paragraphs[0].add_run()
                    run.add_picture(f, width=Inches(3.0))
            
            buf = io.BytesIO()
            doc.save(buf)
            st.session_state.ready_file = buf.getvalue()
            st.session_state.ready_name = pac

# Botón de descarga independiente
if "ready_file" in st.session_state:
    st.download_button(f"⬇️ DESCARGAR INFORME {st.session_state.ready_name}", 
                      st.session_state.ready_file, 
                      f"Informe_{st.session_state.ready_name}.docx")
