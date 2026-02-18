
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Función de IA aislada para evitar cortes de sintaxis
def pedir_ia(key, p, f, e, d, s, a):
    try:
        client = Groq(api_key=key)
        px = f"Redacta informe médico: I. ANATOMÍA: Raíz aórtica ({a}mm) y aurícula izquierda normales. Cavidades con espesores conservados (SIV {s}mm). II. FUNCIÓN: Sistólica conservada. FEy {f}%. III. VÁLVULAS: Ecoestructura normal. IV. CONCLUSIÓN: Normal. Sin introducciones."
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":px}], temperature=0)
        return res.choices[0].message.content
    except Exception as e:
        return f"Error IA: {str(e)}"

def motor(t):
    d = {"pac": "ALBORNOZ ALICIA", "ed": "74", "fy": "68", "dv": "40", "dr": "32", "ai": "32", "si": "11"}
    if t:
        n = re.search(r"(?:Paciente|Nombre)\s*[:=-]?\s*([^<\r\n]*)", t, re.I)
        if n: d["pac"] = n.group(1).strip().upper()
        for k, p in [("dv","DDVI"), ("dr","DRAO"), ("ai","DDAI"), ("si","DDSIV")]:
            m = re.search(rf"\"{p}\"\s*,\s*\"(\d+)\"", t, re.I)
            if m: d[k] = m.group(1)
    return d

def get_imgs(pdf_b):
    out = []
    try:
        with fitz.open(stream=pdf_b, filetype="pdf") as doc:
            for p in doc:
                for i in p.get_images():
                    out.append(doc.extract_image(i[0])["image"])
    except: pass
    return out

def docx(rep, dt, imgs):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(11)
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = h.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    r.bold, r.font.size = True, Pt(12)
    b1 = doc.add_table(rows=2, cols=3); b1.style = 'Table Grid'
    ls = [f"PACIENTE: {dt['pac']}", f"EDAD: {dt['ed']} años", "FECHA: 18/02/2026", "PESO: 56 kg", "ALTURA: 152 cm", "BSA: 1.54 m²"]
    for i, x in enumerate(ls): b1.cell(i//3, i%3).text = x
    doc.add_paragraph("\n")
    b2 = doc.add_table(rows=5, cols=2); b2.style = 'Table Grid'
    ms = [("DDVI", f"{dt['dv']} mm"), ("Raíz Aórtica", f"{dt['dr']} mm"), ("Aurícula Izq.", f"{dt['ai']} mm"), ("Septum", f"{dt['si']} mm"), ("FEy", f"{dt['fy']} %")]
    for i, (n, v) in enumerate(ms): b2.cell(i,0).text, b2.cell(i,1).text = n, v
    doc.add_paragraph("\n")
    for l in rep.split('\n'):
        l = l.strip().replace('*', '').replace('"', '')
        if not l or any(x in l.lower() for x in ["presento", "pastore", "resumen", "importante"]): continue
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(l.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCL"]): p.add_run(l).bold = True
        else: p.add_run(l)
    doc.add_paragraph("\n")
    f = doc.add_paragraph(); f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("__________________________").bold = True
    f.add_run("\nDr. FRANCISCO ALBERTO PASTORE").bold = True
    f.add_run("\nMédico Cardiólogo - MN 74144").bold = True
    if imgs:
        doc.add_page_break()
        ti = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
        for i, m in enumerate(imgs):
            c = ti.cell(i // 2, i % 2)
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.paragraphs[0].add_run().add_picture(io.BytesIO(m), width=Inches(2.4))
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

st.set_page_config(page_title="CardioPro 38.7", layout="wide")
st.title("❤️ CardioReport Pro v38.7")
