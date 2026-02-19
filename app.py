
import streamlit as st
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
import io
import hashlib

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")

# --- 2. FUNCIONES TÉCNICAS (FUERA DE LA VISTA) ---
def limpiar_y_extraer(archivo_pdf):
    # Rebobinar el archivo para lectura fresca
    archivo_pdf.seek(0)
    pdf_bytes = archivo_pdf.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    # Extraer texto para intentar detectar nombre y datos
    texto_completo = " ".join([pag.get_text() for pag in doc])
    
    # Extraer solo imágenes de diagnóstico (evita logos)
    fotos = []
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            xref = img[0]
            pix = doc.extract_image(xref)
            if pix["size"] > 15000: # Solo fotos reales del ecógrafo
                fotos.append(io.BytesIO(pix["image"]))
    doc.close()
    return texto_completo, fotos

# --- 3. LÓGICA DE CONTROL DE ESTADO (EVITA PANTALLA EN BLANCO) ---
if "estudio_activo" not in st.session_state:
    st.session_state.estudio_activo = {"texto": "", "fotos": [], "id": None}

st.title("🏥 Sistema de Informes Dr. Pastore")

# --- 4. BARRA LATERAL: CARGA Y LIMPIEZA ---
with st.sidebar:
    st.header("Entrada de Estudio")
    archivo = st.file_uploader("Subir PDF del Ecógrafo", type=["pdf"])
    
    if archivo:
        id_actual = hashlib.md5(archivo.getvalue()).hexdigest()
        # Si el archivo cambia, reseteamos la memoria de la app al instante
        if st.session_state.estudio_activo["id"] != id_actual:
            txt, imgs = limpiar_y_extraer(archivo)
            st.session_state.estudio_activo = {"texto": txt, "fotos": imgs, "id": id_actual}
            st.rerun()

    if st.button("🗑️ Limpiar Todo"):
        st.session_state.estudio_activo = {"texto": "", "fotos": [], "id": None}
        st.rerun()

# --- 5. CUERPO DE LA APP (SOLO SI HAY ARCHIVO) ---
if st.session_state.estudio_activo["id"]:
    with st.form("formulario_medico"):
        st.subheader("Validación de Datos")
        
        # El médico completa lo fundamental
        c1, c2 = st.columns([3, 1])
        nombre = c1.text_input("Paciente", placeholder="Nombre del Paciente")
        fecha = c2.text_input("Fecha", value="19/02/2026")
        
        st.markdown("### Parámetros Técnicos")
        
        
        col1, col2, col3, col4, col5 = st.columns(5)
        ddvi = col1.text_input("DDVI")
        dsvi = col2.text_input("DSVI")
        siv = col3.text_input("SIV")
        pp = col4.text_input("PP")
        fey = col5.text_input("FEy %")
        
        generar = st.form_submit_button("🚀 GENERAR WORD (GRILLA 2x4)")

    if generar:
        # CREACIÓN DEL WORD CON GRILLA DE 2 COLUMNAS
        doc_word = Document()
        doc_word.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
        doc_word.add_paragraph(f"Paciente: {nombre} | Fecha: {fecha}")
        
        # Texto del informe (Estilo Dr. Pastore)
        p = doc_word.add_paragraph(f"Se realiza estudio encontrando DDVI de {ddvi}mm y FEy de {fey}%.")
        p.alignment = 3 # Justificado
        
        # ANEXO CON IMÁGENES EN COLUMNAS
        if st.session_state.estudio_activo["fotos"]:
            doc_word.add_page_break()
            doc_word.add_heading('ANEXO DE IMÁGENES', 1)
            
            fotos = st.session_state.estudio_activo["fotos"]
            tabla = doc_word.add_table(rows=(len(fotos) + 1) // 2, cols=2)
            
            for i, foto_data in enumerate(fotos):
                fila = i // 2
                col = i % 2
                celda = tabla.rows[fila].cells[col]
                parrafo = celda.paragraphs[0]
                run = parrafo.add_run()
                run.add_picture(foto_data, width=Inches(3.0)) # 2 por fila

        # Descarga del archivo
        buf = io.BytesIO()
        doc_word.save(buf)
        st.download_button("⬇️ DESCARGAR INFORME", buf.getvalue(), f"Informe_{nombre}.docx")

else:
    st.info("👋 Dr. Pastore: Por favor, cargue un archivo PDF para comenzar.")
