
import streamlit as st
from docx import Document
from docx.shared import Pt, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import os
import re
import PyPDF2
from datetime import datetime

# --- 1. EXTRACCIÓN DE DATOS ---
def extraer_datos_pdf(file):
    datos = {"pac": "", "peso": "", "fec": datetime.now()}
    if file:
        try:
            reader = PyPDF2.PdfReader(file)
            texto = ""
            for page in reader.pages: texto += page.extract_text()
            
            # Busca "Paciente: " seguido de letras (evita números)
            m_pac = re.search(r"Paciente[:\s]+([a-zA-Z\s]+)", texto)
            if m_pac: datos["pac"] = m_pac.group(1).strip()
            
            # Busca fecha estándar
            m_fec = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
            if m_fec: datos["fec"] = datetime.strptime(m_fec.group(1), "%d/%m/%Y")
            
            # Busca Peso
            m_pes = re.search(r"Peso[:\s]+(\d+)", texto)
            if m_pes: datos["peso"] = m_pes.group(1).strip()
        except: pass
    return datos

# --- 2. GENERADOR DE WORD ---
def generar_word(d):
    doc = Document()
    
    # Estilo General
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)

    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = t.add_run("ESTUDIO ECOCARDIOGRÁFICO DOPPLER COLOR")
    run_t.bold = True
    run_t.size = Pt(14)

    # Encabezado Paciente
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {d['pac']}\n").bold = True
    p.add_run(f"FECHA: {d['fec_str']}\n")
    p.add_run(f"PESO: {d['peso']} kg | ALTURA: {d['alt']} cm\n")
    doc.add_paragraph("_" * 85)

    # SECCIÓN I: ESTRUCTURA (Basado en DATOSECOCARDIOGRAMA)
    doc.add_paragraph("ANÁLISIS MORFOLÓGICO Y ESTRUCTURAL").bold = True
    t1 = doc.add_table(rows=2, cols=5)
    t1.style = 'Table Grid'
    
    f1 = [("DDVD", d['ddvd']), ("DDVI", d['ddvi']), ("DSVI", d['dsvi']), ("FA", d['fa']+"%"), ("ES", d['es'])]
    f2 = [("SIV", d['siv']), ("PP", d['pp']), ("DRAO", d['drao']), ("AI", d['ai']), ("AAO", d['aao'])]
    
    for i, (l, v) in enumerate(f1): t1.cell(0,i).text = f"{l}: {v}"
    for i, (l, v) in enumerate(f2): t1.cell(1,i).text = f"{l}: {v}"

    # SECCIÓN II: DOPPLER (Basado en DATOSECODOPLER)
    doc.add_paragraph("\nEVALUACIÓN DOPPLER HEMODINÁMICA").bold = True
    t2 = doc.add_table(rows=5, cols=5)
    t2.style = 'Table Grid'
    h = ["Válvula", "Velocidad (cm/s)", "Grad. Pico", "Grad. Medio", "Insuficiencia"]
    for i, text in enumerate(h): t2.cell(0,i).text = text
    
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

    # FIRMA
    doc.add_paragraph("\n\n" + "_"*40)
    doc.add_paragraph("Dr. FRANCISCO ALBERTO PASTORE\nMN 74144")
    if os.path.exists("firma_doctor.png"):
        doc.add_picture("firma_doctor.png", width=Inches(1.8))

    # ANEXO 4x2 (IMÁGENES)
    doc.add_page_break()
    doc.add_paragraph("ANEXO DE IMÁGENES").bold = True
    t_img = doc.add_table(rows=4, cols=2)
    t_img.style = 'Table Grid'
    for row in t_img.rows:
        row.height = Cm(6) # Altura fija para que entren las fotos

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# --- 3. INTERFAZ ---
st.set_page_config(page_title="CardioReport", layout="wide")
st.title("🫀 Sistema de Informes Cardiológicos")

archivo = st.file_uploader("Subir PDF", type=["pdf"])
ex = extraer_datos_pdf(archivo)

with st.form("carga"):
    st.subheader("📋 Datos del Paciente")
    c1, c2, c3, c4 = st.columns(4)
    pac = c1.text_input("Paciente", value=ex["pac"])
    fec = c2.date_input("Fecha", value=ex["fec"])
    peso = c3.text_input("Peso", value=ex["peso"])
    alt = c4.text_input("Altura")

    st.subheader("📏 Mediciones (Ecocardiograma)")
    e1, e2, e3, e4, e5 = st.columns(5)
    ddvd, ddvi, dsvi = e1.text_input("DDVD"), e2.text_input("DDVI"), e3.text_input("DSVI")
    fa, es = e4.text_input("FA (%)"), e5.text_input("ES (mm)")
    
    e1b, e2b, e3b, e4b, e5b = st.columns(5)
    siv, pp, drao = e1b.text_input("SIV"), e2b.text_input("PP"), e3b.text_input("DRAO")
    ai, aao = e4b.text_input("AI"), e5b.text_input("AAO")

    st.subheader("🔊 Hallazgos Doppler")
    # Columnas alineadas para las válvulas
    h = st.columns([1, 1, 1, 1, 1])
    h[0].write("**Válvula**")
    h[1].write("**Velocidad**")
    h[2].write("**Grad. Pico**")
    h[3].write("**Grad. Medio**")
    h[4].write("**Insuficiencia**")

    def fila_v(nombre, k):
        cols = st.columns([1, 1, 1, 1, 1])
        cols[0].write(nombre)
        v = cols[1].text_input(f"v_{k}", label_visibility="collapsed")
        gp = cols[2].text_input(f"gp_{k}", label_visibility="collapsed")
        gm = cols[3].text_input(f"gm_{k}", label_visibility="collapsed")
        ins = cols[4].selectbox(f"i_{k}", ["No", "Leve", "Mod", "Sev"], label_visibility="collapsed")
        return v, gp, gm, ins

    v_tri, gp_tri, gm_tri, i_tri = fila_v("Tricúspide", "t")
    v_pul, gp_pul, gm_pul, i_pul = fila_v("Pulmonar", "p")
    v_mit, gp_mit, gm_mit, i_mit = fila_v("Mitral", "m")
    v_ao, gp_ao, gm_ao, i_ao = fila_v("Aórtica", "a")

    submit = st.form_submit_button("🚀 GENERAR INFORME")

if submit:
    res = {
        "pac": pac.upper(), "fec_str": fec.strftime("%d/%m/%Y"), "peso": peso, "alt": alt,
        "ddvd": ddvd, "ddvi": ddvi, "dsvi": dsvi, "fa": fa, "es": es,
        "siv": siv, "pp": pp, "drao": drao, "ai": ai, "aao": aao,
        "v_tri": v_tri, "gp_tri": gp_tri, "gm_tri": gm_tri, "i_tri": i_tri,
        "v_pul": v_pul, "gp_pul": gp_pul, "gm_pul": gm_pul, "i_pul": i_pul,
        "v_mit": v_mit, "gp_mit": gp_mit, "gm_mit": gm_mit, "i_mit": i_mit,
        "v_ao": v_ao, "gp_ao": gp_ao, "gm_ao": gm_ao, "i_ao": i_ao
    }
    st.download_button("📥 Descargar Word", data=generar_word(res), file_name=f"Informe_{pac}.docx")
