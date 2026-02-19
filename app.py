
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import re

# --- 1. MOTOR DE EXTRACCIÓN MEJORADO (DETECTA ALBORNOZ ALICIA) ---
def extraer_datos_v41(archivo_pdf):
    archivo_pdf.seek(0)
    pdf_bytes = archivo_pdf.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    texto_por_paginas = []
    for pagina in doc:
        texto_por_paginas.append(pagina.get_text())
    
    texto_completo = "\n".join(texto_por_paginas)
    # Limpiamos el texto para la búsqueda de patrones
    t_una_linea = " ".join(texto_completo.split())

    # Lógica de búsqueda mejorada para el nombre
    # Busca "Paciente:" y captura hasta encontrar un salto de línea o "Fecha"
    match_nombre = re.search(r"Paciente:\s*([A-ZÁÉÍÓÚÑ\s,]+)(?=Fecha|OSDE|DNI|ID|$)", t_una_linea, re.I)
    match_fecha = re.search(r"Fecha de estudio:\s*(\d{2}/\d{2}/\d{4})", t_una_linea, re.I)
    
    # Biometría
    peso = re.search(r"Peso\s*\(kg\):\s*(\d+\.?\d*)", t_una_linea, re.I)
    altura = re.search(r"Altura\s*\(cm\):\s*(\d+\.?\d*)", t_una_linea, re.I)

    # Función para buscar números en las tablas de "Cavidades"
    def buscar_tabla(label, txt):
        # Busca la etiqueta seguida de comillas y el valor
        patron = rf'\"{label}\"\s*,\s*\"(\d+)\"'
        m = re.search(patron, txt, re.I)
        return m.group(1) if m else ""

    res = {
        "pac": match_nombre.group(1).strip() if match_nombre else "NOMBRE NO DETECTADO",
        "fec": match_fecha.group(1).strip() if match_fecha else "13/02/2026",
        "peso": peso.group(1).strip() if peso else "",
        "alt": altura.group(1).strip() if altura else "",
        "ddvi": buscar_tabla("DDVI", texto_completo),
        "dsvi": buscar_tabla("DSVI", texto_completo),
        "siv": buscar_tabla("DDSIV", texto_completo),
        "pp": buscar_tabla("DDPP", texto_completo),
        "fa": buscar_tabla("FA", texto_completo)
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
st.set_page_config(page_title="CardioReport Pro v41", layout="wide")
st.title("🏥 Asistente Médico Dr. Pastore")

archivo = st.file_uploader("Subir PDF del Ecógrafo", type=["pdf"])

if archivo:
    # Se ejecuta solo al cargar el archivo
    datos, fotos = extraer_datos_v41(archivo)
    
    with st.form("form_v41"):
        st.subheader(f"Paciente detectado: {datos['pac']}")
        
        c1, c2, c3, c4 = st.columns(4)
        v_pac = c1.text_input("Paciente", value=datos['pac'])
        v_fec = c2.text_input("Fecha", value=datos['fec'])
        v_peso = c3.text_input("Peso (kg)", value=datos['peso'])
        v_alt = c4.text_input("Altura (cm)", value=datos['alt'])
        
        st.write("---")
        st.markdown("**Valores de Cavidades**")
        d1, d2, d3, d4, d5 = st.columns(5)
        v_ddvi = d1.text_input("DDVI", value=datos['ddvi'])
        v_dsvi = d2.text_input("DSVI", value=datos['dsvi'])
        v_siv = d3.text_input("SIV", value=datos['siv'])
        v_pp = d4.text_input("PP", value=datos['pp'])
        v_fa = d5.text_input("FA %", value=datos['fa'])
        
        # Este botón ahora fuerza la creación del documento
        btn_generar = st.form_submit_button("✅ GENERAR DOCUMENTO WORD")

    if btn_generar:
        # CONSTRUCCIÓN DEL WORD PROFESIONAL
        doc = Document()
        header = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
        header.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        p = doc.add_paragraph()
        p.add_run(f"PACIENTE: {v_pac}").bold = True
        p.add_run(f"\nFECHA: {v_fec} | PESO: {v_peso} kg | ALTURA: {v_alt} cm")
        
        doc.add_heading('HALLAZGOS Y CONCLUSIÓN', 1)
        doc.add_paragraph(f"DDVI: {v_ddvi} mm | DSVI: {v_dsvi} mm | SIV: {v_siv} mm | PP: {v_pp} mm | FA: {v_fa} %")
        doc.add_paragraph("\n\n(Escriba su diagnóstico aquí...)\n\n")

        if fotos:
            doc.add_page_break()
            doc.add_heading('ANEXO DE IMÁGENES', 1)
            # Grilla de 2 columnas
            tabla = doc.add_table(rows=(len(fotos)+1)//2, cols=2)
            for i, f in enumerate(fotos):
                run = tabla.rows[i//2].cells[i%2].paragraphs[0].add_run()
                run.add_picture(f, width=Inches(3.0))

        buf = io.BytesIO()
        doc.save(buf)
        st.session_state.archivo_final = buf.getvalue()
        st.session_state.nombre_doc = v_pac

# BOTÓN DE DESCARGA (Fuera del formulario)
if "archivo_final" in st.session_state:
    st.markdown("---")
    st.download_button(
        label=f"⬇️ DESCARGAR INFORME DE {st.session_state.nombre_doc}",
        data=st.session_state.archivo_final,
        file_name=f"Informe_{st.session_state.nombre_doc}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
