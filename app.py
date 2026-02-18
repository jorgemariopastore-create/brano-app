
import streamlit as st
from groq import Groq
import fitz
import io
import re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def motor_v37_6(txt):
    d = {"paciente": "ALBORNOZ ALICIA", "edad": "74", "peso": "56", "altura": "152", "fey": "68", "ddvi": "40", "drao": "32", "ddai": "32", "siv": "11"}
    if txt:
        n = re.search(r"(?:Paciente|Name|Nombre)\s*[:=-]?\s*([^<\r\n]*)", txt, re.I)
        if n: d["paciente"] = n.group(1).strip().upper()
        for k, p in [("ddvi","DDVI"), ("drao","DRAO"), ("ddai","DDAI"), ("siv","DDSIV")]:
            m = re.search(rf"\"{p}\"\s*,\s*\"(\d+)\"", txt, re.I)
            if m: d[k] = m.group(1)
    return d

def crear_doc(reporte, datos, pdf_b):
    doc = Document()
    s = doc.styles['Normal']
    s.font.name, s.font.size = 'Arial', Pt(11)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    r.bold, r.font.size = True, Pt(12)
    
    tbl = doc.add_table(rows=2, cols=3)
    tbl.style = 'Table Grid'
    c = [f"PACIENTE: {datos['paciente']}", f"EDAD: {datos['edad']} años", "FECHA: 13/02/2026", f"PESO: {datos['peso']} kg", f"ALTURA: {datos['altura']} cm", "BSA: 1.54 m²"]
    for i, texto in enumerate(c): tbl.cell(i//3, i%3).text = texto

    doc.add_paragraph("\n")
    tm = doc.add_table(rows=5, cols=2); tm.style = 'Table Grid'
    ms = [("Diámetro Diastólico VI (DDVI)", f"{datos['ddvi']} mm"), ("Raíz Aórtica (DRAO)", f"{datos['drao']} mm"), ("Aurícula Izquierda (DDAI)", f"{datos['ddai']} mm"), ("Septum Interventricular (SIV)", f"{datos['siv']} mm"), ("Fracción de Eyección (FEy)", f"{datos['fey']} %")]
    for i, (n, v) in enumerate(ms): tm.cell(i,0).text, tm.cell(i,1).text = n, v

    doc.add_paragraph("\n")
    for l in reporte.split('\n'):
        l = l.strip().replace('*', '').replace('"', '')
        if not l or any(x in l.lower() for x in ["presento", "pastore", "basado"]): continue
        p
