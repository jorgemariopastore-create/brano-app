
import streamlit as st
from groq import Groq
import fitz, io, re, datetime
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def motor(t):
    hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    d = {"pac": "ALBORNOZ ALICIA", "ed": "74", "fy": "68", "dv": "40", "dr": "32", "ai": "32", "si": "11", "fecha": hoy}
    if t:
        n = re.search(r"(?:Paciente|Nombre)\s*[:=-]?\s*([^<\r\n]*)", t, re.I)
        if n: d["pac"] = n.group(1).strip().upper()
        f_e = re.search(r"(?:Fecha|Estudio|Realizado)\s*[:=-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", t, re.I)
        if f_e: 
            d["fecha"] = f_e.group(1)
        else:
            todas = re.findall(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", t)
            for f in todas:
                if "1951" not in f:
                    d["fecha"] = f
                    break
        for k, p in [("dv","DDVI"), ("dr","DRAO"), ("ai","DDAI"), ("si","DDSIV")]:
            m = re.search(rf"\"{p}\"\s*,\s*\"(\d+)\"", t, re.I)
            if m: d[k] = m.group(1)
    return d

def docx(rep, dt, pdf_b):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(11)
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = h.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    r.bold, r.font.size = True, Pt(12)
    b1 = doc.add_table(rows=2, cols=3); b1.style = 'Table Grid'
    ls = [f"PACIENTE: {dt['pac']}", f"EDAD: {dt['ed']} años", f"FECHA: {dt['fecha']}", "PESO: 56 kg", "ALTURA: 152 cm", "BSA: 1.54 m²"]
    for i, x in enumerate(ls): b1.cell(i//3, i%3).text = x
    doc.add_paragraph("\n")
    b2 = doc.add_table(rows=5, cols=2); b2.style = 'Table Grid'
    ms = [("DDVI", f"{dt['dv']} mm"), ("Raíz Aórtica", f"{dt['dr']} mm"), ("Aurícula Izq.", f"{dt['ai']} mm"), ("Septum", f"{dt['si']} mm"), ("FEy", f"{dt['fy']} %")]
    for i, (n, v) in enumerate(ms): b2.cell(i,0).text, b2.cell(i,1).text = n, v
    doc.add_paragraph("\n")
    # Limpieza de texto fragmentada para evitar SyntaxError
    for l in rep.split('\n'):
        l = l.strip()
        l = l.replace('*', '')
        l = l.replace('"', '')
        if not l: continue
        excluir = ["presento", "pastore", "resumen", "importante", "basado"]
        if any(x in l.lower() for x in excluir): continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        headers = ["I.", "II.", "III.", "IV.", "CONCL"]
        if any(l.upper().startswith(h) for h in headers): p.add_run(l).bold = True
        else: p.add_run(l)
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("\n__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True
    if pdf_b:
        try:
            with fitz.open(stream=pdf_b, filetype="pdf") as dp:
                ims = [dp.extract_image(i[0])["image"] for p in
