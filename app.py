
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
    datos = {"pac": "", "peso": "", "fecha": datetime.now()}
    if file:
        try:
            reader = PyPDF2.PdfReader(file)
            texto = ""
            for page in reader.pages: texto += page.extract_text()
            
            # Buscamos nombre: evita capturar números de protocolo
            lineas = texto.split('\n')
            for linea in lineas:
                if "Paciente" in linea or "Nombre" in linea:
                    nombre = linea.split(':')[-1].strip()
                    # Si el resultado es solo números, seguimos buscando
                    if not nombre.isdigit():
                        datos["pac"] = nombre
                        break
            
            # Fecha específica del informe
            m_fec = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
            if m_fec:
                datos["fecha"] = datetime.strptime(m_fec.group(1), "%d/%m/%Y")
        except: pass
    return datos

# --- 2. GENERADOR DE WORD ---
def generar_word(d):
    doc = Document()
    
    # Configuración de fuente Arial para todo el doc
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(10)

    # ENCABEZADO
    header = doc.add_paragraph()
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_h = header.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_h.bold = True
    run_h.size = Pt(14)

    # DATOS FILIATORIOS
    p = doc.add_paragraph()
    p.add_run(f"\nPACIENTE: {d['pac']}\n").bold = True
    p.add_run(f"FECHA DE ESTUDIO: {d['fecha']}\n")
    p.add_run(f"PESO: {d['peso']} kg | ALTURA: {d['alt']} cm | SC: {d['sc']} m²\n")
    doc.add_paragraph("_" * 85)

    # CAPÍTULO I: ESTRUCTURA
    doc.add_paragraph("CAPÍTULO I: ANÁLISIS MORFOLÓGICO Y ESTRUCTURAL").bold = True
    doc.add_paragraph("Se realiza estudio ecocardiográfico observando las siguientes dimensiones:")
    
    t1 = doc.add_table(rows=2, cols=5)
    t1.style = 'Table Grid'
    vals1 = [("DDVD", d['ddvd']), ("DDVI", d['ddvi']), ("DSVI", d['dsvi']), ("FA/FEy", d['fa']+"%"), ("ES", d['es'])]
    vals2 = [("SIV", d['siv']), ("PP", d['pp']), ("DRAO", d['drao']), ("AI", d['ai']), ("AAO", d['aao'])]
    
    for i, (lab, val) in enumerate(vals1): t1.cell(0,i).text = f"{lab}: {val}"
    for i, (lab, val) in enumerate(vals2): t1.cell(1,i).text = f"{lab}: {val}"

    # CAPÍTULO II: DOPPLER
    doc.add_paragraph("\nCAPÍTULO II: EVALUACIÓN HEMODINÁMICA (DOPPLER)").bold = True
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
        for j, val in enumerate([n, v, gp, gm, ins]): t2.cell(i,j).text = str(val)

    # CAPÍTULO III: CONCLUSIÓN
    doc.add_paragraph("\nCAPÍTULO III: CONCLUSIÓN DIAGNÓSTICA").bold = True
    p_conclu = doc.add_paragraph(d['conclu'])
    p_conclu.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # FIRMA
    doc.add_paragraph("\n\n" + "_"*40)
    doc.add_paragraph("Dr. FRANCISCO ALBERTO PASTORE\nMN 74144 - Médico Cardiólogo")
    if os.path.exists("firma_doctor.png"):
        doc.add_picture("firma_doctor.png", width=Inches(1.8))

    # ANEXO 4x2
    doc.add_page_break()
    doc.add_paragraph("ANEXO DE IMÁGENES").bold = True
    t_img = doc.add_table(rows=4, cols=2)
    t_img.style = 'Table Grid'
    for row in t_img.rows:
        row.height = Cm(6) # Tamaño grande para las fotos

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out

# --- 3. INTERFAZ ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🫀 Generador de Informes Cardiológicos")

file = st.file_uploader("Subir PDF del estudio", type=["pdf"])
ex = extraer_datos_pdf(file)

with st.form("form_medico"):
    c1, c2, c3, c4 = st.columns(4)
    pac = c1.text_input("Nombre del Paciente", value=ex["pac"])
    fec = c2.date_input("Fecha de Estudio", value=ex["fecha"])
    peso = c3.text_input("Peso (Kg)", value=ex["peso"])
    alt = c4.text_input("Altura (cm)")

    st.subheader("📏 Mediciones Estructurales")
    e1, e2, e3, e4, e5 = st.columns(5)
    ddvd, ddvi, dsvi = e1.text_input("DDVD"), e2.text_input("DDVI"), e3.text_input("DSVI")
    fa, es = e4.text_input("FA (%)"), e5.text_input("ES (mm)")
    
    e1b, e2b, e3b, e4b, e5b = st.columns(5)
    siv, pp, drao = e1b.text_input("SIV"), e2b.text_input("PP"), e3b.text_input("DRAO")
    ai, aao = e4b.text_input("AI"), e5b.text_input("AAO")

    st.subheader("🔊 Hallazgos Doppler")
    # Tabla visualmente alineada
    col_v, col_vel, col_gp, col_gm, col_ins = st.columns([1,1,1,1,1])
    col_v.write("**Válvula**")
    col_vel.write("**Vel. cm/s**")
    col_gp.write("**Grad. Pico**")
    col_gm.write("**Grad. Medio**")
    col_ins.write("**Insuficiencia**")

    def fila(nombre, k):
        c = st.columns([1,1,1,1,1])
        c[0].write(nombre)
        v = c[1].text_input(f"v_{k}", label_visibility="collapsed")
        gp = c[2].text_input(f"gp_{k}", label_visibility="collapsed")
        gm = c[3].text_input(f"gm_{k}", label_visibility="collapsed")
        ins = c[4].selectbox(f"i_{k}", ["No", "Leve", "Mod", "Sev"], label_visibility="collapsed")
        return v, gp, gm, ins

    v_tri, gp_tri, gm_tri, i_tri = fila("Tricúspide", "t")
    v_pul, gp_pul, gm_pul, i_pul = fila("Pulmonar", "p")
    v_mit, gp_mit, gm_mit, i_mit = fila("Mitral", "m")
    v_ao, gp_ao, gm_ao, i_ao = fila("Aórtica", "a")

    conclu = st.text_area("Conclusión Final", "Ecocardiograma Doppler color con parámetros conservados.")
    
    submit = st.form_submit_button("🚀 GENERAR INFORME PROFESIONAL")

if submit:
    sc = "" # Aquí podrías agregar el cálculo de SC si lo necesitas
    res = {
        "pac": pac.upper(), "fecha": fec.strftime("%d/%m/%Y"), "peso": peso, "alt": alt, "sc": "---",
        "ddvd": ddvd, "ddvi": ddvi, "dsvi": dsvi, "fa": fa, "es": es,
        "siv": siv, "pp": pp, "drao": drao, "ai": ai, "aao": aao,
        "v_tri": v_tri, "gp_tri": gp_tri, "gm_tri": gm_tri, "i_tri": i_tri,
        "v_pul": v_pul, "gp_pul": gp_pul, "gm_pul": gm_pul, "i_pul": i_pul,
        "v_mit": v_mit, "gp_mit": gp_mit, "gm_mit": gm_mit, "i_mit": i_mit,
        "v_ao": v_ao, "gp_ao": gp_ao, "gm_ao": gm_ao, "i_ao": i_ao,
        "conclu": conclu
    }
    st.download_button("📥 DESCARGAR INFORME", data=generar_word(res), file_name=f"Informe_{pac}.docx")
