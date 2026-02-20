
import streamlit as st
from docx import Document
from docx.shared import Pt, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import os
import re
import PyPDF2
from datetime import datetime

# --- 1. EXTRACCIÓN DE DATOS SEGUROS ---
def extraer_datos_pdf(file):
    datos = {"pac": "", "peso": "", "fecha": datetime.now()}
    if file:
        try:
            reader = PyPDF2.PdfReader(file)
            texto = ""
            for page in reader.pages: texto += page.extract_text()
            
            # Nombre del Paciente
            m_pac = re.search(r"Paciente[:\s]+(.*)", texto, re.IGNORECASE)
            if m_pac: datos["pac"] = m_pac.group(1).strip()
            
            # Peso
            m_pes = re.search(r"Peso[:\s]+(\d+)", texto, re.IGNORECASE)
            if m_pes: datos["peso"] = m_pes.group(1).strip()

            # Fecha (Busca formato DD/MM/YYYY o YYYY-MM-DD)
            m_fec = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
            if m_fec:
                datos["fecha"] = datetime.strptime(m_fec.group(1), "%d/%m/%Y")
        except: pass
    return datos

# --- 2. GENERADOR DE WORD (ESTRUCTURA EXACTA) ---
def generar_word(d):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)

    # Encabezado Paciente
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {d['pac']}\n").bold = True
    p.add_run(f"FECHA: {d['fecha']}\n")
    p.add_run(f"PESO: {d['peso']} kg | ALTURA: {d['alt']} cm")
    doc.add_paragraph("_" * 80)

    # CAPÍTULO I: ECOCARDIOGRAMA
    doc.add_paragraph("CAPÍTULO I: ECOCARDIOGRAMA ESTRUCTURAL").bold = True
    t1 = doc.add_table(rows=2, cols=5)
    t1.style = 'Table Grid'
    # Fila 1
    t1.cell(0,0).text = f"DDVD: {d['ddvd']}"
    t1.cell(0,1).text = f"DDVI: {d['ddvi']}"
    t1.cell(0,2).text = f"DSVI: {d['dsvi']}"
    t1.cell(0,3).text = f"FA: {d['fa']}%"
    t1.cell(0,4).text = f"ES: {d['es']}"
    # Fila 2
    t1.cell(1,0).text = f"SIV: {d['siv']}"
    t1.cell(1,1).text = f"PP: {d['pp']}"
    t1.cell(1,2).text = f"DRAO: {d['drao']}"
    t1.cell(1,3).text = f"AI: {d['ai']}"
    t1.cell(1,4).text = f"AAO: {d['aao']}"

    # CAPÍTULO II: DOPPLER
    doc.add_paragraph("\nCAPÍTULO II: ECO-DOPPLER HEMODINÁMICO").bold = True
    t2 = doc.add_table(rows=5, cols=5)
    t2.style = 'Table Grid'
    h = ["Válvula", "Velocidad (cm/s)", "Grad. Pico", "Grad. Medio", "Insuf."]
    for i, texto in enumerate(h): t2.cell(0,i).text = texto
    
    valvs = [
        ("Tricúspide", d['v_tri'], d['gp_tri'], d['gm_tri'], d['i_tri']),
        ("Pulmonar", d['v_pul'], d['gp_pul'], d['gm_pul'], d['i_pul']),
        ("Mitral", d['v_mit'], d['gp_mit'], d['gm_mit'], d['i_mit']),
        ("Aórtica", d['v_ao'], d['gp_ao'], d['gm_ao'], d['i_ao'])
    ]
    for i, (n, v, gp, gm, ins) in enumerate(valvs, start=1):
        t2.cell(i,0).text = n
        t2.cell(i,1).text = v
        t2.cell(i,2).text = gp
        t2.cell(i,3).text = gm
        t2.cell(i,4).text = ins

    # CAPÍTULO III: CONCLUSIÓN
    doc.add_paragraph("\nCAPÍTULO III: CONCLUSIÓN").bold = True
    doc.add_paragraph(d['conclu']).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    # Firma Digital
    doc.add_paragraph("\n" + "_"*40)
    doc.add_paragraph("Dr. FRANCISCO ALBERTO PASTORE\nMN 74144")
    if os.path.exists("firma_doctor.png"):
        doc.add_picture("firma_doctor.png", width=Inches(1.8))

    # ANEXO DE IMÁGENES 4x2
    doc.add_page_break()
    doc.add_paragraph("ANEXO DE IMÁGENES").bold = True
    t_img = doc.add_table(rows=4, cols=2)
    t_img.style = 'Table Grid'
    for row in t_img.rows:
        row.height = Cm(5) # Espacio para la foto

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out

# --- 3. INTERFAZ STREAMLIT ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🫀 Validación Médica")

pdf = st.file_uploader("Subir PDF", type=["pdf"])
ex = extraer_datos_pdf(pdf)

with st.form("f"):
    st.subheader("📋 Datos Paciente")
    c1, c2, c3, c4 = st.columns(4)
    pac = c1.text_input("Paciente", value=ex["pac"])
    fec = c2.date_input("Fecha", value=ex["fecha"], format="DD/MM/YYYY")
    peso = c3.text_input("Peso (Kg)", value=ex["peso"])
    alt = c4.text_input("Altura (cm)")

    st.divider()
    
    # ECOCARDIOGRAMA (ORDEN EXCEL)
    st.subheader("📏 Ecocardiograma")
    e1, e2, e3, e4, e5 = st.columns(5)
    ddvd = e1.text_input("DDVD")
    ddvi = e2.text_input("DDVI")
    dsvi = e3.text_input("DSVI")
    fa = e4.text_input("FA (%)")
    es = e5.text_input("ES (mm)")
    
    e1b, e2b, e3b, e4b, e5b = st.columns(5)
    siv = e1b.text_input("SIV")
    pp = e2b.text_input("PP")
    drao = e3b.text_input("DRAO")
    ai = e4b.text_input("AI")
    aao = e5b.text_input("AAO")

    st.divider()

    # DOPPLER (ORDEN WORD Y ALINEADO)
    st.subheader("🔊 Eco-Doppler")
    
    # Encabezados de tabla manuales
    h = st.columns([1.5, 2, 2, 2, 2])
    h[0].write("**Válvula**")
    h[1].write("**Velocidad**")
    h[2].write("**Grad. Pico**")
    h[3].write("**Grad. Medio**")
    h[4].write("**Insuficiencia**")

    def fila_doppler(nombre, key):
        cols = st.columns([1.5, 2, 2, 2, 2])
        cols[0].write(nombre)
        v = cols[1].text_input(f"v_{key}", label_visibility="collapsed")
        gp = cols[2].text_input(f"gp_{key}", label_visibility="collapsed")
        gm = cols[3].text_input(f"gm_{key}", label_visibility="collapsed")
        ins = cols[4].selectbox(f"i_{key}", ["No", "Leve", "Mod", "Sev"], label_visibility="collapsed")
        return v, gp, gm, ins

    v_tri, gp_tri, gm_tri, i_tri = fila_doppler("Tricúspide", "tri")
    v_pul, gp_pul, gm_pul, i_pul = fila_doppler("Pulmonar", "pul")
    v_mit, gp_mit, gm_mit, i_mit = fila_doppler("Mitral", "mit")
    v_ao, gp_ao, gm_ao, i_ao = fila_doppler("Aórtica", "ao")

    st.divider()
    conclu = st.text_area("Conclusión y Comentarios", "Dentro de parámetros normales.")
    
    submit = st.form_submit_button("🚀 GENERAR INFORME")

if submit:
    res = {
        "pac": pac.upper(), "fecha": fec.strftime("%d/%m/%Y"), "peso": peso, "alt": alt,
        "ddvd": ddvd, "ddvi": ddvi, "dsvi": dsvi, "fa": fa, "es": es,
        "siv": siv, "pp": pp, "drao": drao, "ai": ai, "aao": aao,
        "v_tri": v_tri, "gp_tri": gp_tri, "gm_tri": gm_tri, "i_tri": i_tri,
        "v_pul": v_pul, "gp_pul": gp_pul, "gm_pul": gm_pul, "i_pul": i_pul,
        "v_mit": v_mit, "gp_mit": gp_mit, "gm_mit": gm_mit, "i_mit": i_mit,
        "v_ao": v_ao, "gp_ao": gp_ao, "gm_ao": gm_ao, "i_ao": i_ao,
        "conclu": conclu
    }
    archivo = generar_word(res)
    st.download_button("📥 Descargar Word", data=archivo, file_name=f"Informe_{pac}.docx")
