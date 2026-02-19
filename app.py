
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re
import io
from docx import Document
from docx.shared import Inches

st.set_page_config(page_title="CardioReport Senior v4.0", layout="wide")

def extraer_datos_limpios(doc_pdf):
    # Extraer texto de las primeras páginas
    texto_sucio = ""
    for i in range(min(2, len(doc_pdf))):
        texto_sucio += doc_pdf[i].get_text()
    
    # NORMALIZACIÓN SENIOR: 
    # Eliminamos comillas, saltos de línea, comas y espacios múltiples
    # Esto transforma '"DDVI\n","40\n"' en 'DDVI 40'
    t = re.sub(r'[\"\'\n\r\t,]', ' ', texto_sucio)
    t = re.sub(r'\s+', ' ', t) 
    
    datos = {"pac": "NO DETECTADO", "dv": "", "si": "", "fy": ""}
    
    # 1. Búsqueda de Paciente
    m_pac = re.search(r"Paciente\s*:\s*([A-Z\s]+?)(?:\s*Fecha|\s*Estudio|$)", t, re.I)
    if m_pac: datos["pac"] = m_pac.group(1).strip()

    # 2. Búsqueda de DDVI (Busca la sigla y captura el número más cercano)
    # Patrón: Palabra DDVI -> espacios/caracteres -> número
    m_dv = re.search(r"DDVI\s*(\d+)", t, re.I)
    if m_dv: datos["dv"] = m_dv.group(1)
    
    # 3. Búsqueda de SIV / DDSIV
    m_si = re.search(r"(?:DDSIV|SIV)\s*(\d+)", t, re.I)
    if m_si: datos["si"] = m_si.group(1)
    
    # 4. FEy: Priorizar texto redactado 'eyección del VI 67%'
    m_fe = re.search(r"eyección\s*del\s*VI\s*(\d+)", t, re.I)
    if m_fe:
        datos["fy"] = m_fe.group(1)
    else:
        # Si no, buscar FA en la tabla
        m_fa = re.search(r"FA\s*(\d+)", t, re.I)
        if m_fa: datos["fy"] = str(round(float(m_fa.group(1)) * 1.76))

    return datos

def crear_informe_word(datos, texto_ia, doc_pdf):
    doc = Document()
    doc.add_heading("INFORME ECOCARDIOGRÁFICO", 0)
    doc.add_paragraph(f"PACIENTE: {datos['pac']}")
    doc.add_paragraph(texto_ia)
    doc.add_paragraph("\nDr. Francisco A. Pastore")
    
    # Anexo 4x2
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
        for idx, img_data in enumerate(imagenes[:8]):
            r, c = idx // 2, idx % 2
            run = tabla.rows[r].cells[c].paragraphs[0].add_run()
            run.add_picture(io.BytesIO(img_data), width=Inches(2.5))
            
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- INTERFAZ ---
st.title("🏥 CardioReport Senior - Dr. Pastore")

if "final_txt" not in st.session_state:
    st.session_state.final_txt = ""
    st.session_state.final_word = None

with st.sidebar:
    pdf_file = st.file_uploader("Subir PDF", type=["pdf"])
    groq_api = st.text_input("Groq API Key", type="password")

if pdf_file and groq_api:
    pdf_obj = fitz.open(stream=pdf_file.read(), filetype="pdf")
    # Al subir el PDF, extraemos datos reales inmediatamente
    datos_iniciales = extraer_datos_limpios(pdf_obj)

    # FORMULARIO DE VALIDACIÓN
    with st.form("form_valida"):
        st.subheader("Confirmación de Datos (Extraídos del PDF)")
        col1, col2, col3, col4 = st.columns(4)
        pac = col1.text_input("Paciente", datos_iniciales["pac"])
        fey = col2.text_input("FEy %", datos_iniciales["fy"])
        ddvi = col3.text_input("DDVI mm", datos_iniciales["dv"])
        siv = col4.text_input("SIV mm", datos_iniciales["si"])
        
        if st.form_submit_button("🚀 GENERAR INFORME TÉCNICO"):
            client = Groq(api_key=groq_api)
            prompt = (f"Actúa como el Dr. Pastore. Informe Ecocardiográfico. "
                      f"Paciente: {pac}. Hallazgos: DDVI {ddvi}mm, SIV {siv}mm, FEy {fey}%. "
                      f"ESTILO: Estrictamente clínico y numérico. Sin recomendaciones. "
                      f"Sin introducciones. Sin verso. Concreto.")
            
            res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
            st.session_state.final_txt = res.choices[0].message.content
            st.session_state.final_word = crear_informe_word({"pac":pac, "fy":fey, "dv":ddvi, "si":siv}, st.session_state.final_txt, pdf_obj)

    # MOSTRAR RESULTADOS (FUERA DEL FORM)
    if st.session_state.final_txt:
        st.markdown("---")
        st.subheader("Informe Final")
        st.info(st.session_state.final_txt)
        st.download_button(
            label="📥 DESCARGAR WORD CON IMÁGENES",
            data=st.session_state.final_word,
            file_name=f"Informe_{pac}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
