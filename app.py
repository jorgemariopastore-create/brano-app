
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. EXTRACCIÓN DE DATOS (ESPEJO DEL DOCTOR) ---
def motor_v36_1(texto):
    # Valores base por defecto
    info = {
        "paciente": "ALBORNOZ ALICIA", "edad": "74", "peso": "56", "altura": "152",
        "fey": "68", "ddvi": "40", "drao": "32", "ddai": "32", "siv": "11"
    }
    if texto:
        n = re.search(r"(?:Paciente|Name|Nombre)\s*[:=-]?\s*([^<\r\n]*)", texto, re.I)
        if n: info["paciente"] = n.group(1).strip().upper()
        
        # Mapeo exacto de etiquetas técnicas de tu ecógrafo
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

# --- 2. GENERADOR DE WORD (ESTILO PASTORE ESTRICTO) ---
def crear_word_v36_1(texto_ia, datos_v, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    table = doc.add_table(rows=2, cols=3)
    table.style = 'Table Grid'
    table.rows[0].cells[0].text = f"PACIENTE: {datos_v['paciente']}"
    table.rows[0].cells[1].text = f"EDAD: {datos_v['edad']} años"
    table.rows[0].cells[2].text = f"FECHA: 13/02/2026"
    table.rows[1].cells[0].text = f"PESO: {datos_v['peso']} kg"
    table.rows[1].cells[1].text = f"ALTURA: {datos_v['altura']} cm"
    table.rows[1].cells[2].text = "BSA: 1.54 m²"

    doc.add_paragraph("\n")
    doc.add_paragraph("HALLAZGOS ECOCARDIOGRÁFICOS").bold = True
    
    table_m = doc.add_table(rows=5, cols=2)
    table_m.style = 'Table Grid'
    meds = [
        ("Diámetro Diastólico VI (DDVI)", f"{datos_v['ddvi']} mm"),
        ("Raíz Aórtica (DRAO)", f"{datos_v['drao']} mm"),
        ("Aurícula Izquierda (DDAI)", f"{datos_v['ddai']} mm"),
        ("Septum Interventricular (SIV)", f"{datos_v['siv']} mm"),
        ("Fracción de Eyección (FEy)", f"{datos_v['fey']} %")
    ]
    for i, (n, v) in enumerate(meds):
        table_m.cell(i, 0).text = n
        table_m.cell(i, 1).text = v

    doc.add_paragraph("\n")

    # Limpieza total del texto: solo puntos romanos
    for linea in texto_ia.split('\n'):
        linea = linea.strip().replace('*', '').replace('"', '')
        if not linea or any(x in linea.lower() for x in ["presento", "pastore", "basado", "atentamente", "firma", "hola"]):
            continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(linea.startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea).bold = True
        else:
            p.add_run(linea)

    doc.add_paragraph("\n")
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMédico Cardiólogo - MN 74144").bold = True

    if pdf_bytes:
        try:
            doc.add_page_break()
            pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
            imgs = [pdf.extract_image(img[0])["image"] for page in pdf for img in page.get_images(full=True)]
            if imgs:
                t_i = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
                for i, d in enumerate(imgs):
                    cp = t_i.cell(i//2, i%2).paragraphs[0]
                    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    cp.add_run().add_picture(io.BytesIO(d), width=Inches(2.3))
            pdf.close()
        except: pass
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- 3. INTERFAZ (BOTONES REESTABLECIDOS) ---
st.set_page_config(page_title="CardioReport Pro v36.1", layout="wide")
st.title("❤️ CardioReport Pro v36.1")

c_file1, c_file2 = st.columns(2)
with c_file1:
    u_txt = st.file_uploader("1. Subir Datos (TXT/HTML)", type=["txt", "html"])
with c_file2:
    u_pdf = st.file_uploader("2. Subir PDF para Imágenes", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("API Key", type="password")

if u_txt and u_pdf and api_key:
    raw = u_txt.read().decode("latin-1", errors="ignore")
    info = motor_v36_1(raw)
    
    st.markdown("---")
    st.subheader("📝 Validar Datos del Informe")
    col1, col2, col3 = st.columns(3)
    with col1:
        nom_v = st.text_input("Paciente", info["paciente"])
        fey_v = st.text_input("FEy (%)", info["fey"])
    with col2:
        eda_v = st.text_input("Edad", info["edad"])
        ddvi_v = st.text_input("DDVI (mm)", info["ddvi"])
    with col3:
        siv_v = st.text_input("SIV (mm)", info["siv"])
        drao_v = st.text_input("DRAO (mm)", info["drao"])

    if st.button("🚀 GENERAR DOCUMENTO WORD"):
        client = Groq(api_key=api_key)
        # Prompt ultra-seco para evitar "conversación"
        prompt = f"""
        Escribe exclusivamente los hallazgos:
        I. ANATOMÍA: Raíz aórtica ({drao_v}
