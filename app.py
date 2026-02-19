
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re
import io
from docx import Document
from docx.shared import Inches

# Configuración de la API
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_KEY = None

def extraer_datos_pdf(doc_pdf):
    # Extraemos y limpiamos el texto de todas las páginas
    texto_sucio = ""
    for pagina in doc_pdf:
        texto_sucio += pagina.get_text()
    
    # Limpieza total para que las tablas no rompan la búsqueda
    t = texto_sucio.replace('"', '').replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')
    
    datos = {"pac": "NO DETECTADO", "dv": "", "si": "", "fy": ""}
    
    # 1. Nombre del Paciente
    m_pac = re.search(r"Paciente:\s*([A-Z\s]+?)(?:\s*Fecha|$)", t, re.I)
    if m_pac: datos["pac"] = m_pac.group(1).strip()

    # 2. Datos de la Tabla (DDVI y SIV)
    m_dv = re.search(r"DDVI\s*(\d+)", t)
    m_si = re.search(r"DDSIV\s*(\d+)", t)
    
    if m_dv: datos["dv"] = m_dv.group(1)
    if m_si: datos["si"] = m_si.group(1)
    
    # 3. Fracción de Eyección (Prioriza el texto del Dr. Pastore)
    m_fe = re.search(r"eyección del VI\s*(\d+)", t)
    if m_fe: 
        datos["fy"] = m_fe.group(1)
    else:
        # Si no está la FE, busca la FA (Fracción de Acortamiento)
        m_fa = re.search(r"FA\s*(\d+)", t)
        if m_fa: datos["fy"] = str(round(float(m_fa.group(1)) * 1.76))

    return datos

def crear_word(datos, informe_ia, doc_pdf):
    doc = Document()
    doc.add_heading(f"INFORME ECOCARDIOGRÁFICO", 0)
    doc.add_paragraph(f"PACIENTE: {datos['pac']}")
    doc.add_paragraph("-" * 30)
    
    # Cuerpo del informe
    doc.add_paragraph(informe_ia)
    doc.add_paragraph("\nDr. Francisco A. Pastore")
    
    # ANEXO DE IMÁGENES (4 filas x 2 columnas)
    doc.add_page_break()
    doc.add_heading("ANEXO DE IMÁGENES", level=1)
    
    # Extraer imágenes del PDF (de las páginas 3 en adelante)
    imgs_bytes = []
    for i in range(2, len(doc_pdf)): # Páginas 3, 4, 5...
        for img in doc_pdf[i].get_images(full=True):
            xref = img[0]
            base_image = doc_pdf.extract_image(xref)
            imgs_bytes.append(base_image["image"])

    if imgs_bytes:
        tabla = doc.add_table(rows=4, cols=2)
        for idx, img_data in enumerate(imgs_bytes[:8]): # Máximo 8 imágenes
            fila = idx // 2
            col = idx % 2
            parrafo = tabla.rows[fila].cells[col].paragraphs[0]
            run = parrafo.add_run()
            run.add_picture(io.BytesIO(img_data), width=Inches(3.0))
            
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="CardioReport Dr. Pastore", layout="wide")
st.title("🏥 Sistema de Informes (Solo PDF)")

with st.sidebar:
    st.header("Carga de Estudio")
    archivo = st.file_uploader("Subir PDF", type=["pdf"])
    if st.button("🔄 Reiniciar"):
        st.session_state.clear()
        st.rerun()

if archivo and GROQ_KEY:
    if "finalizado" not in st.session_state:
        pdf = fitz.open(stream=archivo.read(), filetype="pdf")
        st.session_state.pdf_obj = pdf
        st.session_state.datos = extraer_datos_pdf(pdf)
        st.session_state.finalizado = True

    # FORMULARIO DE VALIDACIÓN
    with st.form("confirmar"):
        st.subheader("🔍 Confirmación de Datos")
        c1, c2, c3, c4 = st.columns(4)
        pac = c1.text_input("Paciente", st.session_state.datos["pac"])
        fey = c2.text_input("FEy %", st.session_state.datos["fy"])
        ddvi = c3.text_input("DDVI mm", st.session_state.datos["dv"])
        siv = c4.text_input("SIV mm", st.session_state.datos["si"])
        
        if st.form_submit_button("🚀 GENERAR INFORME Y WORD"):
            client = Groq(api_key=GROQ_KEY)
            # Prompt para estilo directo Dr. Pastore
            prompt = (f"Genera un informe médico ecocardiográfico para el Dr. Pastore. "
                     f"Paciente: {pac}. Hallazgos: DDVI {ddvi}mm, SIV {siv}mm, FEy {fey}%. "
                     f"Estilo: Muy concreto, puramente numérico y clínico, sin introducciones, "
                     f"sin recomendaciones preventivas y sin 'verso'.")
            
            res = client.chat.completions.create(model='llama-3.3-70b-versatile', 
                                               messages=[{'role':'user','content':prompt}])
            texto_informe = res.choices[0].message.content
            
            st.markdown("---")
            st.subheader("Informe Sugerido")
            st.write(texto_informe)
            
            # Botón de Descarga
            word_data = crear_word(st.session_state.datos, texto_informe, st.session_state.pdf_obj)
            st.download_button(label="📥 DESCARGAR INFORME (WORD + IMÁGENES)",
                             data=word_data,
                             file_name=f"Informe_{pac}.docx",
                             mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
