
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re
import io
from docx import Document
from docx.shared import Inches, Pt
from datetime import datetime

# --- CONFIGURACIÓN SENIOR ---
st.set_page_config(page_title="CardioReport Pro v6.0", layout="wide")

def get_client():
    key = st.secrets.get("GROQ_API_KEY") or st.session_state.get("api_key")
    return Groq(api_key=key) if key else None

def extraer_todo_el_contexto(doc_pdf):
    # Extraemos texto de las primeras 2 páginas para datos y conclusiones del médico
    texto = ""
    for i in range(min(2, len(doc_pdf))):
        texto += doc_pdf[i].get_text()
    
    # Limpieza de caracteres de tabla (", \n, \r)
    t_limpio = re.sub(r'[\"\'\r\t]', '', texto)
    t_limpio = re.sub(r'\n+', ' ', t_limpio)
    
    datos = {
        "paciente": "NO DETECTADO",
        "fecha": datetime.now().strftime("%d/%m/%Y"),
        "edad": "", "peso": "", "altura": "",
        "ddvi": "", "siv": "", "fey": "", "ai": ""
    }

    # 1. Regex de alta precisión
    m_pac = re.search(r"Paciente:\s*([A-Z\s]+?)(?:Fecha|Edad|$)", t_limpio, re.I)
    if m_pac: datos["paciente"] = m_pac.group(1).strip()
    
    m_fec = re.search(r"Fecha(?:\s*de\s*estudio)?:\s*(\d{2}/\d{2}/\d{4})", t_limpio, re.I)
    if m_fec: datos["fecha"] = m_fec.group(1)

    # 2. Datos de tabla (Busca etiqueta y el número inmediato)
    # Ejemplo: DDVI 40 mm -> Captura 40
    metricas = {
        "ddvi": r"DDVI\s*(\d+)",
        "siv": r"(?:DDSIV|SIV)\s*(\d+)",
        "ai": r"(?:DDAI|AI)\s*(\d+)",
        "fey": r"eyección\s*del\s*VI\s*(\d+)" # Prioriza texto del Dr.
    }
    
    for k, v in metricas.items():
        res = re.search(v, t_limpio, re.I)
        if res: datos[k] = res.group(1)
    
    # Si no encontró FEy en texto, busca FA en tabla y calcula
    if not datos["fey"]:
        m_fa = re.search(r"FA\s*(\d+)", t_limpio)
        if m_fa: datos["fey"] = str(round(float(m_fa.group(1)) * 1.76))

    return datos

def generar_word_estilo_pastore(datos, informe_ia, doc_pdf):
    doc = Document()
    # Encabezado Médico
    h = doc.add_heading("INFORME ECOCARDIOGRÁFICO", 0)
    
    # Datos Generales
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {datos['paciente']}\n").bold = True
    p.add_run(f"FECHA: {datos['fecha']}\n")
    if datos['edad']: p.add_run(f"EDAD: {datos['edad']} años  ")
    if datos['peso']: p.add_run(f"PESO: {datos['peso']} kg  ")
    if datos['altura']: p.add_run(f"ALTURA: {datos['altura']} cm")

    doc.add_paragraph("-" * 50)
    
    # Cuerpo del Informe (Sin verso)
    doc.add_paragraph(informe_ia)
    
    doc.add_paragraph("\n" + "_" * 30)
    doc.add_paragraph("Dr. Francisco A. Pastore\nM.P. 12345") # Ajustar matricula

    # ANEXO 4x2
    doc.add_page_break()
    doc.add_heading("ANEXO DE IMÁGENES", level=1)
    imgs = []
    for i in range(len(doc_pdf)):
        for img in doc_pdf[i].get_images(full=True):
            imgs.append(doc_pdf.extract_image(img[0])["image"])
    
    if imgs:
        table = doc.add_table(rows=4, cols=2)
        for idx, img_data in enumerate(imgs[:8]):
            run = table.rows[idx//2].cells[idx%2].paragraphs[0].add_run()
            run.add_picture(io.BytesIO(img_data), width=Inches(2.8))

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- INTERFAZ ---
st.title("🏥 CardioReport Senior v6.0")

with st.sidebar:
    if "GROQ_API_KEY" not in st.secrets:
        st.session_state.api_key = st.text_input("API Key", type="password")
    archivo = st.file_uploader("Subir PDF", type=["pdf"])

if archivo:
    doc_pdf = fitz.open(stream=archivo.read(), filetype="pdf")
    d_auto = extraer_todo_el_contexto(doc_pdf)

    with st.form("validador"):
        st.subheader("Datos Generales y Técnicos")
        c1, c2, c3 = st.columns([2,1,1])
        pac = c1.text_input("Paciente", d_auto["paciente"])
        fec = c2.text_input("Fecha", d_auto["fecha"])
        edad = c3.text_input("Edad", d_auto["edad"])
        
        c4, c5, c6, c7 = st.columns(4)
        fey = c4.text_input("FEy %", d_auto["fey"])
        ddvi = c5.text_input("DDVI mm", d_auto["ddvi"])
        siv = c6.text_input("SIV mm", d_auto["siv"])
        ai = c7.text_input("AI mm", d_auto["ai"])
        
        if st.form_submit_button("GENERAR INFORME"):
            client = get_client()
            # Prompt Senior: Forzamos estructura Concreta + Conclusión
            prompt = f"""Actúa como el Dr. Pastore. Genera un informe médico.
            DATOS: Paciente {pac}, DDVI {ddvi}mm, SIV {siv}mm, AI {ai}mm, FEy {fey}%.
            ESTILO: Técnico, médico, sin verso, sin recomendaciones.
            ESTRUCTURA: 
            1. Hallazgos (numéricos y de motilidad).
            2. Conclusión (Diagnóstico clínico breve)."""
            
            res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
            st.session_state.txt = res.choices[0].message.content
            st.session_state.word = generar_word_estilo_pastore(
                {"paciente":pac, "fecha":fec, "edad":edad, "peso":"", "altura":"", "fey":fey}, 
                st.session_state.txt, doc_pdf
            )
            st.session_state.ready = True

    if st.session_state.get("ready"):
        st.info(st.session_state.txt)
        st.download_button("📥 DESCARGAR INFORME WORD", st.session_state.word, f"Informe_{pac}.docx")
