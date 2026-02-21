
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz
import io
import os
from groq import Groq

# 1. SEGURIDAD DE API
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("Error: No se encontró la API KEY en secrets.")

def extraer_datos_blindado(file):
    info = {"paciente": {}, "eco": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        df = pd.read_excel(xls, "Ecodato", header=None)
        
        # Coordenadas exactas (B1 y B2) - Usamos fillna para evitar el error 400
        info["paciente"]["Nombre"] = str(df.iloc[0, 1]).strip() if pd.notnull(df.iloc[0, 1]) else "PACIENTE NO IDENTIFICADO"
        info["paciente"]["Fecha"] = str(df.iloc[1, 1]).split(" ")[0] if pd.notnull(df.iloc[1, 1]) else "FECHA NO DISPONIBLE"
        
        # S/C corregida: Fila 12, Columna E del Excel (es índice 11, 4 en Python)
        # En tu Excel "Mejor.xlsx", la S/C está debajo de 'Índice Masa'
        try:
            val_sc = df.iloc[11, 4] 
            info["paciente"]["SC"] = f"{float(val_sc):.2f}" if pd.notnull(val_sc) else "N/A"
        except:
            info["paciente"]["SC"] = "N/A"

        # Cavidades (Columna A y B)
        mapeo = {"DDVD": "VD", "DDVI": "DDVI", "DSVI": "DSVI", "FA": "FA", 
                 "DDSIV": "Septum", "DDPP": "Pared Post.", "AAO": "Ao"}
        
        for r in range(len(df)):
            sigla = str(df.iloc[r, 0]).strip().upper()
            if sigla in mapeo:
                valor = df.iloc[r, 1]
                info["eco"][mapeo[sigla]] = str(valor) if pd.notnull(valor) else "S/D"

        # Doppler
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler", header=None)
            for i in range(len(df_dop)):
                v = str(df_dop.iloc[i, 0])
                if any(x in v for x in ["Tric", "Pulm", "Mit", "Aór"]):
                    vel = df_dop.iloc[i, 1]
                    if pd.notnull(vel):
                        info["doppler"].append(f"{v}: {vel} cm/s")
    except Exception as e:
        st.error(f"Error al leer el Excel: {e}")
    return info

def redactar_ia_ultra_concisa(info):
    # Validamos que haya datos para no enviar un prompt vacío (causa del error 400)
    if not info["eco"]:
        return "ERROR: NO SE ENCONTRARON MEDICIONES EN EL EXCEL."

    prompt = f"""
    Eres un Cardiólogo. Traduce estos datos a un informe médico formal.
    DATOS: {info['eco']} | DOPPLER: {info['doppler']}
    
    ESTILO EXIGIDO:
    - TODO EN MAYÚSCULAS.
    - USA LENGUAJE TÉCNICO SECO (Ej: 'DILATACIÓN MODERADA DE VI', 'FUNCIÓN SISTÓLICA CONSERVADA').
    - PROHIBIDO: NO USES 'HOLA', 'ESTIMADO', 'EL ESTUDIO MUESTRA'.
    - DIVIDE SOLO EN: 'HALLAZGOS' Y 'CONCLUSIÓN'.
    """
    try:
        res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":prompt}], temperature=0)
        return res.choices[0].message.content
    except Exception as e:
        return f"ERROR DE CONEXIÓN CON IA: {e}"

def generar_word_final(info, texto_ia, f_pdf):
    doc = Document()
    
    # Estilo de fuente global
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)

    # Encabezado
    tit = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Datos
    p = doc.add_paragraph()
    p.add_run("PACIENTE: ").bold = True
    p.add_run(f"{info['paciente']['Nombre']}\t\t")
    p.add_run("FECHA: ").bold = True
    p.add_run(f"{info['paciente']['Fecha']}\n")
    p.add_run("S/C: ").bold = True
    p.add_run(f"{info['paciente'].get('SC', 'N/A')} m²")

    # Separamos Hallazgos y Conclusión
    texto_ia = texto_ia.upper()
    partes = texto_ia.split("CONCLUSIÓN")

    doc.add_heading('HALLAZGOS', level=1)
    h_p = doc.add_paragraph(partes[0].replace("HALLAZGOS:", "").strip())
    h_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    if len(partes) > 1:
        doc.add_heading('CONCLUSIÓN', level=2)
        c_p = doc.add_paragraph(partes[1].replace(":", "").strip())
        c_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Imágenes
    if f_pdf:
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
                    run.add_picture(imgs[i], width=Inches(2.4))
        except: pass

    # BLOQUE DE FIRMA (FORZADO A LA DERECHA)
    for _ in range(6): doc.add_paragraph() # Espacio para el sello
    f_p = doc.add_paragraph()
    f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f_p.add_run("__________________________\n").bold = True
    f_p.add_run("FIRMA Y SELLO DEL MÉDICO   ").bold = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# Streamlit UI
st.title("CardioReport V6 (Estable) 🩺")

f_xl = st.file_uploader("Subir Excel", type=["xlsx"])
f_pd = st.file_uploader("Subir PDF", type="pdf")

if f_xl:
    if st.button("🚀 GENERAR INFORME"):
        with st.spinner("Procesando datos médicos..."):
            datos = extraer_datos_blindado(f_xl)
            texto = redactar_ia_ultra_concisa(datos)
            word_file = generar_word_final(datos, texto, f_pd)
            
            st.success("Informe generado.")
            st.download_button("📥 DESCARGAR WORD", word_file, f"Informe_{datos['paciente']['Nombre']}.docx")
