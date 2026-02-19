
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def buscar_medida_txt(texto, etiquetas):
    # Busca el valor numérico exacto en los bloques [MEASUREMENT] del TXT
    for etiqueta in etiquetas:
        patron = rf"\[MEASUREMENT\].*?{etiqueta}.*?value\s*=\s*([\d.]+)"
        match = re.search(patron, texto, re.S | re.I)
        if match:
            try:
                # El ecógrafo da decimales (40.0), nosotros lo pasamos a entero (40)
                return str(int(float(match.group(1))))
            except:
                return match.group(1)
    return ""

def motor_hibrido(txt_content, pdf_bytes):
    # Diccionario con valores base
    d = {"pac": "", "ed": "", "fy": "60", "dv": "", "dr": "", "ai": "", "si": "", "fecha": ""}
    
    # --- PASO 1: LEER PDF (Datos Administrativos Seguros) ---
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            texto_pdf = doc[0].get_text()
            # Fecha de estudio (formato DD/MM/AAAA)
            f_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", texto_pdf)
            if f_match: d["fecha"] = f_match.group(1)
            # Nombre (buscando después de "Nombre pac.:" o "Paciente:")
            n_match = re.search(r"(?:Nombre pac\.|Paciente)\s*[:=-]?\s*([^<\r\n]*)", texto_pdf, re.I)
            if n_match: d["pac"] = n_match.group(1).strip().upper()
    except: pass

    # --- PASO 2: LEER TXT (Medidas Técnicas Puras) ---
    if txt_content:
        # Edad (está clara en el TXT como Age = 86Y)
        e_match = re.search(r"Age\s*=\s*(\d+)", txt_content, re.I)
        if e_match: d["ed"] = e_match.group(1)

        # Mapeo de etiquetas técnicas del ecógrafo (LVIDd, IVSd, etc.)
        d["dv"] = buscar_medida_txt(txt_content, ["LVIDd", "DDVI"])
        d["si"] = buscar_medida_txt(txt_content, ["IVSd", "DDSIV"])
        d["dr"] = buscar_medida_txt(txt_content, ["AORootDiam", "DRAO"])
        d["ai"] = buscar_medida_txt(txt_content, ["LADiam", "DDAI"])
        
        # FEy: Buscamos EF (Ejection Fraction) o FA (Fracción de Acortamiento)
        fey_txt = buscar_medida_txt(txt_content, ["EF", "LVEF", "FA"])
        if fey_txt: d["fy"] = fey_txt

    return d

def generar_word(rep, dt, ims):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(11)
    
    # Encabezado
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Tabla Datos Personales (Extraídos mayormente del PDF)
    t1 = doc.add_table(rows=2, cols=3); t1.style = 'Table Grid'
    l1 = [f"PACIENTE: {dt['pac']}", f"EDAD: {dt['ed']} años", f"FECHA: {dt['fecha']}", "PESO: --", "ALTURA: --", "BSA: --"]
    for i, x in enumerate(l1): t1.cell(i//3, i%3).text = x
    
    doc.add_paragraph("\n")
    # Tabla Medidas (Extraídas del TXT)
    t2 = doc.add_table(rows=5, cols=2); t2.style = 'Table Grid'
    ms = [("DDVI", f"{dt['dv']} mm"), ("Raíz Aórtica", f"{dt['dr']} mm"), ("Aurícula Izq.", f"{dt['ai']} mm"), ("Septum", f"{dt['si']} mm"), ("FEy", f"{dt['fy']} %")]
    for i, (n, v) in enumerate(ms):
        t2.cell(i,0).text, t2.cell(i,1).text = n, v
    
    doc.add_paragraph("\n")
    # Informe redactado por IA
    for line in rep.split('\n'):
        line = line.strip().replace('*', '')
        if not line or any(x in line.lower() for x in ["paciente", "doctor", "mn"]): continue
        par = doc.add_paragraph(); par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(line.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCL"]):
            par.add_run(line).bold = True
        else:
            par.add_run(line)
            
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

# --- INTERFAZ ---
st.set_page_config(page_title="CardioPro 40.7 Híbrida", layout="wide")
st.title("🏥 CardioReport Pro v40.7 (Modo Híbrido)")

u1 = st.file_uploader("1. Subir TXT (Para Medidas Técnicas)", type=["txt"])
u2 = st.file_uploader("2. Subir PDF (Para Fecha, Nombre e Imágenes)", type=["pdf"])
ak = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key", type="password")

if u1 and u2 and ak:
    txt_raw = u1.read().decode("latin-1", errors="ignore")
    # El motor ahora combina lo mejor de ambos mundos
    dt = motor_hibrido(txt_raw, u2.getvalue())
    
    st.subheader("🔍 VALIDACIÓN DE DATOS (Combinación PDF + TXT)")
    c1, c2, c3 = st.columns(3)
    v_pac = c1.text_input("Paciente (del PDF)", dt["pac"])
    v_fey = c1.text_input("FEy % (del TXT)", dt["fy"])
    v_eda = c2.text_input("Edad (del TXT)", dt["ed"])
    v_dvi = c2.text_input("DDVI mm (del TXT)", dt["dv"])
    v_fec = c3.text_input("Fecha (del PDF)", dt["fecha"])
    v_siv = c3.text_input("SIV mm (del TXT)", dt["si"])

    if st.button("🚀 GENERAR INFORME"):
        cl = Groq(api_key=ak)
        # El prompt usa los datos ya validados
        px = f"Redacta un informe médico técnico. Estructura: I. ANATOMÍA, II. FUNCIÓN VENTRICULAR, III. VÁLVULAS, IV. CONCLUSIÓN. Datos: DDVI {v_dvi}mm, SIV {v_siv}mm, FEy {v_fey}%. Estilo profesional, sin introducciones."
        res = cl.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":px}], temperature=0)
        txt_ia = res.choices[0].message.content
        st.info(txt_ia)
        
        # Extraer fotos del PDF
        imgs = []
        try:
            with fitz.open(stream=u2.getvalue(), filetype="pdf") as dp:
                for pag in dp:
                    for img in pag.get_images():
                        imgs.append(dp.extract_image(img[0])["image"])
        except: pass
        
        d_f = {"pac":v_pac,"ed":v_eda,"fy":v_fey,"dv":v_dvi,"dr":dt['dr'],"si":v_siv,"ai":dt['ai'],"fecha":v_fec}
        w = generar_word(txt_ia, d_f, imgs)
        st.download_button("📥 DESCARGAR INFORME", w, f"Informe_{v_pac}.docx")
