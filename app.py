
import streamlit as st
from docx import Document
from docx.shared import Pt, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import os
import re
import PyPDF2
from datetime import datetime

# --- LÓGICA DE EXTRACCIÓN MEJORADA ---
def extraer_datos_pdf(file):
    datos = {"pac": "", "peso": "", "fec": datetime.now()}
    if file:
        try:
            reader = PyPDF2.PdfReader(file)
            texto = ""
            for page in reader.pages: texto += page.extract_text()
            
            # Buscar Paciente (evita números sueltos)
            m_pac = re.search(r"Paciente[:\s]+([a-zA-Z\s,]+)", texto)
            if m_pac: datos["pac"] = m_pac.group(1).strip()
            
            # Buscar Fecha en el texto
            m_fec = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
            if m_fec: datos["fec"] = datetime.strptime(m_fec.group(1), "%d/%m/%Y")
            
            # Buscar Peso
            m_pes = re.search(r"Peso[:\s]+(\d+)", texto)
            if m_pes: datos["peso"] = m_pes.group(1).strip()
        except: pass
    return datos

# --- GENERADOR DE WORD ---
def generar_word(d):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)

    # Encabezado Médico
    tit = doc.add_paragraph()
    tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = tit.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.size = Pt(14)

    # Datos del Paciente
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {d['pac']}\n").bold = True
    p.add_run(f"FECHA: {d['fec_str']}\n")
    p.add_run(f"PESO: {d['peso']} kg | ALTURA: {d['alt']} cm")
    doc.add_paragraph("_" * 85)

    # CAPÍTULO I: ECOCARDIOGRAMA
    doc.add_paragraph("CAPÍTULO I: ANÁLISIS ESTRUCTURAL").bold = True
    t1 = doc.add_table(rows=2, cols=5)
    t1.style = 'Table Grid'
    meds = [
        [("DDVD", d['ddvd']), ("DDVI", d['ddvi']), ("DSVI", d['dsvi']), ("FA", d['fa']+"%"), ("ES", d['es'])],
        [("SIV", d['siv']), ("PP", d['pp']), ("DRAO", d['drao']), ("AI", d['ai']), ("AAO", d['aao'])]
    ]
    for r in range(2):
        for c in range(5):
            t1.cell(r,c).text = f"{meds[r][c][0]}: {meds[r][c][1]}"

    # CAPÍTULO II: DOPPLER (GRADIENTE PICO Y MEDIO)
    doc.add_paragraph("\nCAPÍTULO II: EVALUACIÓN HEMODINÁMICA").bold = True
    t2 = doc.add_table(rows=5, cols=5)
    t2.style = 'Table Grid'
    cab = ["Válvula", "Velocidad", "Grad. Pico", "Grad. Medio", "Insuf."]
    for i, h in enumerate(cab): t2.cell(0,i).text = h
    
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

    # FIRMA DIGITAL
    doc.add_paragraph("\n" + "_"*40)
    doc.add_paragraph("Dr. FRANCISCO ALBERTO PASTORE\nMN 74144")
    if os.path.exists("firma_doctor.png"):
        doc.add_picture("firma_doctor.png", width=Inches(1.8))

    # ANEXO 4x2
    doc.add_page_break()
    doc.add_paragraph("ANEXO DE IMÁGENES").bold = True
    t_img = doc.add_table(rows=4, cols=2)
    t_img.style = 'Table Grid'
    for row in t_img.rows: row.height = Cm(5.5)

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# --- INTERFAZ ---
st.set_page_config(page_title="CardioReport", layout="wide")
st.title("🫀 Generador de Informes Médicos")

pdf_file = st.file_uploader("Subir PDF", type=["pdf"])
ex = extraer_datos_pdf(pdf_file)

with st.form("main"):
    st.subheader("📋 Filiación")
    c1, c2, c3, c4 = st.columns(4)
    pac = c1.text_input("Paciente", value=ex["pac"])
    fec = c2.date_input("Fecha de Estudio", value=ex["fec"])
    peso = c3.text_input("Peso", value=ex["peso"])
    alt = c4.text_input("Altura")

    st.subheader("📏 Ecocardiograma")
    e1, e2, e3, e4, e5 = st.columns(5)
    ddvd, ddvi, dsvi = e1.text_input("DDVD"), e2.text_input("DDVI"), e3.text_input("DSVI")
    fa, es = e4.text_input("FA"), e5.text_input("ES")
    e1b, e2b, e3b, e4b, e5b = st.columns(5)
    siv, pp, drao = e1b.text_input("SIV"), e2b.text_input("PP"), e3b.text_input("DRAO")
    ai, aao = e4b.text_input("AI"), e5b.text_input("AAO")

    st.subheader("🔊 Doppler")
    # Tabla manual para evitar desfasaje
    h = st.columns([1.5, 2, 2, 2, 2])
    h[0].write("**Válvula**")
    h[1].write("**Velocidad**")
    h[2].write("**Grad. Pico**")
    h[3].write("**Grad. Medio**")
    h[4].write("**Insuficiencia**")

    def row_d(label, key):
        cols = st.columns([1.5, 2, 2, 2, 2])
        cols[0].write(label)
        v = cols[1].text_input(f"v_{key}", label_visibility="collapsed")
        gp = cols[2].text_input(f"gp_{key}", label_visibility="collapsed")
        gm = cols[3].text_input(f"gm_{key}", label_visibility="collapsed")
        ins = cols[4].selectbox(f"i_{key}", ["No", "Leve", "Mod", "Sev"], label_visibility="collapsed")
        return v, gp, gm, ins

    v_tri, gp_tri, gm_tri, i_tri = row_d("Tricúspide", "tri")
    v_pul, gp_pul, gm_pul, i_pul = row_d("Pulmonar", "pul")
    v_mit, gp_mit, gm_mit, i_mit = row_d("Mitral", "mit")
    v_ao, gp_ao, gm_ao, i_ao = row_d("Aórtica", "ao")

    conclu = st.text_area("Conclusión", "Dentro de parámetros normales.")
    btn = st.form_submit_button("🚀 GENERAR WORD")

if btn:
    res = {
        "pac": pac.upper(), "fec_str": fec.strftime("%d/%m/%Y"), "peso": peso, "alt": alt,
        "ddvd": ddvd, "ddvi": ddvi, "dsvi": dsvi, "fa": fa, "es": es,
        "siv": siv, "pp": pp, "drao": drao, "ai": ai, "aao": aao,
        "v_tri": v_tri, "gp_tri": gp_tri, "gm_tri": gm_tri, "i_tri": i_tri,
        "v_pul": v_pul, "gp_pul": gp_pul, "gm_pul": gm_pul, "i_pul": i_pul,
        "v_mit": v_mit, "gp_mit": gp_mit, "gm_mit": gm_mit, "i_mit": i_mit,
        "v_ao": v_ao, "gp_ao": gp_ao, "gm_ao": gm_ao, "i_ao": i_ao,
        "conclu": conclu
    }
    st.download_button("📥 Descargar", data=generar_word(res), file_name=f"Informe_{pac}.docx")
