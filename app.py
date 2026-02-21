
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

def extraer_datos_fijos(file):
    info = {"paciente": {}, "eco": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        df_eco = pd.read_excel(xls, "Ecodato", header=None)
        
        # 1. Datos de cabecera por posición exacta (Ahorramos errores de búsqueda)
        info["paciente"]["Nombre"] = str(df_eco.iloc[0, 1]).strip()
        info["paciente"]["Fecha"] = str(df_eco.iloc[1, 1]).split(" ")[0]
        
        # 2. Superficie Corporal (S/C) - En tu Excel está en Fila 11, Columna E (index 10, 4)
        try:
            val_sc = df_eco.iloc[10, 4] 
            info["paciente"]["SC"] = f"{float(val_sc):.2f}" if pd.notnull(val_sc) else "N/A"
        except:
            info["paciente"]["SC"] = "N/A"

        # 3. Cavidades (Columna A = Nombre, Columna B = Valor)
        # Recorremos la columna A buscando las siglas clave
        mapeo = {"DDVD": "Ventrículo Derecho", "DDVI": "Diámetro Diastólico VI", 
                 "DSVI": "Diámetro Sistólico VI", "FA": "Fracción de Acortamiento", 
                 "DDSIV": "Septum", "DDPP": "Pared Posterior", "AAO": "Apertura Aórtica"}
        
        for r in range(len(df_eco)):
            celda_a = str(df_eco.iloc[r, 0]).strip().upper()
            if celda_a in mapeo:
                info["eco"][mapeo[celda_a]] = df_eco.iloc[r, 1]

        # 4. Doppler (Hoja "Doppler")
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler", header=None)
            for i in range(len(df_dop)):
                v = str(df_dop.iloc[i, 0])
                if any(x in v for x in ["Tric", "Pulm", "Mit", "Aór"]):
                    vel = df_dop.iloc[i, 1]
                    if pd.notnull(vel):
                        info["doppler"].append(f"{v}: {vel} cm/s")
                        
    except Exception as e:
        st.error(f"Error extrayendo datos: {e}")
    return info

def redactar_ia_tecnica(info):
    # Prompt diseñado para eliminar el "modo carta"
    prompt = f"""
    Genera un informe médico de ecocardiografía con este estilo: SECO, TÉCNICO, SIN SALUDOS.
    DATOS: {info['eco']} | DOPPLER: {info['doppler']}
    
    ESTRUCTURA:
    1. Escribe un párrafo de 'HALLAZGOS' usando lenguaje médico directo (ej: "Se evidencia dilatación del VI...").
    2. Escribe un párrafo de 'CONCLUSIÓN' con el diagnóstico principal.
    
    REGLAS:
    - NO uses "Estimado", "Paciente", "Fecha", ni títulos de especialidad.
    - NO uses negritas ni listas de puntos.
    - El texto debe ser un bloque de prosa técnica.
    """
    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":prompt}], temperature=0)
    return res.choices[0].message.content

def generar_word_sobrio(info, texto_ia, f_pdf):
    doc = Document()
    
    # Encabezado estándar
    tit = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    p_datos = doc.add_paragraph()
    p_datos.add_run("PACIENTE: ").bold = True
    p_datos.add_run(f"{info['paciente']['Nombre']}\n")
    p_datos.add_run("FECHA: ").bold = True
    p_datos.add_run(f"{info['paciente']['Fecha']}\n")
    p_datos.add_run("S/C: ").bold = True
    p_datos.add_run(f"{info['paciente'].get('SC', 'N/A')} m²")

    # Cuerpo del informe (Eliminamos cualquier rastro de la IA intentando poner nombres)
    texto_ia = texto_ia.upper()
    partes = texto_ia.split("CONCLUSIÓN")

    doc.add_heading('Hallazgos', level=1)
    hallazgos_p = doc.add_paragraph(partes[0].replace("HALLAZGOS:", "").strip())
    hallazgos_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    if len(partes) > 1:
        doc.add_heading('Conclusión', level=1)
        concl_p = doc.add_paragraph(partes[1].replace(":", "").strip())
        concl_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Imágenes (Anexo)
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

    # Firma a la derecha
    doc.add_paragraph("\n\n\n\n")
    f_p = doc.add_paragraph()
    f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f_p.add_run("__________________________\n").bold = True
    f_p.add_run("Firma y Sello del Médico").bold = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# Streamlit UI
st.title("CardioReport 5.6 🩺")
f_xl = st.file_uploader("Subir Mejor.xlsx", type=["xlsx"])
f_pd = st.file_uploader("Subir Imágenes PDF", type="pdf")

if f_xl and f_pd:
    if st.button("Generar Informe Profesional"):
        data = extraer_datos_fijos(f_xl)
        txt = redactar_ia_tecnica(data)
        word = generar_word_sobrio(data, txt, f_pd)
        st.success("¡Informe generado con éxito!")
        st.download_button("Descargar Informe", word, f"Informe_{data['paciente']['Nombre']}.docx")
