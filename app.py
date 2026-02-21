
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

def buscar_dato_celda(df, palabras_clave):
    """Busca en todo el DataFrame una palabra clave y devuelve el valor de la derecha"""
    for r in range(len(df)):
        for c in range(len(df.columns)):
            valor_celda = str(df.iloc[r, c]).lower()
            for palabra in palabras_clave:
                if palabra.lower() in valor_celda:
                    # Intentamos obtener el valor de la derecha (columna+1)
                    try:
                        res = str(df.iloc[r, c + 1]).strip()
                        if res != "nan" and res != "": return res
                    except: pass
    return "N/A"

def extraer_datos_manuales(file):
    """Extrae datos de Excel manual buscando términos clave"""
    info = {"paciente": {}, "eco": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        df_eco = pd.read_excel(xls, "Ecodato", header=None)
        
        # Búsqueda de Paciente y Biometría
        info["paciente"]["Nombre"] = buscar_dato_celda(df_eco, ["Paciente", "Nombre", "Name"])
        info["paciente"]["Peso"] = buscar_dato_celda(df_eco, ["Peso", "Weight"])
        info["paciente"]["Altura"] = buscar_dato_celda(df_eco, ["Altura", "Height"])
        info["paciente"]["BSA"] = buscar_dato_celda(df_eco, ["DUBOIS", "SC", "Superficie"])

        # Mediciones Técnicas
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
            val = buscar_dato_celda(df_eco, [sigla])
            if val != "N/A":
                info["eco"][nombre] = val

        # Doppler
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler", header=None)
            for i in range(len(df_dop)):
                v = str(df_dop.iloc[i, 0])
                if v in ["Tricúspide", "Pulmonar", "Mitral", "Aórtica"]:
                    info["doppler"].append(f"{v}: {df_dop.iloc[i, 1]} cm/s")
                    
    except Exception as e:
        st.error(f"Error procesando el Excel: {e}")
    return info

def redactar_informe_ia(info):
    prompt = f"""
    Eres un Cardiólogo. Redacta un informe médico formal.
    DATOS: {info['eco']} | DOPPLER: {info['doppler']}
    
    ESTRUCTURA OBLIGATORIA:
    1. Título 'HALLAZGOS': Escribe en prosa técnica. Si el DDVI > 56mm indica dilatación del VI. Si FA < 27% indica deterioro sistólico.
    2. Título 'CONCLUSIÓN': Diagnóstico final en 2 líneas.
    
    REGLA: No menciones obesidad ni dieta. No uses listas de puntos.
    """
    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}], temperature=0)
    return res.choices[0].message.content

def generar_word_final(info, texto_ia, f_pdf):
    doc = Document()
    
    # Encabezado centrado
    titulo = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Datos del paciente en negrita
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {info['paciente'].get('Nombre', 'BALEIRON MANUEL')}\n").bold = True
    p.add_run(f"PESO: {info['paciente'].get('Peso', '-')} kg | ALTURA: {info['paciente'].get('Altura', '-')} cm | SC: {info['paciente'].get('BSA', '-')} m²")

    # Separación de secciones
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

    # FIRMA AL FINAL A LA DERECHA
    doc.add_paragraph("\n\n")
    firma_para = doc.add_paragraph()
    firma_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    # Intentamos cargar la firma
    if os.path.exists("firma_doctor.png"):
        run_firma = firma_para.add_run()
        run_firma.add_picture("firma_doctor.png", width=Inches(2.0))
    else:
        # Si no existe el archivo, creamos el espacio para que no quede vacío
        firma_para.add_run("__________________________\n").bold = True
        firma_para.add_run("Firma y Sello del Médico").bold = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- UI STREAMLIT ---
st.title("CardioReport Pro 🩺")
f_xl = st.file_uploader("Subir Excel", type=["xls", "xlsx"])
f_pd = st.file_uploader("Subir PDF", type="pdf")

if f_xl and f_pd:
    if st.button("Generar Informe"):
        data = extraer_datos_manuales(f_xl)
        texto = redactar_informe_ia(data)
        archivo = generar_word_final(data, texto, f_pd)
        st.download_button("Descargar Word", archivo, "Informe_Medico_Firmado.docx")
