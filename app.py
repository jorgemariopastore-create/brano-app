
import streamlit as st
from groq import Groq
import fitz, io, re
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def buscar_medida_flexible(texto, sinonimos):
    # Esta función busca cualquier sinónimo dentro de los bloques del ecógrafo
    for s in sinonimos:
        # Busca el nombre del parámetro y luego el valor numérico (value = XX.XX)
        patron = rf"\[MEASUREMENT\].*?{s}.*?value\s*=\s*([\d.]+)"
        match = re.search(patron, texto, re.S | re.I)
        if match:
            try:
                # Retorna el valor redondeado (médico)
                return str(int(float(match.group(1))))
            except:
                return match.group(1)
    return ""

def motor_hibrido_v8(txt_raw, pdf_bytes):
    d = {"pac": "PACIENTE DESCONOCIDO", "ed": "--", "fy": "60", "dv": "--", "dr": "--", "ai": "--", "si": "--", "fecha": "--"}
    
    # 1. EXTRACCIÓN DEL PDF (Nombre y Fecha)
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            full_text = doc[0].get_text()
            f_m = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", full_text)
            if f_m: d["fecha"] = f_m.group(1)
            n_m = re.search(r"(?:Nombre pac\.|Paciente)\s*[:=-]?\s*([^<\r\n]*)", full_text, re.I)
            if n_m: d["pac"] = n_m.group(1).strip().upper()
    except: pass

    # 2. EXTRACCIÓN DEL TXT (Usando Diccionario de Sinónimos)
    if txt_raw:
        # Edad
        e_m = re.search(r"Age\s*=\s*(\d+)", txt_raw, re.I)
        if e_m: d["ed"] = e_m.group(1)

        # TABLA DE SINÓNIMOS TÉCNICOS
        d["dv"] = buscar_medida_flexible(txt_raw, ["LVIDd", "DDVI", "VId d", "VId(d)"])
        d["si"] = buscar_medida_flexible(txt_raw, ["IVSd", "DDSIV", "Septum", "SIVd"])
        d["dr"] = buscar_medida_flexible(txt_raw, ["AORootDiam", "DRAO", "Ao Root", "Raíz Aorta"])
        d["ai"] = buscar_medida_flexible(txt_raw, ["LADiam", "DDAI", "LA Diam", "Aurícula Izq"])
        d["fy"] = buscar_medida_flexible(txt_raw, ["EF", "LVEF", "FA", "Teich", "Cubed"]) or "60"

    return d

def generar_word(rep, dt, ims):
    doc = Document()
    doc.styles['Normal'].font.name, doc.styles['Normal'].font.size = 'Arial', Pt(11)
    
    tit = doc.add_paragraph()
    tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tit.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    t1 = doc.add_table(rows=2, cols=3); t1.style = 'Table Grid'
    l1 = [f"PACIENTE: {dt['pac']}", f"EDAD: {dt['ed']} años", f"FECHA: {dt['fecha']}", "PESO: --", "ALTURA: --", "BSA: --"]
    for i, x in enumerate(l1): t1.cell(i//3, i%3).text = x
    
    doc.add_paragraph("\n")
    t2 = doc.add_table(rows=5, cols=2); t2.style = 'Table Grid'
    ms = [("DDVI", f"{dt['dv']} mm"), ("Raíz Aórtica", f"{dt['dr']} mm"), ("Aurícula Izq.", f"{dt['ai']} mm"), ("Septum", f"{dt['si']} mm"), ("FEy", f"{dt['fy']} %")]
    for i, (n, v) in enumerate(ms):
        t2.cell(i,0).text, t2.cell(i,1).text = n, v
    
    doc.add_paragraph("\n")
    for line in rep.split('\n'):
        line = line.strip().replace('*', '')
        if not line or any(x in line.lower() for x in ["paciente", "doctor", "mn"]): continue
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if any(line.upper().startswith(h) for h in ["I.", "II.", "III.", "IV.", "CONCL"]): p.add_run(line).bold = True
        else: p.add_run(line)
            
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

# INTERFAZ
st.set_page_config(page_title="CardioPro 40.8", layout="wide")
st.title("🏥 CardioReport Pro v40.8 (Sinónimos Inteligentes)")

u1 = st.file_uploader("1. TXT (Medidas)", type=["txt"])
u2 = st.file_uploader("2. PDF (Nombre, Fecha, Fotos)", type=["pdf"])
ak = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key", type="password")

if u1 and u2 and ak:
    txt_content = u1.read().decode("latin-1", errors="ignore")
    # Extraemos datos combinados
    datos = motor_hibrido_v8(txt_content, u2.getvalue())
    
    st.subheader("🔍 VALIDACIÓN DE DATOS")
    c1, c2, c3 = st.columns(3)
    # Mostramos los datos para que el usuario pueda editarlos si falta algo
    v_pac = c1.text_input("Paciente", datos["pac"])
    v_fey = c1.text_input("FEy %", datos["fy"])
    v_eda = c2.text_input("Edad", datos["ed"])
    v_dvi = c2.text_input("DDVI mm", datos["dv"])
    v_fec = c3.text_input("Fecha", datos["fecha"])
    v_siv = c3.text_input("SIV mm", datos["si"])

    if st.button("🚀 GENERAR INFORME"):
        # Aseguramos que todas las variables existan antes de llamar a las funciones
        client = Groq(api_key=ak)
        prompt = f"Informe médico técnico: I. ANATOMÍA, II. FUNCIÓN VENTRICULAR, III. VÁLVULAS, IV. CONCLUSIÓN. Datos: DDVI {v_dvi}mm, SIV {v_siv}mm, FEy {v_fey}%. Estilo profesional, sin nombre de paciente."
        
        try:
            res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":prompt}], temperature=0)
            txt_ia = res.choices[0].message.content
            st.info(txt_ia)
            
            # Imágenes del PDF
            imgs = []
            with fitz.open(stream=u2.getvalue(), filetype="pdf") as dp:
                for pag in dp:
                    for img in pag.get_images():
                        imgs.append(dp.extract_image(img[0])["image"])
            
            # Diccionario final con lo que el médico validó en pantalla
            d_final = {"pac":v_pac, "ed":v_eda, "fy":v_fey, "dv":v_dvi, "si":v_siv, "dr":datos["dr"], "ai":datos["ai"], "fecha":v_fec}
            
            archivo = generar_word(txt_ia, d_final, imgs)
            st.download_button("📥 DESCARGAR WORD", archivo, f"Informe_{v_pac}.docx")
        except Exception as e:
            st.error(f"Error al generar: {e}")
