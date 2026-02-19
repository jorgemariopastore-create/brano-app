
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re
import io
from docx import Document
from docx.shared import Inches

# Configuración de página
st.set_page_config(page_title="CardioReport Pro", layout="wide")

try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_KEY = None

def extraccion_forzada_sonoscape(doc_pdf):
    # Unificamos el texto de las primeras 2 páginas (donde están los datos)
    texto_bruto = ""
    for i in range(min(2, len(doc_pdf))):
        texto_bruto += doc_pdf[i].get_text()
    
    # LIMPIEZA CRÍTICA: Quitamos comillas, comas y saltos de línea para que el texto sea lineal
    t = texto_bruto.replace('"', '').replace('\n', ' ').replace('\r', ' ').replace(',', ' ')
    
    datos = {"pac": "NO DETECTADO", "dv": "", "si": "", "fy": ""}
    
    # 1. Búsqueda de Paciente (Patrón específico del PDF de Alicia)
    m_pac = re.search(r"Paciente:\s*([A-Z\s]+?)(?:\s*Fecha|$)", t, re.I)
    if m_pac:
        datos["pac"] = m_pac.group(1).strip()

    # 2. Mediciones: Buscamos la sigla y capturamos el PRIMER número que aparezca después
    # El SonoScape pone DDVI 40 mm, buscamos el 40.
    m_dv = re.search(r"DDVI\s+(\d+)", t)
    m_si = re.search(r"(?:DDSIV|SIV)\s+(\d+)", t)
    
    if m_dv: datos["dv"] = m_dv.group(1)
    if m_si: datos["si"] = m_si.group(1)
    
    # 3. Fracción de Eyección: Priorizamos la frase redactada por el Dr. Pastore
    m_fey = re.search(r"eyección del VI\s*(\d+)", t)
    if m_fey:
        datos["fy"] = m_fey.group(1)
    else:
        # Si no está escrita, buscamos la FA (Fracción de acortamiento)
        m_fa = re.search(r"FA\s+(\d+)", t)
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
    # Buscamos imágenes en todas las páginas (especialmente de la 3 en adelante)
    for i in range(len(doc_pdf)):
        for img in doc_pdf[i].get_images(full=True):
            xref = img[0]
            base_image = doc_pdf.extract_image(xref)
            imagenes.append(base_image["image"])

    if imagenes:
        tabla = doc.add_table(rows=4, cols=2)
        for idx, img_data in enumerate(imagenes[:8]):
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

# Estado de sesión para persistencia
if "procesado" not in st.session_state:
    st.session_state.procesado = False
    st.session_state.info_ia = ""
    st.session_state.doc_word = None

with st.sidebar:
    archivo = st.file_uploader("Subir PDF de Alicia", type=["pdf"])
    if st.button("Limpiar todo"):
        st.session_state.clear()
        st.rerun()

if archivo and GROQ_KEY:
    # Leer el PDF una sola vez
    doc_original = fitz.open(stream=archivo.read(), filetype="pdf")
    datos_auto = extraccion_forzada_sonoscape(doc_original)

    # FORMULARIO DE VALIDACIÓN
    with st.form("validador"):
        st.subheader("🔍 Validar Datos Extraídos del PDF")
        col1, col2, col3, col4 = st.columns(4)
        
        # Aquí se cargan los datos reales de Alicia si la extracción funcionó
        pac = col1.text_input("Paciente", datos_auto["pac"])
        fey = col2.text_input("FEy %", datos_auto["fy"])
        ddvi = col3.text_input("DDVI mm", datos_auto["dv"])
        siv = col4.text_input("SIV mm", datos_auto["si"])
        
        btn_ia = st.form_submit_button("🚀 GENERAR INFORME SIN VERSO")

    if btn_ia:
        client = Groq(api_key=GROQ_KEY)
        # Prompt Estricto
        prompt = (f"Actúa como el Dr. Pastore. Redacta el informe médico ecocardiográfico. "
                  f"Paciente: {pac}. Hallazgos: DDVI {ddvi}mm, SIV {siv}mm, FEy {fey}%. "
                  f"ESTILO: Muy concreto, estrictamente numérico y clínico. "
                  f"Sin saludos, sin recomendaciones, sin introducciones. Solo los hallazgos.")
        
        res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
        st.session_state.info_ia = res.choices[0].message.content
        st.session_state.doc_word = generar_word({"pac":pac, "fy":fey, "dv":ddvi, "si":siv}, st.session_state.info_ia, doc_original)
        st.session_state.procesado = True

    # RESULTADOS Y DESCARGA (Fuera del formulario para evitar el error)
    if st.session_state.procesado:
        st.markdown("---")
        st.subheader("Informe Técnico Final")
        st.info(st.session_state.info_ia)
        
        st.download_button(
            label="📥 DESCARGAR INFORME (WORD + IMÁGENES)",
            data=st.session_state.doc_word,
            file_name=f"Informe_{pac}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
