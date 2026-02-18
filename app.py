
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def motor_ext(txt):
    d = {"paciente": "ALBORNOZ ALICIA", "edad": "74", "fey": "68", "ddvi": "40", "drao": "32", "ddai": "32", "siv": "11"}
    if txt:
        n = re.search(r"(?:Paciente|Nombre)\s*[:=-]?\s*([^<\r\n]*)", txt, re.I)
        if n: d["paciente"] = n.group(1).strip().upper()
        for k, p in [("ddvi","DDVI"), ("drao","DRAO"), ("ddai","DDAI"), ("siv","DDSIV")]:
            m = re.search(rf"\"{p}\"\s*,\s*\"(\d+)\"", txt, re.I)
            if m: d[k] = m.group(1)
    return d

def crear_doc(rep, dt, pdf_b):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(11)
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    r.bold, r.font.size = True, Pt(12)
    tbl = doc.add_table(rows=2, cols=3); tbl.style = 'Table Grid'
    dat = [f"PACIENTE: {dt['paciente']}", f"EDAD: {dt['edad']} años", "FECHA: 13/02/2026", "PESO: 56 kg", "ALTURA: 152 cm", "BSA: 1.54 m²"]
    for i, texto in enumerate(dat): tbl.cell(i//3, i%3).text = texto
    doc.add_paragraph("\n")
    tm = doc.add_table(rows=5, cols=2); tm.style = 'Table Grid'
    ms = [("DDVI", f"{dt['ddvi']} mm"), ("DRAO", f"{dt['drao']} mm"), ("DDAI", f"{dt['ddai']} mm"), ("SIV", f"{dt['siv']} mm"), ("FEy", f"{dt['fey']} %")]
    for i, (n, v) in enumerate(ms): tm.cell(i,0).text, tm.cell(i,1).text = n, v
    doc.add_paragraph("\n")
    for l in rep.split('\n'):
        l = l.strip().replace('*', '').replace('"', '')
        if not l or any(x in l.lower() for x in ["presento", "pastore"]): continue
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(l.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCL"]): p.add_run(l).bold = True
        else: p.add_run(l)
    doc.add_paragraph("\n")
    f = doc.add_paragraph(); f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True
    if pdf_b:
        try:
            pdf = fitz.open(stream=pdf_b, filetype="pdf")
            imgs = []
            for pg in pdf:
                for im in pg.get_images(full=True): imgs.append(pdf.extract_image(im[0])["image"])
            if imgs:
                doc.add_page_break()
                ti = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
                for i, img in enumerate(imgs):
                    pi = ti.cell(i//2, i%2).paragraphs[0]
                    pi.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    pi.add_run().add_picture(io.BytesIO(img), width=Inches(2.4))
            pdf.close()
        except: pass
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

st.set_page_config(page_title="Cardio Pro", layout="wide")
st.title("❤️ CardioReport Pro v37.8")
c1, c2 = st.columns(2)
with c1: u_txt = st.file_uploader("1. Datos TXT", type=["txt", "html"])
with c2: u_pdf = st.file_uploader("2. PDF Original", type=["pdf"])
key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("API Key", type="password")

if u_txt and u_pdf and key:
    dt = motor_ext(u_txt.read().decode("latin-1", errors="ignore"))
    st.subheader("🔍 VALIDACIÓN DE DATOS")
    v1, v2, v3 = st.columns(3)
    with v1: 
        f_pac = st.text_input("Paciente", dt["paciente"])
        f_fey = st.text_input("FEy %", dt["fey"])
    with v2:
        f_ed = st.text_input("Edad", dt["edad"])
        f_dd = st.text_input("DDVI mm", dt["ddvi"])
    with v3:
        f_si = st.text_input("SIV mm", dt["siv"])
        f_dr = st.text_input("DRAO mm", dt["drao"])

    if st.button("🚀 GENERAR INFORME"):
        cl = Groq(api_key=key)
        pr = f"Escribe exclusivamente: I. ANATOMÍA: Raíz aórtica ({f_dr}mm) y aurícula izquierda normales. Cavidades con espesores conservados (Septum {f_si}mm). II. FUNCIÓN: Sistólica conservada. FEy {f_fey}%. III. VÁLVULAS: Ecoestructura normal. IV. CONCLUSIÓN: Normal."
        res = cl.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": pr}], temperature=0)
        rep = res.choices[0].message.content
        st.info(rep)
        word = crear_doc(rep, {"paciente": f_pac, "edad": f_ed, "fey": f_fey, "ddvi": f_dd, "drao": f_dr, "siv": f_si}, u_pdf.getvalue())
        st.download_button("📥 DESCARGAR", word, f"Informe_{f_pac}.docx")
