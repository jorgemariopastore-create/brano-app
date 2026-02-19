
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import re

# --- 1. MOTOR DE EXTRACCIÓN MEJORADO (BUSCA ENTRE COMILLAS Y TABLAS) ---
def extraer_datos_precisos(archivo_pdf):
    archivo_pdf.seek(0)
    pdf_bytes = archivo_pdf.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    texto_sucio = ""
    for pagina in doc:
        texto_sucio += pagina.get_text()
    
    # Normalizamos el texto quitando saltos de línea extraños
    t = " ".join(texto_sucio.split())
    
    def buscar_dato(etiqueta, cadena):
        # Esta expresión regular busca el dato incluso si tiene comillas o está en tablas
        patron = rf'{etiqueta}\s*\"?,\s*\"?(\d+\.?\d*)'
        m = re.search(patron, cadena, re.I)
        return m.group(1).strip() if m else ""

    # Extracción de Encabezado
    nombre_pac = re.search(r"Paciente:\s*([A-Z\s]+)", t, re.I)
    fecha_est = re.search(r"Fecha de estudio:\s*(\d{{2}}/\d{{2}}/\d{{4}})", t, re.I)
    peso_val = re.search(r"Peso \(kg\):\s*(\d+\.?\d*)", t, re.I)
    alt_val = re.search(r"Altura \(cm\):\s*(\d+\.?\d*)", t, re.I)

    datos = {
        "pac": nombre_pac.group(1).strip() if nombre_pac else "Paciente no detectado",
        "fec": fecha_est.group(1).strip() if fecha_est else "19/02/2026",
        "peso": peso_val.group(1).strip() if peso_val else "",
        "alt": alt_val.group(1).strip() if alt_val else "",
        "ddvi": buscar_dato("DDVI", t),
        "dsvi": buscar_dato("DSVI", t),
        "siv": buscar_dato("DDSIV", t),
        "pp": buscar_dato("DDPP", t),
        "fa": buscar_dato("FA", t)
    }

    fotos = []
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            pix = doc.extract_image(img[0])
            if pix["size"] > 15000:
                fotos.append(io.BytesIO(pix["image"]))
    doc.close()
    return datos, fotos

# --- 2. INTERFAZ Y PROCESAMIENTO ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")

archivo = st.file_uploader("Subir PDF del Ecógrafo", type=["pdf"])

if archivo:
    with st.spinner("Analizando PDF y extrayendo datos técnicos..."):
        datos, fotos = extraer_datos_precisos(archivo)

    # PANEL DE CONTROL PARA EL DOCTOR
    with st.form("validador_informe"):
        st.subheader(f"Datos del Paciente: {datos['pac']}")
        
        c1, c2, c3, c4 = st.columns(4)
        pac_final = c1.text_input("Nombre", value=datos['pac'])
        fec_final = c2.text_input("Fecha", value=datos['fec'])
        peso_final = c3.text_input("Peso (kg)", value=datos['peso'])
        alt_final = c4.text_input("Altura (cm)", value=datos['alt'])
        
        st.write("---")
        st.markdown("**Cavidades y Función Sistólica**")
        d1, d2, d3, d4, d5 = st.columns(5)
        v_ddvi = d1.text_input("DDVI", value=datos['ddvi'])
        v_dsvi = d2.text_input("DSVI", value=datos['dsvi'])
        v_siv = d3.text_input("SIV", value=datos['siv'])
        v_pp = d4.text_input("PP", value=datos['pp'])
        v_fa = d5.text_input("FA %", value=datos['fa'])
        
        generar = st.form_submit_button("🚀 GENERAR INFORME COMPLETO EN WORD")

    # --- 3. GENERACIÓN DEL WORD FINAL (SÓLO SI SE PULSA EL BOTÓN) ---
    if generar:
        doc = Document()
        
        # Formato de Título Profesional
        header = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
        header.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Datos Generales
        p1 = doc.add_paragraph()
        p1.add_run(f"PACIENTE: {pac_final}").bold = True
        p1.add_run(f"\nFECHA: {fec_final} | PESO: {peso_final} kg | ALTURA: {alt_final} cm")
        
        

        # Tabla de Valores
        doc.add_heading('PARÁMETROS OBTENIDOS', 1)
        tabla_vals = doc.add_table(rows=2, cols=5)
        tabla_vals.style = 'Table Grid'
        
        etiquetas = ["DDVI (mm)", "DSVI (mm)", "SIV (mm)", "PP (mm)", "FA (%)"]
        valores = [v_ddvi, v_dsvi, v_siv, v_pp, v_fa]
        
        for i in range(5):
            tabla_vals.cell(0, i).text = etiquetas[i]
            tabla_vals.cell(1, i).text = valores[i]

        # Espacio para la conclusión del Dr.
        doc.add_heading('HALLAZGOS Y CONCLUSIÓN', 1)
        doc.add_paragraph("\n\n(Redacte aquí su conclusión médica final...)\n\n")

        # Anexo de Imágenes en 2 columnas
        if fotos:
            doc.add_page_break()
            doc.add_heading('ANEXO DE IMÁGENES', 1)
            tabla_img = doc.add_table(rows=(len(fotos)+1)//2, cols=2)
            for i, f in enumerate(fotos):
                run = tabla_img.rows[i//2].cells[i%2].paragraphs[0].add_run()
                run.add_picture(f, width=Inches(3.0))

        # Preparar descarga
        buf = io.BytesIO()
        doc.save(buf)
        st.session_state.file_final = buf.getvalue()
        st.session_state.name_final = pac_final

# --- 4. BOTÓN DE DESCARGA (VISIBLE SÓLO CUANDO EL WORD SE GENERÓ) ---
if "file_final" in st.session_state:
    st.markdown("---")
    st.success(f"Informe de {st.session_state.name_final} preparado correctamente.")
    st.download_button(
        label="⬇️ DESCARGAR DOCUMENTO WORD",
        data=st.session_state.file_final,
        file_name=f"Informe_{st.session_state.name_final}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
