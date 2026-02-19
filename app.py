
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
import io

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CardioReport Senior", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")

# --- 2. MOTOR DE IMÁGENES ---
def extraer_imagenes(archivo_objeto):
    try:
        archivo_objeto.seek(0)
        doc = fitz.open(stream=archivo_objeto.read(), filetype="pdf")
        imgs = []
        for i in range(len(doc)):
            for img in doc.get_page_images(i):
                xref = img[0]
                base_image = doc.extract_image(xref)
                imgs.append(io.BytesIO(base_image["image"]))
        return imgs
    except:
        return []

# --- 3. INTERFAZ ---
with st.sidebar:
    st.header("Carga de Estudio")
    archivo_pdf = st.file_uploader("Subir PDF para imágenes", type=["pdf"])

# Inicializamos el Word en la memoria de la sesión
if "word_file" not in st.session_state:
    st.session_state.word_file = None
if "nombre_paciente" not in st.session_state:
    st.session_state.nombre_paciente = "Informe"

# --- 4. FORMULARIO (SOLO PARA DATOS) ---
with st.form("datos_informe"):
    st.subheader("Datos del Informe")
    c1, c2 = st.columns([3, 1])
    pac = c1.text_input("Paciente", value="ALBORNOZ ALICIA")
    fec = c2.text_input("Fecha", value="13/02/2026")
    
    st.markdown("---")
    c3, c4, c5, c6, c7 = st.columns(5)
    ddvi = c3.text_input("DDVI", value="40")
    dsvi = c4.text_input("DSVI", value="25")
    siv = c5.text_input("SIV", value="11")
    pp = c6.text_input("PP", value="10")
    fey = c7.text_input("FEy %", value="67")
    
    # El botón del formulario SOLO procesa, no descarga
    procesar = st.form_submit_button("🚀 PROCESAR INFORME Y EXTRAER IMÁGENES")

# --- 5. LÓGICA DE PROCESAMIENTO (FUERA DEL FORMULARIO) ---
if procesar:
    with st.spinner("Generando documento profesional..."):
        # A. Crear Word
        doc = Document()
        doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
        doc.add_paragraph(f"Paciente: {pac}   |   Fecha: {fec}")
        
        # B. Simular texto profesional (Aquí iría su lógica de Groq)
        texto_medico = f"Se observa DDVI de {ddvi}mm, con espesores de {siv}mm. FEy conservada de {fey}%."
        p = doc.add_paragraph(texto_medico)
        p.alignment = 3 # Justificado
        
        # C. Agregar Imágenes si existen
        if archivo_pdf:
            doc.add_page_break()
            doc.add_heading('ANEXO DE IMÁGENES', 1)
            lista_imgs = extraer_imagenes(archivo_pdf)
            for im in lista_imgs:
                doc.add_picture(im, width=Inches(3.5))
        
        # D. Guardar en memoria de sesión
        buffer = io.BytesIO()
        doc.save(buffer)
        st.session_state.word_file = buffer.getvalue()
        st.session_state.nombre_paciente = pac
        st.success("✅ Informe listo para descargar")

# --- 6. BOTÓN DE DESCARGA (FUERA DEL FORMULARIO) ---
if st.session_state.word_file:
    st.download_button(
        label="⬇️ DESCARGAR INFORME EN WORD",
        data=st.session_state.word_file,
        file_name=f"Informe_{st.session_state.nombre_paciente}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
