
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import re

# --- 1. MOTOR DE EXTRACCIÓN AVANZADO (PDF -> DATOS) ---
def extraer_datos_completos(archivo_pdf):
    archivo_pdf.seek(0)
    pdf_bytes = archivo_pdf.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    texto = " ".join([p.get_text() for p in doc])
    t = " ".join(texto.split())
    
    # Mapeo de datos (Basado en el PDF ALBORNOZ ALICIA)
    def buscar(patron, cadena):
        m = re.search(patron, cadena, re.I)
        return m.group(1).strip() if m else ""

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

# --- 2. GENERADOR DE REDACCIÓN MÉDICA ---
def redactar_hallazgos(d):
    # Lógica para redactar según valores extraídos
    texto = f"Ventrículo izquierdo con diámetro diastólico de {d['ddvi']} mm y sistólico de {d['dsvi']} mm. "
    texto += f"Espesores parietales (SIV: {d['siv']} mm, PP: {d['pp']} mm) dentro de límites normales. "
    texto += f"Función sistólica conservada con Fracción de Acortamiento del {d['fa']}%. "
    texto += "Motilidad parietal global y segmentaria conservada en reposo."
    return texto

# --- 3. INTERFAZ ---
st.title("🏥 Sistema de Informes Senior - Dr. Pastore")

archivo = st.file_uploader("Subir PDF del Ecógrafo", type=["pdf"])

if archivo:
    datos, fotos = extraer_datos_completos(archivo)
    
    with st.form("panel_medico"):
        st.subheader(f"Paciente: {datos['pac']}")
        c1, c2, c3 = st.columns(3)
        peso = c1.text_input("Peso (kg)", value=datos["peso"])
        alt = c2.text_input("Altura (cm)", value=datos["alt"])
        bsa = c3.text_input("BSA (m2)", value=datos["bsa"])
        
        st.markdown("---")
        # El médico solo valida lo que ya se leyó
        col1, col2, col3, col4, col5 = st.columns(5)
        v_ddvi = col1.text_input("DDVI", value=datos["ddvi"])
        v_dsvi = col2.text_input("DSVI", value=datos["dsvi"])
        v_siv = col3.text_input("SIV", value=datos["siv"])
        v_pp = col4.text_input("PP", value=datos["pp"])
        v_fa = col5.text_input("FA %", value=datos["fa"])
        
        hallazgos_ia = redactar_hallazgos(datos)
        conclusión = st.text_area("Informe Sugerido (Editable)", value=hallazgos_ia, height=150)
        
        if st.form_submit_button("🚀 GENERAR INFORME PROFESIONAL"):
            doc = Document()
            # Encabezado Médico
            header = doc.add_paragraph()
            header.add_run(f"PACIENTE: {datos['pac']}\n").bold = True
            header.add_run(f"PESO: {peso} kg | ALTURA: {alt} cm | BSA: {bsa} m2\n")
            header.add_run(f"FECHA: {datos['fec']}\n")
            
            # Hallazgos
            doc.add_heading('ECOCARDIOGRAMA 2D Y DOPPLER COLOR', 1)
            p = doc.add_paragraph(conclusión)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            
            # Grilla de Imágenes
            if fotos:
                doc.add_page_break()
                tabla = doc.add_table(rows=(len(fotos)+1)//2, cols=2)
                for i, f in enumerate(fotos):
                    run = tabla.rows[i//2].cells[i%2].paragraphs[0].add_run()
                    run.add_picture(f, width=Inches(3.0))
            
            buf = io.BytesIO()
            doc.save(buf)
            st.session_state.file = buf.getvalue()
            st.session_state.name = datos['pac']

if "file" in st.session_state:
    st.download_button(f"⬇️ DESCARGAR INFORME {st.session_state.name}", st.session_state.file, f"Informe_{st.session_state.name}.docx")
