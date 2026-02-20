
import streamlit as st
from docx import Document
from docx.shared import Pt, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import os
import re
import PyPDF2
from datetime import datetime

# --- EXTRACCIÓN MEJORADA ---
def extraer_datos_pdf(file):
    datos = {"pac": "", "fec": datetime.now(), "peso": ""}
    if file:
        try:
            reader = PyPDF2.PdfReader(file)
            texto = "".join([p.extract_text() for p in reader.pages])
            m_pac = re.search(r"Paciente[:\s]+([a-zA-Z\s]+)", texto)
            if m_pac: datos["pac"] = m_pac.group(1).strip().upper()
            m_fec = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
            if m_fec: datos["fec"] = datetime.strptime(m_fec.group(1), "%d/%m/%Y")
        except: pass
    return datos

# --- GENERADOR DE INFORME REDACTADO ---
def generar_word_profesional(d):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Encabezado centrado
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = titulo.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.size = Pt(14)

    # Filiación
    filiacion = doc.add_paragraph()
    filiacion.add_run(f"PACIENTE: {d['pac']}\n").bold = True
    filiacion.add_run(f"FECHA: {d['fec_str']}  |  PESO: {d['peso']} kg  |  ALTURA: {d['alt']} cm\n")
    doc.add_paragraph("_" * 85)

    # CUERPO DEL INFORME (Redacción Médica)
    doc.add_paragraph("HALLAZGOS ECOCARDIOGRÁFICOS:").bold = True
    
    texto_estructural = (
        f"Se observa ventrículo izquierdo con diámetro diastólico de {d['ddvi']} mm y sistólico de {d['dsvi']} mm. "
        f"La fracción de acortamiento se calcula en {d['fa']}%, con una excursión sistólica del anillo tricúspideo (ES) de {d['es']} mm. "
        f"El espesor del septum interventricular (SIV) es de {d['siv']} mm y la pared posterior (PP) de {d['pp']} mm. "
        f"La raíz aórtica mide {d['drao']} mm, la aurícula izquierda {d['ai']} mm y la aorta ascendente {d['aao']} mm. "
        f"El diámetro del ventrículo derecho (DDVD) es de {d['ddvd']} mm."
    )
    p1 = doc.add_paragraph(texto_estructural)
    p1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    doc.add_paragraph("\nESTUDIO DOPPLER HEMODINÁMICO:").bold = True
    
    doppler_intro = "Al análisis Doppler color y espectral, se registran los siguientes parámetros transvalvulares:"
    doc.add_paragraph(doppler_intro)

    # Tabla Doppler Estilizada
    t2 = doc.add_table(rows=5, cols=5)
    t2.style = 'Table Grid'
    h = ["Válvula", "Veloc. (cm/s)", "Grad. Pico", "Grad. Medio", "Insuficiencia"]
    for i, txt in enumerate(h): t2.cell(0,i).text = txt
    
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

    # Conclusión
    if d['conclu']:
        doc.add_paragraph("\nCONCLUSIÓN:").bold = True
        p_c = doc.add_paragraph(d['conclu'])
        p_c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Firma
    doc.add_paragraph("\n\n" + "_"*40)
    doc.add_paragraph("Dr. FRANCISCO ALBERTO PASTORE\nMN 74144 - Médico Cardiólogo")
    if os.path.exists("firma_doctor.png"):
        doc.add_picture("firma_doctor.png", width=Inches(1.8))

    # ANEXO IMÁGENES 4x2
    doc.add_page_break()
    doc.add_paragraph("ANEXO DE IMÁGENES (CAPTURAS DE PANTALLA)").bold = True
    t_img = doc.add_table(rows=4, cols=2)
    t_img.style = 'Table Grid'
    for row in t_img.rows:
        row.height = Cm(6) # Espacio real para fotos

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🫀 Sistema de Redacción de Informes")

archivo = st.file_uploader("Subir PDF del equipo", type=["pdf"])
ex = extraer_datos_pdf(archivo)

with st.form("main"):
    col1, col2 = st.columns(2)
    pac = col1.text_input("Paciente", value=ex["pac"])
    fec = col2.date_input("Fecha", value=ex["fec"])
    peso = col1.text_input("Peso")
    alt = col2.text_input("Altura")

    st.subheader("📏 Datos Estructurales (Ecocardiograma)")
    e1, e2, e3, e4, e5 = st.columns(5)
    ddvd, ddvi, dsvi = e1.text_input("DDVD"), e2.text_input("DDVI"), e3.text_input("DSVI")
    fa, es = e4.text_input("FA (%)"), e5.text_input("ES (mm)")
    e1b, e2b, e3b, e4b, e5b = st.columns(5)
    siv, pp, drao = e1b.text_input("SIV"), e2b.text_input("PP"), e3b.text_input("Raíz Ao")
    ai, aao = e4b.text_input("AI"), e5b.text_input("Ao Asc.")

    st.subheader("🔊 Datos Hemodinámicos (Doppler)")
    h = st.columns([1, 1, 1, 1, 1])
    h[0].write("**Válvula**"); h[1].write("**Velocidad**"); h[2].write("**G. Pico**"); h[3].write("**G. Medio**"); h[4].write("**Insuf.**")
    
    def f_doppler(nombre, k):
        c = st.columns([1, 1, 1, 1, 1])
        c[0].write(nombre)
        return c[1].text_input(f"v_{k}", label_visibility="collapsed"), \
               c[2].text_input(f"p_{k}", label_visibility="collapsed"), \
               c[3].text_input(f"m_{k}", label_visibility="collapsed"), \
               c[4].selectbox(f"i_{k}", ["No", "Leve", "Mod", "Sev"], label_visibility="collapsed")

    v_tri, gp_tri, gm_tri, i_tri = f_doppler("Tricúspide", "t")
    v_pul, gp_pul, gm_pul, i_pul = f_doppler("Pulmonar", "p")
    v_mit, gp_mit, gm_mit, i_mit = f_doppler("Mitral", "m")
    v_ao, gp_ao, gm_ao, i_ao = f_doppler("Aórtica", "a")

    conclu = st.text_area("Conclusión Final (Opcional)", "")
    btn = st.form_submit_button("🚀 REDACTAR INFORME PROFESIONAL")

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
    st.download_button("📥 Descargar Word Redactado", data=generar_word_profesional(res), file_name=f"Informe_{pac}.docx")
