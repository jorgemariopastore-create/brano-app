
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz
import io
import os
from groq import Groq

# 1. CLIENTE GROQ
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def buscar_valor_flexible(df, clave):
    """Busca una palabra en cualquier parte del Excel y toma el valor de la derecha"""
    for r in range(len(df)):
        for c in range(len(df.columns)):
            celda = str(df.iloc[r, c]).lower()
            if clave.lower() in celda:
                # Intentamos tomar la celda de la derecha
                return str(df.iloc[r, c+1]).strip()
    return "N/A"

def procesar_excel_medico(file):
    """Extrae datos de un Excel llenado manualmente por el médico"""
    datos = {"paciente": {}, "mediciones": "", "doppler": ""}
    
    try:
        # Cargar las hojas (Ecodato y Doppler)
        xls = pd.ExcelFile(file)
        df_eco = pd.read_excel(xls, "Ecodato", header=None)
        
        # Datos del encabezado (Punto 5)
        datos["paciente"]["Nombre"] = buscar_valor_flexible(df_eco, "Paciente")
        datos["paciente"]["Peso"] = buscar_valor_flexible(df_eco, "Peso")
        datos["paciente"]["Altura"] = buscar_valor_flexible(df_eco, "Altura")
        datos["paciente"]["BSA"] = buscar_valor_flexible(df_eco, "DUBOIS") # Superficie corporal

        # Mediciones técnicas (Punto 1 y 3)
        # Buscamos las siglas comunes que el médico suele anotar
        dicc_siglas = {
            "DDVI": "Diámetro Diastólico Ventrículo Izquierdo",
            "DSVI": "Diámetro Sistólico Ventrículo Izquierdo",
            "FA": "Fracción de Acortamiento",
            "DDVD": "Diámetro Ventrículo Derecho",
            "DDAI": "Diámetro Aurícula Izquierda",
            "DDSIV": "Septum Interventricular",
            "DDPP": "Pared Posterior"
        }
        
        for sigla, nombre_largo in dicc_siglas.items():
            valor = buscar_valor_flexible(df_eco, sigla)
            if valor != "N/A":
                datos["mediciones"] += f"- {nombre_largo}: {valor}\n"

        # Datos Doppler
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler", header=None)
            for i in range(len(df_dop)):
                valvula = str(df_dop.iloc[i, 0])
                if valvula in ["Tricúspide", "Pulmonar", "Mitral", "Aórtica"]:
                    datos["doppler"] += f"- Válvula {valvula}: {df_dop.iloc[i, 1]} cm/s\n"
                    
    except Exception as e:
        st.error(f"Error leyendo el Excel manual: {e}")
    return datos

def redactar_informe_ia(info):
    """La IA redacta como médico, separando Hallazgos de Conclusión"""
    prompt = f"""
    Eres un Cardiólogo experto. Redacta un informe basado en estos datos:
    {info['mediciones']}
    {info['doppler']}

    INSTRUCCIONES DE FORMATO:
    1. Divide el texto en dos secciones claras: 'HALLAZGOS' y 'CONCLUSIÓN'.
    2. En HALLAZGOS: Usa párrafos fluidos (prosa), no listas. Menciona nombres completos.
    3. Analiza: Si el DDVI es > 56mm, indica que está aumentado. Si la FA es < 27%, indica deterioro sistólico.
    4. En CONCLUSIÓN: Da un diagnóstico final breve (máximo 3 líneas).
    5. No hables de obesidad ni des consejos de salud.
    """
    
    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return res.choices[0].message.content

def generar_word_medico(info, texto_ia, f_pdf):
    doc = Document()
    
    # 1. ENCABEZADO (Punto 5)
    doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {info['paciente'].get('Nombre', 'N/A')}\n").bold = True
    p.add_run(f"FECHA: 27/01/2026\n")
    p.add_run(f"PESO: {info['paciente'].get('Peso', '-')} kg | ALTURA: {info['paciente'].get('Altura', '-')} cm | SC: {info['paciente'].get('BSA', '-')} m²")

    # 2. CUERPO (Separando Hallazgos de Conclusión)
    # Buscamos dónde la IA puso la palabra "CONCLUSIÓN" para separar los bloques
    texto_limpio = texto_ia.replace("HALLAZGOS:", "").strip()
    partes = texto_limpio.split("CONCLUSIÓN")
    
    doc.add_heading('Hallazgos', level=1)
    doc.add_paragraph(partes[0].strip())
    
    if len(partes) > 1:
        doc.add_heading('Conclusión', level=1)
        doc.add_paragraph(partes[1].replace(":", "").strip())

    # 3. IMÁGENES (4x2)
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

    # 4. FIRMA (Punto 4)
    doc.add_paragraph("\n\n")
    firma_p = doc.add_paragraph()
    firma_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if os.path.exists("firma_doctor.png"):
        firma_p.add_run().add_picture("firma_doctor.png", width=Inches(1.8))
    else:
        firma_p.add_run("__________________________\nFirma del Médico").bold = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- INTERFAZ ---
st.title("Asistente de Informes Cardiológicos 🩺")
f_excel = st.file_uploader("Subir Excel (Ecodato y Doppler)", type=["xlsx", "xls"])
f_pdf = st.file_uploader("Subir PDF de Imágenes", type="pdf")

if f_excel and f_pdf:
    if st.button("Generar Informe Profesional"):
        with st.spinner("Procesando datos del médico..."):
            datos = procesar_excel_medico(f_excel)
            texto = redactar_informe_ia(datos)
            word = generar_word_medico(datos, texto, f_pdf)
            st.success("Informe redactado.")
            st.download_button("Descargar Informe Word", word, "Informe_Medico.docx")
