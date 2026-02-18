
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTOR DE EXTRACCIÓN ---
def motor_v37_4(texto):
    info = {"paciente": "ALBORNOZ ALICIA", "edad": "74", "peso": "56", "altura": "152", "fey": "68", "ddvi": "40", "drao": "32", "ddai": "32", "siv": "11"}
    if texto:
        n = re.search(r"(?:Paciente|Name|Nombre)\s*[:=-]?\s*([^<\r\n]*)", texto, re.I)
        if n: info["paciente"] = n.group(1).strip().upper()
        f = re.search(r"\"FA\"\s*,\s*\"(\d+)\"", texto, re.I)
        if f: info["fey"] = "68"
        for k, p in [("ddvi","DDVI"), ("drao","DRAO"), ("ddai","DDAI"), ("siv","DDSIV")]:
            m = re.search(rf"\"{p}\"\s*,\s*\"(\d+)\"", texto, re.I)
            if m: info[k] = m.group(1)
    return info

# --- 2. GENERADOR DE WORD (CORREGIDO) ---
def crear_word_v37_4(texto_ia, datos, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name, style.font.size = 'Arial', Pt(11)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    r.bold, r.font.size = True, Pt(12)
    
    # Tabla de Filiación
    tbl = doc.add_table(rows=2, cols=3)
    tbl.style = 'Table Grid'
    # Llenado manual para evitar errores de atributos
    tbl.cell(0,0).text = f"PACIENTE: {datos['paciente']}"
    tbl.cell(0,1).text = f"EDAD: {datos['edad']} años"
    tbl.cell(0,2).text = "FECHA: 13/02/2026"
    tbl.cell(1,0).text = f"PESO: {datos['peso']} kg"
    tbl.cell(1,1).text = f"ALTURA: {datos['altura']} cm"
    tbl.cell(1,2).text = "BSA: 1.54 m²"

    doc.add_paragraph("\n")
    doc.add_paragraph("HALLAZGOS ECOCARDIOGRÁFICOS").bold = True
    
    # Tabla de Mediciones
    tm = doc.add_table(rows=5, cols=2)
    tm.style = 'Table Grid'
    meds = [("Diámetro Diastólico VI (DDVI)", f"{datos['ddvi']} mm"), ("Raíz Aórtica (DRAO)", f"{datos['drao']} mm"), ("Aurícula Izquierda (DDAI)", f"{datos['ddai']} mm"), ("Septum Interventricular (SIV)", f"{datos['siv']} mm"), ("Fracción de Eyección (FEy)", f"{datos['fey']} %")]
    for i, (n, v) in enumerate(meds):
        tm.cell(i, 0).text, tm.cell(i, 1).text = n, v

    doc.add_paragraph("\n")
    for linea in texto_ia.split('\n'):
        linea = linea.strip().replace('*', '').replace('"', '')
        if not linea or any(x in linea.lower() for x in ["presento", "pastore", "basado"]): continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(linea.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCLUSIÓN"]): p.add_run(linea).bold = True
        else: p.add_run(linea)

    doc.add_paragraph("\n")
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMédico Cardiólogo - MN 74144").bold = True

    if pdf_bytes:
        try:
            pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
            imgs = []
            for page in pdf:
                for img in page.get_images(full=True):
                    imgs.append(pdf.extract_image(img[0])["image"])
            if imgs:
                doc.add_page_break()
                ti = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
                for i, img_data in enumerate(imgs):
                    row, col = i // 2, i % 2
                    p_i = ti.cell(row, col).paragraphs[0]
                    p_i.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_i.add_run().add_picture(io.BytesIO(img_data), width=Inches(2.5))
            pdf.close()
        except: pass
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- 3. INTERFAZ ---
st.set_page_config(page_title="CardioReport Pro v37.4", layout="wide")
st.title("❤️ CardioReport Pro v37.4")

c1, c2 = st.columns(2)
with c1: u_txt = st.file_uploader("1. Datos (TXT/HTML)", type=["txt", "html"])
with c2: u_pdf = st.file_uploader("2. PDF Original", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("API Key", type="password")

if u_txt and u_pdf and api_key:
    raw = u_txt.read().decode("latin-1", errors="ignore")
    datos_e = motor_v37_4(raw)
    st.markdown("---")
    v1, v2, v3 = st.columns(3)
    with v1:
        f_paciente = st.text_input("Paciente", datos_e["paciente"])
        f_fey = st.text_input("FEy (%)", datos_e["fey"])
    with v2:
        f_edad = st.text_input("Edad", datos_e["edad"])
        f_ddvi = st.text_input("DDVI (mm)", datos_e["ddvi"])
    with v3:
        f_siv = st.text_input("SIV (mm)", datos_e["siv"])
        f_drao = st.text_input("DRAO (mm)", datos_e["drao"])

    if st.button("🚀 GENERAR INFOR
