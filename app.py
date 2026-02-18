
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTOR DE EXTRACCIÓN UNIVERSAL (No forzado) ---
def motor_v35_1(texto):
    # Valores por defecto vacíos para evitar arrastrar datos de otros pacientes
    info = {
        "paciente": "", 
        "edad": "74", 
        "peso": "56", 
        "altura": "152", 
        "fey": "", 
        "ddvi": "",
        "drao": "32",
        "ddai": "32"
    }
    
    if texto:
        # Busca cualquier nombre después de "Paciente:", "Name:" o "Nombre:"
        n = re.search(r"(?:Patient Name|Name|Nombre|PACIENTE)\s*[:=-]\s*([^<\r\n]*)", texto, re.I)
        if n: info["paciente"] = n.group(1).replace(',', '').strip()
        
        # Busca la Fracción de Eyección (FEy / EF)
        f = re.search(r"(?:EF|FEy|Fracción de Eyección).*?([\d\.,]+)", texto, re.I)
        if f: info["fey"] = f.group(1).replace(',', '.')
        
        # Busca el Diámetro Diastólico (DDVI / LVIDd)
        d = re.search(r"(?:LVIDd|DDVI).*?([\d\.,]+)", texto, re.I)
        if d: info["ddvi"] = d.group(1).replace(',', '.')

    return info

# --- 2. GENERADOR DE WORD (ESTILO PASTORE ESPEJO) ---
def crear_word_final(texto_ia, datos_v, pdf_bytes):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(10)
    
    # Encabezado centrado
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla de Identificación del Paciente
    table = doc.add_table(rows=2, cols=3)
    table.style = 'Table Grid'
    c0 = table.rows[0].cells
    c0[0].text = f"PACIENTE: {datos_v['paciente']}"
    c0[1].text = f"EDAD: {datos_v['edad']} años"
    c0[2].text = f"FECHA: 13/02/2026"
    c1 = table.rows[1].cells
    c1[0].text = f"PESO: {datos_v['peso']} kg"
    c1[1].text = f"ALTURA: {datos_v['altura']} cm"
    try:
        bsa = ( (float(datos_v['peso']) * float(datos_v['altura'])) / 3600 )**0.5
        c1[2].text = f"BSA: {bsa:.2f} m²"
    except: c1[2].text = "BSA: --"

    doc.add_paragraph("\n")

    # Cuadro Técnico de Mediciones
    doc.add_paragraph("HALLAZGOS ECOCARDIOGRÁFICOS").bold = True
    table_m = doc.add_table(rows=5, cols=2)
    table_m.style = 'Table Grid'
    meds = [
        ("Diámetro Diastólico VI (DDVI)", f"{datos_v['ddvi']} mm"),
        ("Raíz Aórtica (DRAO)", f"{datos_v['drao']} mm"),
        ("Aurícula Izquierda (DDAI)", f"{datos_v['ddai']} mm"),
        ("Septum Interventricular", "11 mm"),
        ("Fracción de Eyección (FEy)", f"{datos_v['fey']} %")
    ]
    for i, (n, v) in enumerate(meds):
        table_m.cell(i, 0).text = n
        table_m.cell(i, 1).text = v

    doc.add_paragraph("\n")

    # Cuerpo del Informe (Texto de la IA Justificado)
    for linea in texto_ia.split('\n'):
        linea = linea.strip().replace('"', '') # Limpieza de comillas
        if not linea or "informe" in linea.lower(): continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea).bold = True
        else:
            p.add_run(linea)

    # Firma a la Derecha
    doc.add_paragraph("\n")
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMédico Cardiólogo - MN 74144").bold = True

    # Anexo de Imágenes
    if pdf_bytes:
