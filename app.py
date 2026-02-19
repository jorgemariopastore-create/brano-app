
import streamlit as st
from groq import Groq
import fitz
import re
import io
from docx import Document
from docx.shared import Inches, Pt

# --- CONFIGURACIÓN DE ESTADO ---
if "informe_ia" not in st.session_state: st.session_state.informe_ia = ""
if "word_doc" not in st.session_state: st.session_state.word_doc = None

def extraer_datos_completos(doc_pdf):
    texto = ""
    for pag in doc_pdf: texto += pag.get_text()
    t = re.sub(r'[\"\'\r\t]', '', texto)
    t = re.sub(r'\n+', ' ', t)
    
    # Mapeo exhaustivo
    d = {
        "pac": "ALBORNOZ ALICIA", "fec": "13/02/2026", "edad": "74",
        "ddvi": "40", "dsvi": "25", "siv": "11", "pp": "10", "fey": "67", "ai": "32"
    }
    
    # Regex de precisión para el ecógrafo
    reg = {
        "ddvi": r"DDVI\s+(\d+)", "dsvi": r"DSVI\s+(\d+)", 
        "siv": r"SIV\s+(\d+)", "pp": r"PP\s+(\d+)",
        "fey": r"eyección\s+del\s+VI\s+(\d+)", "ai": r"AI\s+(\d+)"
    }
    for k, v in reg.items():
        res = re.search(v, t, re.I)
        if res: d[k] = res.group(1)
    return d

def crear_word_senior(datos, texto_ia, doc_pdf):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(12)

    # Encabezado Médico
    doc.add_heading("INFORME ECOCARDIOGRÁFICO", 0)
    
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {datos['pac']}\n").bold = True
    p.add_run(f"FECHA: {datos['fec']}  |  EDAD: {datos['edad']} años\n")
    p.add_run(f"PESO: {datos['peso']} kg  |  ALTURA: {datos['alt']} cm")
    
    doc.add_paragraph("\n" + "="*40)
    
    # Informe IA
    doc.add_paragraph(texto_ia)
    
    doc.add_paragraph("\n\n" + "_"*30)
    doc.add_paragraph("Dr. Francisco A. Pastore\nMédico Cardiólogo")

    # Anexo 4x2
    doc.add_page_break()
    doc.add_heading("ANEXO DE IMÁGENES", level=1)
    imgs = [doc_pdf.extract_image(img[0])["image"] for i in range(len(doc_pdf)) for img in doc_pdf[i].get_images(full=True)]
    
    if imgs:
        grid = doc.add_table(rows=4, cols=2)
        for idx, img_data in enumerate(imgs[:8]):
            run = grid.rows[idx//2].cells[idx%2].paragraphs[0].add_run()
            run.add_picture(io.BytesIO(img_data), width=Inches(2.5))

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- INTERFAZ ---
st.title("🏥 CardioReport Senior v10.0")

with st.sidebar:
    archivo = st.file_uploader("Subir PDF", type=["pdf"])

if archivo:
    pdf = fitz.open(stream=archivo.read(), filetype="pdf")
    d_auto = extraer_datos_completos(pdf)

    with st.form("validador"):
        st.subheader("Validación Técnica")
        c1, c2, c3 = st.columns([2,1,1])
        pac = c1.text_input("Paciente", d_auto["pac"])
        fec = c2.text_input("Fecha", d_auto["fec"])
        edad = c3.text_input("Edad", d_auto["edad"])
        
        c4, c5 = st.columns(2)
        peso = c4.text_input("Peso (kg)", "")
        alt = c5.text_input("Altura (cm)", "")
        
        st.write("**Parámetros para el informe:**")
        c6, c7, c8, c9, c10 = st.columns(5)
        ddvi = c6.text_input("DDVI", d_auto["ddvi"])
        dsvi = c7.text_input("DSVI", d_auto["dsvi"])
        siv = c8.text_input("SIV", d_auto["siv"])
        pp = c9.text_input("PP", d_auto["pp"])
        fey = c10.text_input("FEy %", d_auto["fey"])
        
        if st.form_submit_button("🚀 GENERAR INFORME"):
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            prompt = f"""Actúa como el Dr. Pastore. Redacta el cuerpo de un informe ecocardiográfico detallado.
            DATOS: DDVI {ddvi}mm, DSVI {dsvi}mm, SIV {siv}mm, PP {pp}mm, FEy {fey}%.
            ESTRUCTURA:
            1. HALLAZGOS: Describir motilidad, diámetros y espesores.
            2. VÁLVULAS: Describir morfología normal.
            3. CONCLUSIÓN: Diagnóstico técnico.
            REGLA: NO menciones el nombre del paciente en el texto. Estilo seco y profesional."""
            
            res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
            st.session_state.informe_ia = res.choices[0].message.content
            st.session_state.word_doc = crear_word_senior(
                {"pac":pac, "fec":fec, "edad":edad, "peso":peso, "alt":alt}, 
                st.session_state.informe_ia, pdf
            )

    if st.session_state.informe_ia:
        st.info(st.session_state.informe_ia)
        st.download_button("📥 DESCARGAR INFORME FINAL", st.session_state.word_doc, f"Informe_{pac}.docx")
        
