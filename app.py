
import streamlit as st
from groq import Groq
import fitz, io, re, datetime
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def motor(t):
    # Valores por defecto
    d = {"pac": "ALBORNOZ ALICIA", "ed": "74", "fy": "68", "dv": "40", "dr": "32", "ai": "32", "si": "11", "fecha": datetime.datetime.now().strftime("%d/%m/%Y")}
    if t:
        # Extraer Paciente
        n = re.search(r"(?:Paciente|Nombre)\s*[:=-]?\s*([^<\r\n]*)", t, re.I)
        if n: d["pac"] = n.group(1).strip().upper()
        # Extraer Fecha del estudio
        f = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", t)
        if f: d["fecha"] = f.group(1)
        # Extraer Medidas
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
    for l in rep.split('\n'):
        l = l.strip().replace('*', '').replace('"', '')
        if not l or any(x in l.lower() for x in ["presento", "pastore", "resumen", "importante", "basado"]): continue
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(l.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCL"]): p.add_run(l).bold = True
        else: p.add_run(l)
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("\n__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True
    if pdf_b:
        try:
            with fitz.open(stream=pdf_b, filetype="pdf") as dp:
                ims = [dp.extract_image(i[0])["image"] for p in dp for i in p.get_images()]
                if ims:
                    doc.add_page_break()
                    ti = doc.add_table(rows=(len(ims)+1)//2, cols=2)
                    for i, m in enumerate(ims):
                        c = ti.cell(i//2, i%2).paragraphs[0]
                        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        c.add_run().add_picture(io.BytesIO(m), width=Inches(2.4))
        except: pass
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

st.set_page_config(page_title="CardioPro", layout="wide")
st.title("❤️ CardioReport Pro v38.9")
u1 = st.file_uploader("1. TXT", type=["txt", "html"])
u2 = st.file_uploader("2. PDF", type=["pdf"])
ak = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("API", type="password")

if u1 and u2 and ak:
    dt = motor(u1.read().decode("latin-1", errors="ignore"))
    st.subheader("🔍 VALIDACIÓN")
    v1, v2, v3 = st.columns(3)
    p = v1.text_input("Pac", dt["pac"])
    f = v1.text_input("FEy", dt["fy"])
    e = v2.text_input("Ed", dt["ed"])
    d = v2.text_input("DDVI", dt["dv"])
    s = v3.text_input("SIV", dt["si"])
    fe = v3.text_input("Fecha", dt["fecha"])
    a = dt["dr"] # Valor DRAO
    if st.button("🚀 GENERAR"):
        cl = Groq(api_key=ak)
        px = f"Informe médico profesional: I. ANATOMÍA: Raíz ({a}mm), SIV ({s}mm). II. FUNCIÓN: FEy {f}%. III. VÁLVULAS: Normal. IV. CONCLUSIÓN: Normal. Sin introducciones."
        rs = cl.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":px}], temperature=0)
        rep = rs.choices[0].message.content
        st.info(rep)
        fd = {"pac":p,"ed":e,"fy":f,"dv":d,"dr":a,"si":s,"ai":dt["ai"],"fecha":fe}
        w = docx(rep, fd, u2.getvalue())
        st.download_button("📥 DESCARGAR", w, f"{p}.docx")
