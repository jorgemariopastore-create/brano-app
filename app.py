
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

def buscar_dato_mejorado(df, keyword):
    """Busca la palabra clave en el DF y devuelve la celda de la derecha"""
    for r in range(len(df)):
        for c in range(len(df.columns)):
            if keyword.lower() in str(df.iloc[r, c]).lower():
                try:
                    valor = str(df.iloc[r, c+1]).strip()
                    if valor.lower() != "nan" and valor != "":
                        return valor
                except: pass
    return "N/A"

def extraer_datos_formato_mejor(file):
    info = {"paciente": {}, "eco": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        df_eco = pd.read_excel(xls, "Ecodato", header=None)
        
        # Datos de cabecera según el nuevo formato 'Mejor.xlsx'
        info["paciente"]["Nombre"] = buscar_dato_mejorado(df_eco, "Paciente")
        info["paciente"]["Fecha"] = buscar_dato_mejorado(df_eco, "Fecha")
        
        # Intentamos capturar peso/altura si el médico los agrega en celdas vacías
        info["paciente"]["Peso"] = buscar_dato_mejorado(df_eco, "Peso")
        info["paciente"]["Altura"] = buscar_dato_mejorado(df_eco, "Altura")
        info["paciente"]["BSA"] = buscar_dato_mejorado(df_eco, "DUBOIS")

        # Mediciones de la tabla de cavidades
        mapeo = {
            "DDVI": "Diámetro Diastólico Ventrículo Izquierdo",
            "DSVI": "Diámetro Sistólico Ventrículo Izquierdo",
            "FA": "Fracción de Acortamiento",
            "DDVD": "Ventrículo Derecho",
            "DDAI": "Aurícula Izquierda",
            "DDSIV": "Septum Interventricular",
            "DDPP": "Pared Posterior",
            "AAO": "Apertura Aórtica"
        }
        
        for sigla, nombre in mapeo.items():
            # Buscamos en la primera columna la sigla exacta
            for r in range(len(df_eco)):
                if str(df_eco.iloc[r, 0]).strip().upper() == sigla:
                    val = df_eco.iloc[r, 1]
                    info["eco"][nombre] = val
                    break

        # Hoja Doppler
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler", header=None)
            for i in range(len(df_dop)):
                v = str(df_dop.iloc[i, 0])
                if any(x in v for x in ["Tric", "Pulm", "Mit", "Aór"]):
                    vel = df_dop.iloc[i, 1]
                    if str(vel).lower() != "nan":
                        info["doppler"].append(f"{v}: {vel} cm/s")
                        
    except Exception as e:
        st.error(f"Error procesando formato Mejor.xlsx: {e}")
    return info

def redactar_ia_estricta(info):
    prompt = f"""
    Eres un Cardiólogo. Redacta un informe médico con estos datos:
    Mediciones: {info['eco']}
    Doppler: {info['doppler']}
    
    INSTRUCCIONES:
    1. Sección 'HALLAZGOS': Escribe un párrafo técnico fluido. 
       - Si DDVI > 56mm, indica dilatación. 
       - Si FA < 27%, indica deterioro sistólico.
    2. Sección 'CONCLUSIÓN': Diagnóstico final en 2 o 3 líneas.
    
    PROHIBIDO: No uses viñetas. No des consejos de salud ni recomendaciones de estudios futuros.
    """
    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user","content":prompt}], temperature=0)
    return res.choices[0].message.content

def generar_word_profesional(info, texto_ia, f_pdf):
    doc = Document()
    
    # Encabezado
    titulo = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {info['paciente'].get('Nombre', 'N/A')}\n").bold = True
    p.add_run(f"FECHA: {info['paciente'].get('Fecha', '27/01/2026')}\n")
    p.add_run(f"PESO: {info['paciente'].get('Peso', '-')} kg | ALTURA: {info['paciente'].get('Altura', '-')} cm | SC: {info['paciente'].get('BSA', '-')} m²")

    # Cuerpo (Hallazgos y Conclusión)
    texto_ia = texto_ia.upper()
    partes = texto_ia.split("CONCLUSIÓN")
    
    doc.add_heading('Hallazgos', level=1)
    doc.add_paragraph(partes[0].replace("HALLAZGOS:", "").strip())
    
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
            tabla = doc.add_table(rows=4, cols=2)
            for i in range(min(len(imgs), 8)):
                run = tabla.rows[i//2].cells[i%2].paragraphs[0].add_run()
                run.add_picture(imgs[i], width=Inches(2.8))
    except: pass

    # Firma a la derecha
    doc.add_paragraph("\n\n")
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

# Streamlit UI
st.title("CardioReport (Formato Mejorado) 🩺")
f_xl = st.file_uploader("Subir Excel Mejor.xlsx", type=["xlsx", "xls"])
f_pd = st.file_uploader("Subir PDF de Imágenes", type="pdf")

if f_xl and f_pd:
    if st.button("🚀 Generar Informe"):
        datos = extraer_datos_formato_mejor(f_xl)
        informe_txt = redactar_ia_estricta(datos)
        word_file = generar_word_profesional(datos, informe_txt, f_pd)
        st.success(f"Informe de {datos['paciente']['Nombre']} generado.")
        st.download_button("📥 Descargar Word", word_file, f"Informe_{datos['paciente']['Nombre']}.docx")
