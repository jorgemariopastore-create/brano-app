
import streamlit as st
from groq import Groq
import fitz, io, re, datetime
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def motor(t, pdf_bytes):
    # Valores iniciales vacíos para forzar la lectura nueva
    d = {"pac": "", "ed": "", "fy": "60", "dv": "", "dr": "", "ai": "", "si": "", "fecha": ""}
    
    # 1. Extraer Fecha y Datos del PDF
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc_p:
            texto_p = doc_p[0].get_text()
            # Buscar fecha
            f_pdf = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", texto_p)
            if f_pdf: d["fecha"] = f_pdf.group(1)
            # Buscar nombre en PDF si no está en TXT
            n_pdf = re.search(r"(?:Paciente|Nombre)\s*[:=-]?\s*([^<\r\n]*)", texto_p, re.I)
            if n_pdf: d["pac"] = n_pdf.group(1).strip().upper()
    except: pass

    # 2. Extraer datos del TXT/HTML (Sobrescribe lo anterior si encuentra datos)
    if t:
        n_txt = re.search(r"(?:Paciente|Nombre)\s*[:=-]?\s*([^<\r\n]*)", t, re.I)
        if n_txt: d["pac"] = n_txt.group(1).strip().upper()
        
        # Mapeo de valores técnicos
        for k, p in [("dv","DDVI"), ("dr","DRAO"), ("ai","DDAI"), ("si","DDSIV"), ("fy","FA")]:
            m = re.search(rf"\"{p}\"\s*,\s*\"(\d+)\"", t, re.I)
            if m: d[k] = m.group(1)
            
        # Edad
        ed = re.search(r"Edad\s*[:=-]?\s*(\d+)", t, re.I)
        if ed: d["ed"] = ed.group(1)
            
    return d

def docx(rep, dt, ims):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(11)
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    b1 = doc.add_table(rows=2, cols=3); b1.style = 'Table Grid'
    ls = [f"PACIENTE: {dt['pac']}", f"EDAD: {dt['ed']} años", f"FECHA: {dt['fecha']}", "PESO: 56 kg", "ALTURA: 152 cm", "BSA: 1.54 m²"]
    for i, x in enumerate(ls): b1.cell(i//3, i%3).text = x
    
    doc.add_paragraph("\n")
    b2 = doc.add_table(rows=5, cols=2); b2.style = 'Table Grid'
    ms = [("DDVI", f"{dt['dv']} mm"), ("Raíz Aórtica", f"{dt['dr']} mm"), ("Aurícula Izq.", f"{dt['ai']} mm"), ("Septum", f"{dt['si']} mm"), ("FEy", f"{dt['fy']} %")]
    for i, (n, v) in enumerate(ms):
        b2.cell(i,0).text, b2.cell(i,1).text = n, v
    
    doc.add_paragraph("\n")
    for l in rep.split('\n'):
        l = l.strip().replace('*', '').replace('"', '')
        if not l or any(x in l.lower() for x in ["pastore", "resumen", "nota"]): continue
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(l.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCL"]): p.add_run(l).bold = True
        else: p.add_run(l)
    
    f = doc.add_paragraph(); f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("\n__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True
    
    if ims:
        doc.add_page_break()
        ti = doc.add_table(rows=(len(ims)+1)//2, cols=2)
        for i, m in enumerate(ims):
            c = ti.cell(i//2, i%2).paragraphs[0]
            c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.add_run().add_picture(io.BytesIO(m), width=Inches(2.4))
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

st.set_page_config(page_title="CardioPro 40.2", layout="wide")
st.title("❤️ CardioReport Pro v40.2")

u1 = st.file_uploader("1. Cargar TXT/HTML del nuevo paciente", type=["txt", "html"])
u2 = st.file_uploader("2. Cargar PDF del nuevo paciente", type=["pdf"])
ak = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("API", type="password")

if u1 and u2 and ak:
    # Reset de archivos si se suben nuevos
    t_raw = u1.read().decode("latin-1", errors="ignore")
    dt = motor(t_raw, u2.getvalue())
    
    st.subheader("🔍 VALIDACIÓN: Verifique los datos del NUEVO paciente")
    c1, c2, c3 = st.columns(3)
    # Los widgets ahora muestran lo que el motor encuentra en tiempo real
    p_nom = c1.text_input("Nombre Paciente", dt["pac"])
    f_ey = c1.text_input("FEy %", dt["fy"])
    e_dad = c2.text_input("Edad", dt["ed"])
    d_dvi = c2.text_input("DDVI mm", dt["dv"])
    f_ech = c3.text_input("Fecha del Informe", dt["fecha"])
    s_iv = c3.text_input("SIV mm", dt["si"])
    
    if st.button("🚀 GENERAR INFORME"):
        cl = Groq(api_key=ak)
        # Prompt dinámico con los datos de la validación
        px = f"Redacta un informe médico técnico. Paciente: {p_nom}. I. ANATOMÍA: Raíz aórtica ({dt['dr']}mm) y aurícula izquierda normales. SIV {s_iv}mm. II. FUNCIÓN: VI conservada. FEy {f_ey}%. III. VÁLVULAS: Sin alteraciones. IV. CONCLUSIÓN: Estudio normal. Estilo seco, sin introducciones."
        rs = cl.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":px}], temperature=0)
        rep = rs.choices[0].message.content
        st.info(rep)
        
        ims = []
        try:
            with fitz.open(stream=u2.getvalue(), filetype="pdf") as dp:
                for pag in dp:
                    for img in pag.get_images():
                        ims.append(dp.extract_image(img[0])["image"])
        except: pass
        
        datos_finales = {"pac":p_nom,"ed":e_dad,"fy":f_ey,"dv":d_dvi,"dr":dt['dr'],"si":s_iv,"ai":dt['ai'],"fecha":f_ech}
        w = docx(rep, datos_finales, ims)
        st.download_button("📥 DESCARGAR INFORME", w, f"{p_nom}.docx")
