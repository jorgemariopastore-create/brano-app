
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz
import io
import os
from groq import Groq

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def extraer_datos_coordenadas_final(file):
    info = {"paciente": {}, "eco": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        df = pd.read_excel(xls, "Ecodato", header=None)
        
        # Coordenadas exactas según Mejor.xlsx
        info["paciente"]["Nombre"] = str(df.iloc[0, 1]).strip() # Celda B1
        info["paciente"]["Fecha"] = str(df.iloc[1, 1]).split(" ")[0] # Celda B2
        
        # S/C está en Fila 11, Columna E (Índice 10, 4)
        try:
            val_sc = df.iloc[10, 4]
            info["paciente"]["SC"] = f"{float(val_sc):.2f}" if pd.notnull(val_sc) else "N/A"
        except:
            info["paciente"]["SC"] = "N/A"

        # Cavidades (Siglas en Columna A, Valores en Columna B)
        mapeo = {"DDVD": "VD", "DDVI": "DDVI", "DSVI": "DSVI", "FA": "FA", 
                 "DDSIV": "Septum", "DDPP": "Pared Post.", "AAO": "Ao"}
        
        for r in range(len(df)):
            sigla = str(df.iloc[r, 0]).strip().upper()
            if sigla in mapeo:
                info["eco"][mapeo[sigla]] = df.iloc[r, 1]

        # Doppler (Hoja Doppler)
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler", header=None)
            for i in range(len(df_dop)):
                v = str(df_dop.iloc[i, 0])
                if any(x in v for x in ["Tric", "Pulm", "Mit", "Aór"]):
                    if pd.notnull(df_dop.iloc[i, 1]):
                        info["doppler"].append(f"{v}: {df_dop.iloc[i, 1]} cm/s")
    except Exception as e:
        st.error(f"Error en lectura de celdas: {e}")
    return info

def redactar_ia_concisa(info):
    prompt = f"""
    Actúa como un cardiólogo redactando un informe técnico. 
    DATOS: {info['eco']} | DOPPLER: {info['doppler']}
    
    ESTILO OBLIGATORIO:
    - SIN introducciones. SIN frases como "se observa" o "el estudio muestra".
    - Usa frases nominales cortas. 
    - Ejemplo de formato: "Dilatación de cavidades izquierdas (DDVI 61mm). Deterioro sistólico moderado (FA 24%). Apertura valvular conservada."
    - Separa en dos secciones: 'HALLAZGOS' y 'CONCLUSIÓN'.
    - TODO EN MAYÚSCULAS.
    """
    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":prompt}], temperature=0)
    return res.choices[0].message.content

def generar_word_tecnico(info, texto_ia, f_pdf):
    doc = Document()
    
    # Encabezado
    tit = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Datos paciente
    p = doc.add_paragraph()
    p.add_run("PACIENTE: ").bold = True
    p.add_run(f"{info['paciente']['Nombre']}\n")
    p.add_run("FECHA: ").bold = True
    p.add_run(f"{info['paciente']['Fecha']}\n")
    p.add_run("S/C: ").bold = True
    p.add_run(f"{info['paciente'].get('SC', 'N/A')} m²")

    # Cuerpo del Informe (Justificado y técnico)
    texto_ia = texto_ia.upper()
    partes = texto_ia.split("CONCLUSIÓN")

    doc.add_heading('HALLAZGOS', level=1)
    h_txt = partes[0].replace("HALLAZGOS:", "").strip()
    h_p = doc.add_paragraph(h_txt)
    h_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    if len(partes) > 1:
        doc.add_heading('CONCLUSIÓN', level=1)
        c_txt = partes[1].replace(":", "").strip()
        c_p = doc.add_paragraph(c_txt)
        c_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Imágenes
    doc.add_page_break()
    doc.add_heading('ANEXO DE IMÁGENES', level=1)
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

    # BLOQUE DE FIRMA (A la derecha)
    for _ in range(5): doc.add_paragraph() # Espacio para el sello
    f_p = doc.add_paragraph()
    f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f_p.add_run("__________________________\n").bold = True
    f_p.add_run("FIRMA Y SELLO DEL MÉDICO").bold = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# UI
st.title("CardioReport 5.8 🩺")
f_xl = st.file_uploader("Subir Mejor.xlsx", type=["xlsx"])
f_pd = st.file_uploader("Subir PDF de Imágenes", type="pdf")

if f_xl and f_pd:
    if st.button("Generar Informe Médico"):
        data = extraer_datos_coordenadas_final(f_xl)
        txt = redactar_ia_concisa(data)
        word = generar_word_tecnico(data, txt, f_pd)
        st.download_button("Descargar Informe Word", word, f"Informe_{data['paciente']['Nombre']}.docx")
        
