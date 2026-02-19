
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
import io
import hashlib

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="CardioReport Senior", layout="wide")
st.title("🏥 Sistema de Informes Dr. Pastore")

# --- 2. MOTOR DE IMÁGENES CON PURGA DE MEMORIA ---
def extraer_imagenes_seguro(archivo_objeto):
    try:
        # Rebobinamos el archivo para asegurar lectura fresca
        archivo_objeto.seek(0)
        doc = fitz.open(stream=archivo_objeto.read(), filetype="pdf")
        imgs = []
        for i in range(len(doc)):
            # Solo extraemos imágenes grandes (evitamos iconos o logos del software)
            for img in doc.get_page_images(i):
                xref = img[0]
                base_image = doc.extract_image(xref)
                # Filtro senior: solo imágenes de más de 10kb (capturas reales)
                if len(base_image["image"]) > 10000:
                    imgs.append(io.BytesIO(base_image["image"]))
        return imgs
    except:
        return []

# --- 3. GESTIÓN DE SESIÓN Y CAMBIO DE PACIENTE ---
# Si no existe el ID del archivo o el nombre, los inicializamos
if "file_id" not in st.session_state: st.session_state.file_id = None
if "word_file" not in st.session_state: st.session_state.word_file = None

with st.sidebar:
    st.header("Estudio del Paciente")
    archivo_pdf = st.file_uploader("Subir PDF del Ecógrafo", type=["pdf"])
    
    # DETECCIÓN DE CAMBIO DE PACIENTE
    if archivo_pdf:
        # Creamos una huella digital única (Hash MD5) del contenido
        nuevo_id = hashlib.md5(archivo_pdf.getvalue()).hexdigest()
        
        # SI EL ARCHIVO ES DIFERENTE AL ANTERIOR: BORRAMOS TODO
        if st.session_state.file_id != nuevo_id:
            st.session_state.file_id = nuevo_id
            st.session_state.word_file = None  # Borramos el Word del paciente anterior
            st.session_state.listo_para_descargar = False
            # Opcional: st.rerun() para limpiar la interfaz visualmente

# --- 4. FORMULARIO DE DATOS MÍNIMOS ---
with st.form("datos_informe"):
    st.subheader("Validación Médica")
    c1, c2 = st.columns([3, 1])
    pac = c1.text_input("Paciente", value="", placeholder="Nombre del nuevo paciente")
    fec = c2.text_input("Fecha", value="19/02/2026")
    
    st.markdown("---")
    c3, c4, c5, c6, c7 = st.columns(5)
    ddvi = c3.text_input("DDVI", value="")
    dsvi = c4.text_input("DSVI", value="")
    siv = c5.text_input("SIV", value="")
    pp = c6.text_input("PP", value="")
    fey = c7.text_input("FEy %", value="")
    
    procesar = st.form_submit_button("🚀 GENERAR INFORME Y ANEXAR IMÁGENES")

# --- 5. GENERACIÓN DEL DOCUMENTO ---
if procesar:
    if not archivo_pdf:
        st.error("⚠️ Error: Debe subir el PDF para poder extraer las imágenes correspondientes.")
    else:
        with st.spinner("Vinculando imágenes del estudio actual..."):
            doc = Document()
            # ... (Aquí va toda la lógica de estilo Arial 12 y Justificado) ...
            doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
            doc.add_paragraph(f"Paciente: {pac} | Fecha: {fec}")
            
            # Texto Médico (IA o Manual)
            p = doc.add_paragraph(f"Se realiza estudio encontrando DDVI de {ddvi}mm y FEy de {fey}%.")
            p.alignment = 3 # Justificado
            
            # Extracción e inserción de imágenes NUEVAS
            doc.add_page_break()
            doc.add_heading('ANEXO DE IMÁGENES DEL ESTUDIO', 1)
            
            nuevas_imgs = extraer_imagenes_seguro(archivo_pdf)
            for im in nuevas_imgs:
                doc.add_picture(im, width=Inches(3.5))
            
            # Guardamos el resultado en la sesión
            buffer = io.BytesIO()
            doc.save(buffer)
            st.session_state.word_file = buffer.getvalue()
            st.session_state.nombre_doc = pac
            st.session_state.listo_para_descargar = True

# --- 6. DESCARGA SEGURA ---
if st.session_state.get("listo_para_descargar"):
    st.success(f"✅ Informe de {st.session_state.nombre_doc} generado con sus imágenes.")
    st.download_button(
        label="⬇️ DESCARGAR WORD",
        data=st.session_state.word_file,
        file_name=f"Informe_{st.session_state.nombre_doc}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
