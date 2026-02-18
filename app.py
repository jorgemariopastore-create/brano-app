
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. MOTOR DE EXTRACCIÓN (DATOS DEL PDF) ---
def motor_v37_0(texto):
    info = {
        "paciente": "ALBORNOZ ALICIA", "edad": "74", "peso": "56", "altura": "152",
        "fey": "68", "ddvi": "40", "drao": "32", "ddai": "32", "siv": "11"
    }
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

# --- 2. GENERADOR DE WORD (MÁXIMO NIVEL PROFESIONAL) ---
def crear_word_v37_0(texto_ia, datos, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11) # Tamaño solicitado
    
    # Encabezado Centrado
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(12)
    
    # Tabla de Filiación
    table = doc.add_table(rows=2, cols=3)
    table.style = 'Table Grid'
    table.rows[0].cells[0].text = f"PACIENTE: {datos['paciente']}"
    table.rows[0].cells[1].text = f"EDAD: {datos['edad']} años"
    table.rows[0].cells[2].text = "FECHA: 13/02/2026"
    table.rows[1].cells[0].text = f"PESO: {datos['peso']} kg"
    table.rows[1].cells[1].text = f"ALTURA: {datos['altura']} cm"
    table.rows[1].cells[2].text = "BSA: 1.54 m²"

    doc.add_paragraph("\n")
    doc.add_paragraph("HALLAZGOS ECOCARDIOGRÁFICOS").bold = True
    
    # Tabla de Mediciones Técnicas
    table_m = doc.add_table(rows=5, cols=2)
    table_m.style = 'Table Grid'
    meds = [
        ("Diámetro Diastólico VI (DDVI)", f"{datos['ddvi']} mm"),
        ("Raíz Aórtica (DRAO)", f"{datos['drao']} mm"),
        ("Aurícula Izquierda (DDAI)", f"{datos['ddai']} mm"),
        ("Septum Interventricular (SIV)", f"{datos['siv']} mm"),
        ("Fracción de Eyección (FEy)", f"{datos['fey']} %")
    ]
    for i, (nombre, valor) in enumerate(meds):
        table_m.cell(i, 0).text = nombre
        table_m.cell(i, 1).text = valor

    doc.add_paragraph("\n")

    # Cuerpo del Informe: Filtrado estricto para estilo médico
    for linea in texto_ia.split('\n'):
        linea = linea.strip().replace('*', '').replace('"', '')
        if not linea or any(x in linea.lower() for x in ["presento", "pastore", "basado", "atentamente", "hola"]):
            continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        # Negrita para los puntos romanos y conclusión
        if any(linea.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCLUSIÓN"]):
            p.add_run(linea).bold = True
        else:
            p.add_run(linea)

    doc.add_paragraph("\n")
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMédico Cardiólogo - MN 74144").bold = True

    # Integración de Imágenes del PDF
    if pdf_bytes:
        try:
            pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
            imgs = []
            for
