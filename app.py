
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

def extraer_datos_mejorado(file):
    info = {"paciente": {}, "eco": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        df_eco = pd.read_excel(xls, "Ecodato", header=None)
        
        # 1. Datos Básicos
        info["paciente"]["Nombre"] = str(df_eco.iloc[0, 1]).strip()
        info["paciente"]["Fecha"] = str(df_eco.iloc[1, 1]).split(" ")[0]
        
        # 2. Superficie Corporal (S/C) - Buscamos en la columna de la derecha de DUBOIS
        for r in range(len(df_eco)):
            fila_texto = str(df_eco.iloc[r, :]).lower()
            if "dubois" in fila_texto:
                # En tu Excel, el valor suele estar 1 o 2 celdas a la derecha
                for c_idx in range(len(df_eco.columns)):
                    if "dubois" in str(df_eco.iloc[r, c_idx]).lower():
                        val = df_eco.iloc[r, c_idx + 1]
                        info["paciente"]["SC"] = f"{float(val):.2f}" if pd.notnull(val) else "N/A"
                        break

        # 3. Cavidades (Estructura fija según tu Excel)
        mapeo = {"DDVD": "Ventrículo Derecho", "DDVI": "Diámetro Diastólico VI", 
                 "DSVI": "Diámetro Sistólico VI", "FA": "Fracción de Acortamiento", 
                 "DDSIV": "Septum", "DDPP": "Pared Posterior", "AAO": "Apertura Aórtica"}
        
        for r in range(len(df_eco)):
            key = str(df_eco.iloc[r, 0]).strip().upper()
            if key in mapeo:
                info["eco"][mapeo[key]] = df_eco.iloc[r, 1]

        # 4. Doppler
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler", header=None)
            for i in range(len(df_dop)):
                v = str(df_dop.iloc[i, 0])
                if any(x in v for x in ["Tric", "Pulm", "Mit", "Aór"]):
                    info["doppler"].append(f"{v}: {df_dop.iloc[i, 1]} cm/s")
                    
    except Exception as e:
        st.error(f"Error en datos: {e}")
    return info

def redactar_ia_final(info):
    prompt = f"""
    Eres un Cardiólogo. Genera el texto para un informe.
    DATOS: {info['eco']} | DOPPLER: {info['doppler']}
    
    REGLAS DE ORO:
    1. Escribe UN párrafo para 'HALLAZGOS' y UN párrafo para 'CONCLUSIÓN'.
    2. PROHIBIDO poner: Nombre del paciente, fecha, título 'Informe Médico' o especialidad.
    3. PROHIBIDO usar listas, negritas o recomendaciones.
    4. El texto debe ser puramente descriptivo y técnico.
    """
    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":prompt}], temperature=0)
    return res.choices[0].message.content

def generar_word_final(info, texto_ia, f_pdf):
    doc = Document()
    
    # Encabezado Estilo Clínico
    tit = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Subencabezado de datos
    p_datos = doc.add_paragraph()
    p_datos.add_run(f"PACIENTE: {info['paciente']['Nombre']}\n").bold = True
    p_datos.add_run(f"FECHA: {info['paciente']['Fecha']}\n")
    p_datos.add_run(f"S/C: {info['paciente'].get('SC', 'N/A')} m²").bold = True

    # Texto clínico
    texto_limpio = texto_ia.replace("HALLAZGOS:", "").replace("Hallazgos:", "")
    partes = texto_limpio.upper().split("CONCLUSIÓN")

    doc.add_heading('Hallazgos', level=1)
    h_p = doc.add_paragraph(partes[0].strip())
    h_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY # <--- JUSTIFICADO

    if len(partes) > 1:
        doc.add_heading('Conclusión', level=1)
        c_p = doc.add_paragraph(partes[1].replace(":", "").strip())
        c_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY # <--- JUSTIFICADO

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
                run.add_picture(imgs[i], width=Inches(2.5))
    except: pass

    # Firma (Derecha y separada)
    doc.add_paragraph("\n\n\n")
    f_p = doc.add_paragraph()
    f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    if os.path.exists("firma_doctor.png"):
        f_p.add_run().add_picture("firma_doctor.png", width=Inches(1.8))
    else:
        f_p.add_run("__________________________\n").bold = True
        f_p.add_run("Firma y Sello del Médico").bold = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# Streamlit
st.title("CardioReport Pro 🩺")
f_xl = st.file_uploader("Excel Mejorado", type=["xlsx"])
f_pd = st.file_uploader("PDF Imágenes", type="pdf")

if f_xl and f_pd:
    if st.button("🚀 Generar Informe Final"):
        data = extraer_datos_mejorado(f_xl)
        txt = redactar_ia_final(data)
        archivo = generar_word_final(data, txt, f_pd)
        st.download_button("📥 Descargar Informe", archivo, f"Informe_{data['paciente']['Nombre']}.docx")
