
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

def extraer_datos_coordenadas(file):
    info = {"paciente": {}, "eco": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        df_eco = pd.read_excel(xls, "Ecodato", header=None)
        
        # Extracción por posición fija según el último Excel enviado
        info["paciente"]["Nombre"] = str(df_eco.iloc[0, 1]).strip()
        info["paciente"]["Fecha"] = str(df_eco.iloc[1, 1]).split(" ")[0]
        
        # S/C está en la Columna E (4), Fila 11 (10)
        try:
            val_sc = df_eco.iloc[10, 4]
            info["paciente"]["SC"] = f"{float(val_sc):.2f}" if pd.notnull(val_sc) else "N/A"
        except:
            info["paciente"]["SC"] = "N/A"

        # Cavidades (Columna A y B)
        mapeo = {"DDVD": "Ventrículo Derecho", "DDVI": "Diámetro Diastólico VI", 
                 "DSVI": "Diámetro Sistólico VI", "FA": "Fracción de Acortamiento", 
                 "DDSIV": "Septum", "DDPP": "Pared Posterior", "AAO": "Apertura Aórtica"}
        
        for r in range(len(df_eco)):
            sigla = str(df_eco.iloc[r, 0]).strip().upper()
            if sigla in mapeo:
                info["eco"][mapeo[sigla]] = df_eco.iloc[r, 1]

        # Doppler (Hoja Doppler)
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler", header=None)
            for i in range(len(df_dop)):
                v = str(df_dop.iloc[i, 0])
                if any(x in v for x in ["Tric", "Pulm", "Mit", "Aór"]):
                    if pd.notnull(df_dop.iloc[i, 1]):
                        info["doppler"].append(f"{v}: {df_dop.iloc[i, 1]} cm/s")
    except Exception as e:
        st.error(f"Error técnico: {e}")
    return info

def redactar_ia_medica_pura(info):
    # Prompt ultra-seco para evitar el modo carta
    prompt = f"""
    Eres un transcriptor médico. Genera un informe técnico basado en: {info['eco']} y {info['doppler']}.
    
    REGLAS DE ORO:
    - Escribe el párrafo de 'HALLAZGOS' y el de 'CONCLUSIÓN'.
    - NO escribas saludos, ni introducciones, ni "estimado", ni instrucciones.
    - NO repitas datos del encabezado (Nombre, fecha, S/C).
    - Usa un tono descriptivo, frío y profesional.
    - Ejemplo: "Se observa dilatación del ventrículo izquierdo con DDVI de 61mm..."
    """
    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":prompt}], temperature=0)
    return res.choices[0].message.content

def generar_word_oficial(info, texto_ia, f_pdf):
    doc = Document()
    
    # Encabezado
    tit = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Bloque de datos
    p_datos = doc.add_paragraph()
    p_datos.add_run("PACIENTE: ").bold = True
    p_datos.add_run(f"{info['paciente']['Nombre']}\n")
    p_datos.add_run("FECHA: ").bold = True
    p_datos.add_run(f"{info['paciente']['Fecha']}\n")
    p_datos.add_run("S/C: ").bold = True
    p_datos.add_run(f"{info['paciente'].get('SC', 'N/A')} m²")

    # Contenido (Justificado)
    texto_limpio = texto_ia.replace("SECO, TÉCNICO, SIN SALUDOS.", "").strip()
    partes = texto_limpio.upper().split("CONCLUSIÓN")

    doc.add_heading('Hallazgos', level=1)
    h_p = doc.add_paragraph(partes[0].replace("HALLAZGOS:", "").strip())
    h_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    if len(partes) > 1:
        doc.add_heading('Conclusión', level=1)
        c_p = doc.add_paragraph(partes[1].replace(":", "").strip())
        c_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

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
                run.add_picture(imgs[i], width=Inches(2.6))
    except: pass

    # Firma Profesional
    doc.add_paragraph("\n\n\n\n")
    f_p = doc.add_paragraph()
    f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f_p.add_run("__________________________\n").bold = True
    f_p.add_run("Firma y Sello del Médico").bold = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# Streamlit App
st.title("CardioReport Oficial 🩺")
f_xl = st.file_uploader("Excel (Mejor.xlsx)", type=["xlsx"])
f_pd = st.file_uploader("PDF (Imágenes)", type="pdf")

if f_xl and f_pd:
    if st.button("Generar Informe"):
        data = extraer_datos_coordenadas(f_xl)
        txt = redactar_ia_medica_pura(data)
        word = generar_word_oficial(data, txt, f_pd)
        st.download_button("Descargar Informe", word, f"Informe_{data['paciente']['Nombre']}.docx")
