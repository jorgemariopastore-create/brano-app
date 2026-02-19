
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re
import io
from docx import Document
from docx.shared import Inches

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")

try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_KEY = None

def extraer_datos_pdf(doc_pdf):
    # Unimos todo el texto y limpiamos ruidos de tablas
    texto_sucio = ""
    for pagina in doc_pdf:
        texto_sucio += pagina.get_text()
    
    # Limpieza profunda para que DDVI","40" se lea como DDVI 40
    t = texto_sucio.replace('"', '').replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')
    
    datos = {"pac": "NO DETECTADO", "dv": "", "si": "", "fy": ""}
    
    # 1. Nombre (Patrón: Paciente: NOMBRE)
    m_pac = re.search(r"Paciente:\s*([A-Z\s]+?)(?:\s*Fecha|\s*Estudio|$)", t, re.I)
    if m_pac: datos["pac"] = m_pac.group(1).strip()

    # 2. Mediciones (Buscamos la etiqueta y el primer número que sigue)
    m_dv = re.search(r"DDVI\s*(\d+)", t)
    m_si = re.search(r"(?:DDSIV|SIV)\s*(\d+)", t)
    
    if m_dv: datos["dv"] = m_dv.group(1)
    if m_si: datos["si"] = m_si.group(1)
    
    # 3. Función Sistólica (Prioriza FEy sobre FA)
    m_fey = re.search(r"eyección del VI\s*(\d+)", t)
    if m_fey:
        datos["fy"] = m_fey.group(1)
    else:
        m_fa = re.search(r"FA\s*(\d+)", t)
        if m_fa: datos["fy"] = str(round(float(m_fa.group(1)) * 1.76))

    return datos

def generar_word(datos, informe_ia, doc_pdf):
    doc = Document()
    doc.add_heading("INFORME ECOCARDIOGRÁFICO", 0)
    doc.add_paragraph(f"PACIENTE: {datos['pac']}")
    doc.add_paragraph("-" * 30)
    doc.add_paragraph(informe_ia)
    doc.add_paragraph("\nDr. Francisco A. Pastore")
    
    # Anexo de Imágenes (4 filas x 2 columnas)
    doc.add_page_break()
    doc.add_heading("ANEXO DE IMÁGENES", level=1)
    
    imagenes = []
    for i in range(len(doc_pdf)):
        for img in doc_pdf[i].get_images(full=True):
            xref = img[0]
            base_image = doc_pdf.extract_image(xref)
            imagenes.append(base_image["image"])

    if imagenes:
        tabla = doc.add_table(rows=4, cols=2)
        for idx, img_data in enumerate(imagenes[:8]): # Tope de 8 imágenes
            row, col = idx // 2, idx % 2
            paragraph = tabla.rows[row].cells[col].paragraphs[0]
            run = paragraph.add_run()
            run.add_picture(io.BytesIO(img_data), width=Inches(2.8))
            
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- INTERFAZ ---
st.title("🏥 Sistema de Informes Dr. Pastore")

if "finalizado" not in st.session_state:
    st.session_state.finalizado = False
    st.session_state.informe_txt = ""
    st.session_state.word_data = None

with st.sidebar:
    archivo = st.file_uploader("Subir PDF", type=["pdf"])
    if st.button("Limpiar"):
        st.session_state.clear()
        st.rerun()

if archivo and GROQ_KEY:
    doc_pdf = fitz.open(stream=archivo.read(), filetype="pdf")
    datos = extraer_datos_pdf(doc_pdf)

    # FORMULARIO
    with st.form("validador"):
        st.subheader("🔍 Validar Datos")
        c1, c2, c3, c4 = st.columns(4)
        pac = c1.text_input("Paciente", datos["pac"])
        fey = c2.text_input("FEy %", datos["fy"])
        ddvi = c3.text_input("DDVI mm", datos["dv"])
        siv = c4.text_input("SIV mm", datos["si"])
        
        btn = st.form_submit_button("🚀 PROCESAR INFORME")

    if btn:
        client = Groq(api_key=GROQ_KEY)
        # Prompt Estricto: Estilo Pastore (Sin verso)
        prompt = (f"Actúa como el Dr. Pastore. Redacta el informe médico. "
                  f"Paciente: {pac}. Hallazgos: DDVI {ddvi}mm, SIV {siv}mm, FEy {fey}%. "
                  f"ESTILO: Muy concreto, estrictamente numérico y clínico. Sin recomendaciones. "
                  f"Sin saludos. Sin verso.")
        
        res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
        st.session_state.informe_txt = res.choices[0].message.content
        st.session_state.word_data = generar_word({"pac":pac, "fy":fey, "dv":ddvi, "si":siv}, st.session_state.informe_txt, doc_pdf)
        st.session_state.finalizado = True

    # RESULTADOS FUERA DEL FORMULARIO (Evita el error de Streamlit)
    if st.session_state.finalizado:
        st.markdown("---")
        st.info(st.session_state.informe_txt)
        st.download_button(
            label="📥 DESCARGAR INFORME (WORD + IMÁGENES)",
            data=st.session_state.word_data,
            file_name=f"Informe_{pac}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
