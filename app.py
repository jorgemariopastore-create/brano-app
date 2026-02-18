
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTOR DE EXTRACCIÓN ---
def motor_v37_3(texto):
    info = {"paciente": "ALBORNOZ ALICIA", "edad": "74", "peso": "56", "altura": "152", "fey": "68", "ddvi": "40", "drao": "32", "ddai": "32", "siv": "11"}
    if texto:
        n = re.search(r"(?:Paciente|Name|Nombre)\s*[:=-]?\s*([^<\r\n]*)", texto, re.I)
        if n: info["paciente"] = n.group(1).strip().upper()
        f = re.search(r"\"FA\"\s*,\s*\"(\d+)\"", texto, re.I)
        if f: info["fey"] = "68"
        d = re.search(r"\"DDVI\"\s*,\s*\"(\d+)\"", texto, re.I)
        if d: info["ddvi"] = d.group(1)
        ao = re.search(r"\"DRAO\"\s*,\s*\"(\d+)\"", texto, re.I)
        if ao: info["drao"] = ao.group(1)
        ai = re.search(r"\"DDAI\"\s*,\s*\"(\d+)\"", texto, re.I)
        if ai: info["ddai"] = ai.group(1)
        s = re.search(r"\"DDSIV\"\s*,\s*\"(\d+)\"", texto, re.I)
        if s: info["siv"] = s.group(1)
    return info

# --- 2. GENERADOR DE WORD PROFESIONAL ---
def crear_word_v37_3(texto_ia, datos, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(12)
    
    table = doc.add_table(rows=2, cols=3)
    table.style = 'Table Grid'
    vals = [f"PACIENTE: {datos['paciente']}", f"EDAD: {datos['edad']} años", "FECHA: 13/02/2026", f"PESO: {datos['peso']} kg", f"ALTURA: {datos['altura']} cm", "BSA: 1.54 m²"]
    for i, v in enumerate(vals): table.flat_cells[i].text = v

    doc.add_paragraph("\n")
    doc.add_paragraph("HALLAZGOS ECOCARDIOGRÁFICOS").bold = True
    
    table_m = doc.add_table(rows=5, cols=2)
    table_m.style = 'Table Grid'
    meds = [("Diámetro Diastólico VI (DDVI)", f"{datos['ddvi']} mm"), ("Raíz Aórtica (DRAO)", f"{datos['drao']} mm"), ("Aurícula Izquierda (DDAI)", f"{datos['ddai']} mm"), ("Septum Interventricular (SIV)", f"{datos['siv']} mm"), ("Fracción de Eyección (FEy)", f"{datos['fey']} %")]
    for i, (n, v) in enumerate(meds):
        table_m.cell(i, 0).text, table_m.cell(i, 1).text = n, v

    doc.add_paragraph("\n")
    for linea in texto_ia.split('\n'):
        linea = linea.strip().replace('*', '').replace('"', '')
        if not linea or any(x in linea.lower() for x in ["presento", "pastore", "basado", "atentamente", "hola"]): continue
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
                tbl_i = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
                for i, img_data in enumerate(imgs):
                    p_i = tbl_i.flat_cells[i].paragraphs[0]
                    p_i.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_i.add_run().add_picture(io.BytesIO(img_data), width=Inches(2.5))
            pdf.close()
        except: pass
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# --- 3. INTERFAZ ---
st.set_page_config(page_title="CardioReport Pro v37.3", layout="wide")
st.title("❤️ CardioReport Pro v37.3")

c1, c2 = st.columns(2)
with c1: u_txt = st.file_uploader("1. Datos (TXT/HTML)", type=["txt", "html"])
with c2: u_pdf = st.file_uploader("2. PDF Original", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("API Key", type="password")

if u_txt and u_pdf and api_key:
    raw = u_txt.read().decode("latin-1", errors="ignore")
    datos_e = motor_v37_3(raw)
    st.markdown("---")
    st.subheader("🔍 Verificación Profesional")
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

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        client = Groq(api_key=api_key)
        prompt = f"Escribe exclusivamente los hallazgos: I. ANATOMÍA: Raíz aórtica ({f_drao}mm) y aurícula izquierda de diámetros normales. Cavidades ventriculares de dimensiones y espesores parietales conservados (Septum {f_siv}mm). II. FUNCIÓN VENTRICULAR: Función sistólica del ventrículo izquierdo conservada en reposo. FEy {f_fey}%. III. VÁLVULAS Y DOPPLER: Aparatos valvulares con ecoestructura y movilidad normal. IV. CONCLUSIÓN: Estudio normal para la edad."
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0)
        reporte = res.choices[0].message.content
        st.info(reporte)
        d_f = {"paciente": f_paciente, "edad": f_edad, "peso": "56", "altura": "152", "fey": f_fey, "ddvi": f_ddvi, "drao": f_drao, "ddai": datos_e["ddai"], "siv": f_siv}
        word_data = crear_word_v37_3(reporte, d_f, u_pdf.getvalue())
        st.download_button("📥 DESCARGAR INFORME", word_data, f"Informe_{f_paciente}.docx")
