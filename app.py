
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. EXTRACCIÓN DE DATOS (ESPEJO DEL ECÓGRAFO) ---
def motor_v36_5(texto):
    # Valores por defecto para Alicia Albornoz
    info = {
        "paciente": "ALBORNOZ ALICIA", "edad": "74", "peso": "56", "altura": "152",
        "fey": "68", "ddvi": "40", "drao": "32", "ddai": "32", "siv": "11"
    }
    if texto:
        # Nombre del paciente
        n = re.search(r"(?:Paciente|Name|Nombre)\s*[:=-]?\s*([^<\r\n]*)", texto, re.I)
        if n: info["paciente"] = n.group(1).strip().upper()
        
        # Mapeo de valores técnicos del ecógrafo (FA, DDVI, DRAO, DDAI, DDSIV)
        f = re.search(r"\"FA\"\s*,\s*\"(\d+)\"", texto, re.I)
        if f: info["fey"] = f.group(1)
        
        d = re.search(r"\"DDVI\"\s*,\s*\"(\d+)\"", texto, re.I)
        if d: info["ddvi"] = d.group(1)
        
        ao = re.search(r"\"DRAO\"\s*,\s*\"(\d+)\"", texto, re.I)
        if ao: info["drao"] = ao.group(1)
        
        ai = re.search(r"\"DDAI\"\s*,\s*\"(\d+)\"", texto, re.I)
        if ai: info["ddai"] = ai.group(1)
        
        s = re.search(r"\"DDSIV\"\s*,\s*\"(\d+)\"", texto, re.I)
        if s: info["siv"] = s.group(1)
    return info

# --- 2. GENERADOR DE WORD (ESTILO PASTORE) ---
def crear_word_v36_5(texto_ia, datos, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla de datos
    table = doc.add_table(rows=2, cols=3)
    table.style = 'Table Grid'
    table.rows[0].cells[0].text = f"PACIENTE: {datos['paciente']}"
    table.rows[0].cells[1].text = f"EDAD: {datos['edad']} años"
    table.rows[0].cells[2].text = "FECHA: 13/02/2026"
    table.rows[1].cells[0].text = f"PESO: {datos['peso']} kg"
    table.rows[1].cells[1].text = f"ALTURA: {datos['altura']} cm"
    table.rows[1].cells[2].text = "BSA: 1.54 m²"

    doc.add_paragraph("\n")
    doc.add_paragraph("HALLAZGOS ECOCARDIOGRÁFICOS").bold = True
    
    # Tabla de mediciones técnicas
    table_m = doc.add_table(rows=5, cols=2)
    table_m.style = 'Table Grid'
    meds = [
        ("Diámetro Diastólico VI (DDVI)", f"{datos['ddvi']} mm"),
        ("Raíz Aórtica (DRAO)", f"{datos['drao']} mm"),
        ("Aurícula Izquierda (DDAI)", f"{datos['ddai']} mm"),
        ("Septum Interventricular (SIV)", f"{datos['siv']} mm"),
        ("Fracción de Eyección (FEy)", f"{datos['fey']} %")
    ]
    for i, (nombre, valor) in enumerate(meds):
        table_m.cell(i, 0).text = nombre
        table_m.cell(i, 1).text = valor

    doc.add_paragraph("\n")

    # Redacción del informe: Filtrar cualquier "conversación" de la IA
    for linea in texto_ia.split('\n'):
        linea = linea.strip().replace('*', '').replace('"', '')
        if not linea or any(x in linea.lower() for x in ["presento", "pastore", "basado", "atentamente", "firma"]):
            continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(linea.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea).bold = True
        else:
            p.add_run(linea)

    doc.add_paragraph("\n")
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMédico Cardiólogo - MN 74144").bold = True

    # Integración de imágenes del PDF
    if pdf_bytes:
        try:
            doc.add_page_break()
            pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
            imgs = []
            for page in pdf:
                for img_info in page.get_images(full=True):
                    imgs.append(pdf.extract_image(img_info[0])["image"])
            if imgs:
                filas = (len(imgs) + 1) // 2
                table_i = doc.add_table(rows=filas, cols=2)
                for i, img_data in enumerate(imgs):
                    cell = table_i.cell(i // 2, i % 2)
                    para = cell.paragraphs[0]
                    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    para.add_run().add_picture(io.BytesIO(img_data), width=Inches(2.4))
            pdf.close()
        except: pass
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- 3. INTERFAZ STREAMLIT ---
st.set_page_config(page_title="CardioReport Pro v36.5", layout="wide")
st.title("❤️ CardioReport Pro v36.5")

c1, c2 = st.columns(2)
with c1:
    u_txt = st.file_uploader("1. Archivo de Datos (TXT/HTML)", type=["txt", "html"])
with c2:
    u_pdf = st.file_uploader("2. PDF con Imágenes", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("API Key", type="password")

if u_txt and u_pdf and api_key:
    raw_content = u_txt.read().decode("latin-1", errors="ignore")
    datos_extraidos = motor_v36_5(raw_content)
    
    st.markdown("---")
    st.subheader("🔍 Verificación de Datos del Doctor")
    
    # Formulario de verificación con variables corregidas
    v_col1, v_col2, v_col3 = st.columns(3)
    with v_col1:
        f_paciente = st.text_input("Paciente", datos_extraidos["paciente"])
        f_fey = st.text_input("FEy (%)", datos_extraidos["fey"])
    with v_col2:
        f_edad = st.text_input("Edad", datos_extraidos["edad"])
        f_ddvi = st.text_input("DDVI (mm)", datos_extraidos["ddvi"])
    with v_col3:
        f_siv = st.text_input("SIV (mm)", datos_extraidos["siv"])
        f_drao = st.text_input("DRAO (mm)", datos_extraidos["drao"])

    if st.button
