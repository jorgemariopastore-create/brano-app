
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTOR DE EXTRACCIÓN (REVISADO) ---
def motor_v36_4(texto):
    info = {
        "paciente": "ALBORNOZ ALICIA", "edad": "74", "peso": "56", "altura": "152",
        "fey": "68", "ddvi": "40", "drao": "32", "ddai": "32", "siv": "11"
    }
    if texto:
        n = re.search(r"(?:Paciente|Name|Nombre)\s*[:=-]?\s*([^<\r\n]*)", texto, re.I)
        if n: info["paciente"] = n.group(1).strip().upper()
        # Búsqueda de etiquetas del ecógrafo
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

# --- 2. GENERADOR DE WORD (PASTORE ORIGINAL) ---
def crear_word_v36_4(texto_ia, datos_v, pdf_bytes):
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
    table.rows[0].cells[2].text = "FECHA: 13/02/2026"
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

    # Filtro estricto: El informe empieza directo con los puntos romanos
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

    # Imágenes (Corregido con variables seguras)
    if pdf_bytes:
        try:
            doc.add_page_break()
            pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
            imgs = []
            for page in pdf:
                for item in page.get_images(full=True):
                    imgs.append(pdf.extract_image(item[0])["image"])
            
            if len(imgs) > 0:
                filas = (len(imgs) + 1) // 2
                t_i = doc.add_table(rows=filas, cols=2)
                for i, img_data in enumerate(imgs):
                    celda = t_i.cell(i // 2, i % 2)
                    parra = celda.paragraphs[0]
                    parra.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    parra.add_run().add_picture(io.BytesIO(img_data), width=Inches(2.5))
            pdf.close()
        except:
            pass
    
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

# --- 3. INTERFAZ (RESTABLECIDA) ---
st.set_page_config(page_title="CardioReport Pro v36.4", layout="wide")
st.title("❤️ CardioReport Pro v36.4")

# Botones de carga
ca, cb = st.columns(2)
with ca:
    u_txt = st.file_uploader("1. Subir Datos (TXT/HTML)", type=["txt", "html"])
with cb:
    u_pdf = st.file_uploader("2. Subir PDF para Imágenes", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("API Key", type="password")

if u_txt and u_pdf and api_key:
    raw = u_txt.read().decode("latin-1", errors="ignore")
    info = motor_v36_4(raw)
    
    st.markdown("---")
    st.subheader("📝 Verificación de Datos")
    c1, c2, c3 = st.columns(3)
    with c1:
        nom
