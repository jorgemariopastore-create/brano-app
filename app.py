
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz
import io
import os
from groq import Groq

# Configuración API
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def buscar_dato_en_toda_la_hoja(df, terminos):
    """Busca cualquier término de la lista en el Excel y devuelve lo que hay a la derecha"""
    for r in range(len(df)):
        for c in range(len(df.columns)):
            celda = str(df.iloc[r, c]).strip().lower()
            for t in terminos:
                if t.lower() in celda:
                    try:
                        res = str(df.iloc[r, c + 1]).strip()
                        if res.lower() != "nan" and res != "": return res
                    except: pass
    return "N/A"

def extraer_datos_excel_manual(file):
    info = {"paciente": {}, "eco": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        df_eco = pd.read_excel(xls, "Ecodato", header=None)
        
        # Búsqueda ultra-flexible de paciente
        info["paciente"]["Nombre"] = buscar_dato_en_toda_la_hoja(df_eco, ["Paciente", "Nombre", "BALEIRON"])
        info["paciente"]["Peso"] = buscar_dato_en_toda_la_hoja(df_eco, ["Peso", "Kg"])
        info["paciente"]["Altura"] = buscar_dato_en_toda_la_ho_hoja(df_eco, ["Altura", "Cm"])
        info["paciente"]["BSA"] = buscar_dato_en_toda_la_hoja(df_eco, ["DUBOIS", "Superficie", "SC"])

        # Mediciones técnicas
        mapeo = {
            "DDVI": "Diámetro Diastólico Ventrículo Izquierdo",
            "DSVI": "Diámetro Sistólico Ventrículo Izquierdo",
            "FA": "Fracción de Acortamiento",
            "DDVD": "Ventrículo Derecho",
            "DDAI": "Aurícula Izquierda",
            "DDSIV": "Septum Interventricular",
            "DDPP": "Pared Posterior"
        }
        for sigla, nombre in mapeo.items():
            val = buscar_dato_en_toda_la_hoja(df_eco, [sigla])
            if val != "N/A": info["eco"][nombre] = val

        # Doppler
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler", header=None)
            for i in range(len(df_dop)):
                v = str(df_dop.iloc[i, 0])
                if any(x in v for x in ["Tric", "Pulm", "Mit", "Aór"]):
                    info["doppler"].append(f"{v}: {df_dop.iloc[i, 1]} cm/s")
    except Exception as e:
        st.error(f"Error: {e}")
    return info

def redactar_ia(info):
    prompt = f"""
    Eres Cardiólogo. Redacta:
    1. HALLAZGOS: Párrafo técnico en prosa. DDVI > 56mm es dilatación. FA < 27% es deterioro. 
    2. CONCLUSIÓN: Diagnóstico final breve.
    Datos: {info['eco']} | Doppler: {info['doppler']}
    """
    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":prompt}], temperature=0)
    return res.choices[0].message.content

def generar_word(info, texto_ia, f_pdf):
    doc = Document()
    
    # Encabezado
    tit = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {info['paciente'].get('Nombre')}\n").bold = True
    p.add_run(f"FECHA: 27/01/2026\n")
    p.add_run(f"PESO: {info['paciente'].get('Peso')} kg | ALTURA: {info['paciente'].get('Altura')} cm | SC: {info['paciente'].get('BSA')} m²")

    # Secciones
    texto_ia = texto_ia.replace("HALLAZGOS:", "").strip()
    partes = texto_ia.split("CONCLUSIÓN")
    
    doc.add_heading('Hallazgos', level=1)
    doc.add_paragraph(partes[0].strip())
    
    if len(partes) > 1:
        doc.add_heading('Conclusión', level=1)
        doc.add_paragraph(partes[1].replace(":", "").strip())

    # Imágenes
    doc.add_page_break()
    doc.add_heading('Anexo de Imágenes', level=1)
    try:
        f_pdf.seek(0)
        pdf = fitz.open(stream=f_pdf.read(), filetype="pdf")
        imgs = [io.BytesIO(pdf.extract_image(img[0])["image"]) for p in pdf for img in p.get_images()]
        if imgs:
            t = doc.add_table(rows=4, cols=2)
            for i in range(min(len(imgs), 8)):
                run = t.rows[i//2].cells[i%2].paragraphs[0].add_run()
                run.add_picture(imgs[i], width=Inches(2.8))
    except: pass

    # --- FIRMA MÉDICA (FORZADA) ---
    doc.add_paragraph("\n\n")
    f_p = doc.add_paragraph()
    f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if os.path.exists("firma_doctor.png"):
        f_p.add_run().add_picture("firma_doctor.png", width=Inches(2.0))
    else:
        # Esto asegura que si no hay imagen, salga la línea de firma
        f_p.add_run("__________________________\n").bold = True
        f_p.add_run("Firma y Sello del Médico").bold = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# Streamlit
st.title("CardioReport 🩺")
f_xl = st.file_uploader("Subir Excel", type=["xls", "xlsx"])
f_pd = st.file_uploader("Subir PDF", type="pdf")

if f_xl and f_pd:
    if st.button("Generar Informe"):
        data = extraer_datos_excel_manual(f_xl)
        txt = redactar_ia(data)
        word = generar_word(data, txt, f_pd)
        st.download_button("Descargar Informe", word, "Informe_Final.docx")
