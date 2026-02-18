
import streamlit as st
from groq import Groq
import fitz, io, re, datetime
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def motor(t):
    hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    d = {"pac": "PACIENTE", "ed": "0", "fy": "60", "dv": "40", "dr": "30", "ai": "30", "si": "10", "fecha": hoy}
    if t:
        n = re.search(r"(?:Paciente|Nombre)\s*[:=-]?\s*([^<\r\n]*)", t, re.I)
        if n: d["pac"] = n.group(1).strip().upper()
        # Buscamos la fecha del estudio (13/02/2026)
        f_e = re.search(r"(?:Fecha|Estudio|Realizado)\s*[:=-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", t, re.I)
        if f_e: d["fecha"] = f_e.group(1)
        # Buscamos las medidas
        for k, p in [("dv","DDVI"), ("dr","DRAO"), ("ai","DDAI"), ("si","DDSIV"), ("fy","FA"), ("ed","Edad")]:
            m = re.search(rf"\"{p}\"\s*,\s*\"(\d+)\"", t, re.I)
            if m: d[k] = m.group(1)
    return d

def docx(rep, dt, ims):
    doc = Document()
    doc.styles['Normal'].font.name = 'Arial'
    doc.styles['Normal'].font.size = Pt(11)
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    # Tabla de datos personales
    b1 = doc.add_table(rows=2, cols=3)
    b1.style = 'Table Grid'
    ls = [f"PACIENTE: {dt['pac']}", f"EDAD: {dt['ed']} años", f"FECHA: {dt['fecha']}", "PESO: 56 kg", "ALTURA: 152 cm", "BSA: 1.54 m²"]
    for i, x in enumerate(ls): b1.cell(i//3, i%3).text = x
    doc.add_paragraph("\n")
    # Tabla de mediciones
    b2 = doc.add_table(rows=5, cols=2)
    b2.style = 'Table Grid'
    ms = [("DDVI", f"{dt['dv']} mm"), ("Raíz Aórtica", f"{dt['dr']} mm"), ("Aurícula Izq.", f"{dt['ai']} mm"), ("Septum", f"{dt['si']} mm"), ("FEy", f"{dt['fy']} %")]
    for i, (n, v) in enumerate(ms):
        b2.cell(i,0).text = n
        b2.cell(i,1).text = v
    doc.add_paragraph("\n")
    # Texto del informe
    for l in rep.split('\n'):
        l = l.strip().replace('*', '').replace('"', '')
        if not l or any(x in l.lower() for x in ["pastore", "resumen"]): continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(l.upper().startswith(h) for h in ["I.", "II.", "III.", "IV."]): p.add_run(l).bold = True
        else: p.add_run(l)
    # Firma
    f = doc.add_paragraph()
    f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("\n__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True
    # Imagenes
    if ims:
        doc.add_page_break()
        ti = doc.add_table(rows=(len(ims)+1)//2, cols=2)
        for i, m in enumerate(ims):
            celda = ti.cell(i//2, i%2).paragraphs[0]
            celda.alignment = WD_ALIGN_PARAGRAPH.CENTER
            celda.add_run().add_picture(io.BytesIO(m), width=Inches(2.4))
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

st.set_page_config(page_title="CardioPro 39.5", layout="wide")
st.title("❤️ CardioReport Pro v39.5")
u1 = st.file_uploader("1. TXT", type=["txt", "html"])
u2 = st.file_uploader("2. PDF", type=["pdf"])
ak = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("API", type="password")

if u1 and u2 and ak:
    dt = motor(u1.read().decode("latin-1", errors="ignore"))
    st.subheader("🔍 VALIDACIÓN")
    v1, v2, v3 = st.columns(3)
    p = v1.text_input("Paciente", dt["pac"])
    f = v1.text_input("FEy %", dt["fy"])
    e = v2.text_input("Edad", dt["ed"])
    d = v2.text_input("DDVI mm", dt["dv"])
    fe = v3.text_input("Fecha Estudio", dt["fecha"])
    s = v3.text_input("SIV mm", dt["si"])
    if st.button("🚀 GENERAR"):
        cl = Groq(api_key=ak)
        px = f"Informe médico profesional: I. ANATOMÍA: Raíz ({dt['dr']}mm), SIV ({s}mm). II. FUNCIÓN: FEy {f}%. III. VÁLVULAS: Normal. IV. CONCLUSIÓN: Normal. Sin intro."
        rs = cl.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":px}], temperature=0)
        rep = rs.choices[0].message.content
        st.info(rep)
        # Extraer imagenes del PDF
        ims_list = []
        try:
            with fitz.open(stream=u2.getvalue(), filetype="pdf") as doc_pdf:
                for pagina in doc_pdf:
                    for img in pagina.get_images():
                        ims_list.append(doc_pdf.extract_image(img[0])["image"])
        except: pass
        fd = {"pac":p,"ed":e,"fy":f,"dv":d,"dr":dt['dr'],"si":s,"ai":dt['ai'],"fecha":fe}
        w = docx(rep, fd, ims_list)
        st.download_button("📥 DESCARGAR DOCX", w, f"{p}.docx")
