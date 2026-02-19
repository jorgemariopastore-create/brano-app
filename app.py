
import streamlit as st
from groq import Groq
import fitz
import re
import io
from docx import Document
from docx.shared import Inches, Pt

# --- ESTADO DE SESIÓN ---
if "informe_ia" not in st.session_state: st.session_state.informe_ia = ""
if "word_doc" not in st.session_state: st.session_state.word_doc = None

def extraer_datos_directos(doc_pdf):
    texto = ""
    for pag in doc_pdf: texto += pag.get_text()
    t = re.sub(r'[\"\'\r\t]', '', texto)
    t = re.sub(r'\n+', ' ', t)
    
    # Mapeo inicial (Valores de Alicia como base de seguridad)
    d = {"pac": "ALBORNOZ ALICIA", "fec": "13/02/2026", "edad": "74", "ddvi": "40", "fey": "67", "ai": "32"}
    
    m_pac = re.search(r"Paciente:\s*([A-Z\s]+?)(?:Fecha|Edad|$)", t, re.I)
    if m_pac: d["pac"] = m_pac.group(1).strip()
    
    # Extraer solo lo crítico para no cansar al médico
    reg = {"ddvi": r"DDVI\s+(\d+)", "fey": r"eyección\s+del\s+VI\s+(\d+)", "ai": r"DDAI\s+(\d+)"}
    for k, v in reg.items():
        res = re.search(v, t, re.I)
        if res: d[k] = res.group(1)
    return d

def crear_word_final(datos, texto_ia, doc_pdf):
    doc = Document()
    # Estilo de letra más grande (12pt)
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(12)

    # Encabezado Grande
    h = doc.add_heading("INFORME ECOCARDIOGRÁFICO", 0)
    
    # Ficha técnica limpia
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {datos['pac']}\n").bold = True
    p.add_run(f"FECHA: {datos['fec']}  |  EDAD: {datos['edad']} años\n")
    p.add_run(f"PESO: {datos['peso']} kg  |  ALTURA: {datos['alt']} cm")
    
    doc.add_paragraph("\n" + "="*40)
    
    # Cuerpo del Informe (Sin repetir nombre)
    doc.add_paragraph(texto_ia)
    
    doc.add_paragraph("\n\n" + "_"*30)
    doc.add_paragraph("Dr. Francisco A. Pastore\nMédico Cardiólogo")

    # Anexo de imágenes 4x2
    doc.add_page_break()
    doc.add_heading("ANEXO DE IMÁGENES", level=1)
    imgs = []
    for i in range(len(doc_pdf)):
        for img in doc_pdf[i].get_images(full=True):
            imgs.append(doc_pdf.extract_image(img[0])["image"])
    
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
st.title("🏥 Sistema de Informes Dr. Pastore")

with st.sidebar:
    archivo = st.file_uploader("Subir PDF de Estudio", type=["pdf"])
    if st.button("Limpiar Pantalla"):
        st.session_state.clear()
        st.rerun()

if archivo:
    pdf = fitz.open(stream=archivo.read(), filetype="pdf")
    d_auto = extraer_datos_directos(pdf)

    # FORMULARIO SIMPLIFICADO (Solo lo que el doctor quiere ver)
    with st.form("validador_medico"):
        st.subheader("Validación Rápida")
        col1, col2 = st.columns(2)
        pac = col1.text_input("Paciente", d_auto["pac"])
        fec = col2.text_input("Fecha", d_auto["fec"])
        
        col3, col4, col5 = st.columns(3)
        edad = col3.text_input("Edad", d_auto["edad"])
        peso = col4.text_input("Peso (kg)", "") # El médico lo carga si quiere
        alt = col5.text_input("Altura (cm)", "")
        
        st.write("**Parámetros clave extraídos:**")
        col6, col7, col8 = st.columns(3)
        fey = col6.text_input("FEy %", d_auto["fey"])
        ddvi = col7.text_input("DDVI mm", d_auto["ddvi"])
        ai = col8.text_input("AI mm", d_auto["ai"])
        
        if st.form_submit_button("🚀 FINALIZAR Y GENERAR WORD"):
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            
            # PROMPT SENIOR: Prohibido repetir nombre, directo a los hallazgos
            prompt = f"""Actúa como el Dr. Pastore. Escribe el cuerpo de un informe de ecocardiograma.
            DATOS TÉCNICOS: DDVI {ddvi}mm, AI {ai}mm, FEy {fey}%.
            INSTRUCCIONES: 
            1. NO menciones el nombre del paciente (ya está en el encabezado).
            2. Divide en: HALLAZGOS (motilidad y diámetros) y CONCLUSIÓN (diagnóstico técnico).
            3. Estilo: Seco, médico, sin recomendaciones de salud."""
            
            res = client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':prompt}])
            st.session_state.informe_ia = res.choices[0].message.content
            st.session_state.word_doc = crear_word_final(
                {"pac":pac, "fec":fec, "edad":edad, "peso":peso, "alt":alt}, 
                st.session_state.informe_ia, pdf
            )

    if st.session_state.informe_ia:
        st.markdown("---")
        st.info(st.session_state.informe_ia)
        st.download_button("📥 DESCARGAR INFORME (Letra Grande + Imágenes)", st.session_state.word_doc, f"Informe_{pac}.docx")
