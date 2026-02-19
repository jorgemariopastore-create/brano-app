
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def buscar_en_txt(texto, etiquetas):
    # Busca el valor numérico exacto en los bloques técnicos del ecógrafo
    for etiqueta in etiquetas:
        patron = rf"\[MEASUREMENT\].*?{etiqueta}.*?value\s*=\s*([\d.]+)"
        match = re.search(patron, texto, re.S | re.I)
        if match:
            try:
                # Convertimos 40.0 (dato crudo) a 40 (dato médico)
                return str(int(float(match.group(1))))
            except:
                return match.group(1)
    return ""

def motor_hibrido(txt_content, pdf_bytes):
    d = {"pac": "", "ed": "", "fy": "60", "dv": "", "dr": "", "ai": "", "si": "", "fecha": ""}
    
    # 1. DATOS SEGUROS DEL PDF (Nombre y Fecha)
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            texto_pdf = doc[0].get_text()
            # Fecha (formato DD/MM/AAAA)
            f_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", texto_pdf)
            if f_match: d["fecha"] = f_match.group(1)
            # Nombre limpio
            n_match = re.search(r"(?:Nombre pac\.|Paciente)\s*[:=-]?\s*([^<\r\n]*)", texto_pdf, re.I)
            if n_match: d["pac"] = n_match.group(1).strip().upper()
    except: pass

    # 2. DATOS TÉCNICOS DEL TXT (Medidas puras del ecógrafo)
    if txt_content:
        # Edad (del TXT es muy fiable)
        e_match = re.search(r"Age\s*=\s*(\d+)", txt_content, re.I)
        if e_match: d["ed"] = e_match.group(1)

        # Mapeo de etiquetas técnicas que usa tu equipo
        d["dv"] = buscar_en_txt(txt_content, ["LVIDd", "DDVI"]) # Diámetro Diastólico
        d["si"] = buscar_en_txt(txt_content, ["IVSd", "DDSIV"]) # Septum
        d["dr"] = buscar_en_txt(txt_content, ["AORootDiam", "DRAO"]) # Raíz Aórtica
        d["ai"] = buscar_en_txt(txt_content, ["LADiam", "DDAI"]) # Aurícula Izq.
        
        # FEy: Buscamos EF (Ejection Fraction) que es el dato real de fuerza
        fey_txt = buscar_en_txt(txt_content, ["EF", "LVEF", "FA"])
        if fey_txt: d["fy"] = fey_txt

    return d

def generar_docx(rep, dt, ims):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(11)
    
    # Encabezado
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla Datos (Híbrida: Nombre de PDF, Edad de TXT)
    t1 = doc.add_table(rows=2, cols=3); t1.style = 'Table Grid'
    l1 = [f"PACIENTE: {dt['pac']}", f"EDAD: {dt['ed']} años", f"FECHA: {dt['fecha']}", "PESO: --", "ALTURA: --", "BSA: --"]
    for i, x in enumerate(l1): t1.cell(i//3, i%3).text = x
    
    doc.add_paragraph("\n")
    # Tabla Medidas (Todas del TXT)
    t2 = doc.add_table(rows=5, cols=2); t2.style = 'Table Grid'
    ms = [("DDVI", f"{dt['dv']} mm"), ("Raíz Aórtica", f"{dt['dr']} mm"), ("Aurícula Izq.", f"{dt['ai']} mm"), ("Septum", f"{dt['si']} mm"), ("FEy", f"{dt['fy']} %")]
    for i, (n, v) in enumerate(ms):
        t2.cell(i,0).text, t2.cell(i,1).text = n, v
    
    doc.add_paragraph("\n")
    # Informe
    for line in rep.split('\n'):
        line = line.strip().replace('*', '')
        if not line or any(x in line.lower() for x in ["paciente", "doctor", "mn"]): continue
        par = doc.add_paragraph(); par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(line.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCL"]):
            par.add_run(line).bold = True
        else: par.add_run(line)
            
    f = doc.add_paragraph(); f.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f.add_run("\n\n__________________________\nDr. FRANCISCO ALBERTO PASTORE\nMN 74144").bold = True
    
    if ims:
        doc.add_page_break()
        ti = doc.add_table(rows=(len(ims)+1)//2, cols=2)
        for i, m in enumerate(ims):
            c = ti.cell(i//2, i%2).paragraphs[0]
            c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.add_run().add_picture(io.BytesIO(m), width=Inches(2.5))
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

# Streamlit
st.set_page_config(page_title="CardioPro 40.7 Híbrida", layout="wide")
st.title("🏥 CardioReport Pro v40.7 (Modo Híbrido)")

u1 = st.file_uploader("1. TXT (Medidas)", type=["txt"])
u2 = st.file_uploader("2. PDF (Nombre, Fecha, Fotos)", type=["pdf"])
ak = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key", type="password")

if u1 and u2 and ak:
    txt_raw = u1.read().decode("latin-1", errors="ignore")
    # Aquí ocurre la magia híbrida
    dt = motor_hibrido(txt_raw, u2.getvalue())
    
    st.subheader("🔍 VALIDACIÓN DE DATOS (PDF + TXT)")
    c1, c2, c3 = st.columns(3)
    v_pac = c1.text_input("Paciente (del PDF)", dt["pac"])
    v_fey = c1.text_input("FEy % (del TXT)", dt["fy"])
    v_eda = c2.text_input("Edad (del TXT)", dt["ed"])
    v_dvi = c2.text_input("DDVI mm (del TXT)", dt["dv"])
    v_fec = c3.text_input("Fecha (del PDF)", dt["fecha"])
    v_siv = c3.text_input("SIV mm (del TXT)", dt["si"])

    if st.button("🚀 GENERAR"):
        cl = Groq(api_key=ak)
        px = f"Redacta un informe médico. Estructura: I. ANATOMÍA, II. FUNCIÓN VENTRICULAR, III. VÁLVULAS, IV. CONCLUSIÓN. Datos: DDVI {v_dvi}mm, SIV {v_siv}mm, FEy {v_fey}%. Estilo técnico, sin nombre de paciente."
        res = cl.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":px}], temperature=0)
        txt_ia = res.choices[0].message.content
        st.info(txt_ia)
        
        imgs = []
        try:
            with fitz.open(stream=u2.getvalue(), filetype="pdf") as dp:
                for pag in dp:
                    for img in pag.get_images():
                        imgs.append(dp.extract_image(img[0])["image"])
        except: pass
        
        d_f = {"pac":v_pac,"ed":v_eda,"fy":v_fey,"dv":v_dvi,"dr":dt['dr'],"si":v_siv,"ai":dt['ai'],"fecha":v_fec}
        w = generar_word(txt_ia, d_f, imgs)
        st.download_button("📥 DESCARGAR WORD", w, f"Informe_{v_pac}.docx")
