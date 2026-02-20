
import streamlit as st
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import os
import re
import PyPDF2
from datetime import datetime

# --- 1. LÓGICA DE EXTRACCIÓN MEJORADA ---
def extraer_datos_pdf(file):
    texto_completo = ""
    datos = {}
    if file is not None:
        try:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                texto_completo += page.extract_text()
            
            # Buscamos los datos ignorando mayúsculas/minúsculas y espacios extra
            patrones = {
                "pac": r"Paciente[:\s]+(.*)",
                "peso": r"Peso[:\s]+(\d+)",
                "altura": r"Altura[:\s]+(\d+)",
                "ddvi": r"DDVI[:\s]+(\d+)",
                "siv": r"SIV[:\s]+(\d+)",
                "pp": r"PP[:\s]+(\d+)",
                "fa": r"FA[:\s]+(\d+)",
                "ai": r"AI[:\s]+(\d+)"
            }
            
            for clave, patron in patrones.items():
                match = re.search(patron, texto_completo, re.IGNORECASE)
                if match:
                    datos[clave] = match.group(1).strip()
        except:
            st.error("Error al leer el contenido del PDF.")
    return datos

# --- 2. CÁLCULO SC ---
def calcular_sc_dubois(peso, altura):
    try:
        p = float(peso)
        a = float(altura)
        if p > 0 and a > 0:
            return 0.007184 * (p**0.425) * (a**0.725)
    except:
        pass
    return 0

# --- 3. GENERADOR DE WORD PROFESIONAL ---
def generar_word(datos):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Identificación
    p_id = doc.add_paragraph()
    p_id.add_run(f"PACIENTE: {datos['pac']}\n").bold = True
    p_id.add_run(f"FECHA: {datos['fecha']}\n")
    p_id.add_run(f"PESO: {datos['peso']} kg | ALTURA: {datos['altura']} cm | SC: {datos['sc']:.2f} m²")
    doc.add_paragraph("_" * 75)

    # CAPÍTULO I
    doc.add_paragraph("\nCAPÍTULO I: ECOCARDIOGRAMA ESTRUCTURAL").bold = True
    t1 = doc.add_table(rows=3, cols=4)
    items = [
        ("DDVD", datos['ddvd']), ("DDVI", datos['ddvi']), ("DSVI", datos['dsvi']), ("FA/FEy", datos['fey']),
        ("ES", datos['es']), ("SIV", datos['siv']), ("PP", datos['pp']), ("DRAO", datos['drao']),
        ("AI", datos['ai']), ("AAO", datos['aao']), ("", ""), ("", "")
    ]
    idx = 0
    for r in range(3):
        for c in range(4):
            if idx < len(items):
                t1.cell(r, c).text = f"{items[idx][0]}: {items[idx][1]}"
                idx += 1

    # CAPÍTULO II
    doc.add_paragraph("\nCAPÍTULO II: ECO-DOPPLER HEMODINÁMICO").bold = True
    t2 = doc.add_table(rows=5, cols=4)
    headers = ["Válvula", "Vel. cm/s", "Grad. P/M", "Insuf."]
    for i, h in enumerate(headers): t2.cell(0,i).text = h
    
    valvs = [
        ("Tricúspide", datos['v_tri'], datos['g_tri'], datos['i_tri']),
        ("Pulmonar", datos['v_pul'], datos['g_pul'], datos['i_pul']),
        ("Mitral", datos['v_mit'], datos['g_mit'], datos['i_mit']),
        ("Aórtica", datos['v_ao'], datos['g_ao'], datos['i_ao'])
    ]
    for i, (n, v, g, ins) in enumerate(valvs, start=1):
        t2.cell(i,0).text = n
        t2.cell(i,1).text = v
        t2.cell(i,2).text = g
        t2.cell(i,3).text = ins

    # CONCLUSIÓN Y FIRMA
    doc.add_paragraph("\nCAPÍTULO III: CONCLUSIÓN").bold = True
    doc.add_paragraph(datos['conclusion']).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_paragraph("\n" + "_"*40)
    doc.add_paragraph("Dr. FRANCISCO ALBERTO PASTORE\nMN 74144")
    if os.path.exists("firma_doctor.png"):
        doc.add_picture("firma_doctor.png", width=Inches(1.5))

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# --- 4. INTERFAZ STREAMLIT ---
st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("🫀 Validación Médica")

archivo_pdf = st.file_uploader("1. Suba el PDF del estudio", type=["pdf"])
datos_ex = extraer_datos_pdf(archivo_pdf)

# Iniciamos el formulario
with st.form("main_form"):
    st.subheader("📋 Datos Paciente")
    c1, c2, c3, c4 = st.columns(4)
    pac = c1.text_input("Paciente", value=datos_ex.get("pac", ""))
    fec = c2.date_input("Fecha", datetime.now())
    pes = c3.text_input("Peso (Kg)", value=datos_ex.get("peso", ""))
    alt = c4.text_input("Altura (cm)", value=datos_ex.get("altura", ""))
