
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz
import io
from groq import Groq

# Configuración del Cliente
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def extraer_datos_quirurgico(file):
    info = {"paciente": {}, "eco": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        # Cargamos la hoja de datos tal cual
        df = pd.read_excel(xls, "Ecodato", header=None)
        
        # 1. Cabecera - Coordenadas Fijas (B1 y B2)
        info["paciente"]["Nombre"] = str(df.iloc[0, 1]).strip()
        info["paciente"]["Fecha"] = str(df.iloc[1, 1]).split(" ")[0]
        
        # 2. S/C - Coordenada Fija E11 (Índice 10, 4)
        val_sc = df.iloc[10, 4]
        info["paciente"]["SC"] = f"{float(val_sc):.2f}" if pd.notnull(val_sc) else "N/A"

        # 3. Mediciones (Extracción directa por filas conocidas)
        # Mapeamos los valores de la columna B según la etiqueta en columna A
        mediciones = {}
        for r in range(len(df)):
            label = str(df.iloc[r, 0]).strip().upper()
            val = df.iloc[r, 1]
            if label in ["DDVI", "DSVI", "FA", "DDVD", "DDAI", "DDSIV", "DDPP", "AAO"]:
                mediciones[label] = str(val)
        info["eco"] = mediciones

        # 4. Doppler (Hoja Doppler)
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler", header=None)
            for i in range(len(df_dop)):
                v = str(df_dop.iloc[i, 0])
                vel = str(df_dop.iloc[i, 1])
                if any(x in v for x in ["Tric", "Pulm", "Mit", "Aór"]) and vel != "nan":
                    info["doppler"].append(f"{v}: {vel} CM/S")
    except Exception as e:
        st.error(f"Error en extracción Senior: {e}")
    return info

def redactar_ia_senior_estricta(info):
    # Prompt diseñado para eliminar la "creatividad" y las sugerencias
    prompt = f"""
    ERES UN TRANSCRIPTOR MÉDICO. GENERA UN INFORME ECOCARDIOGRÁFICO BASADO EN ESTOS DATOS:
    CAVIDADES: {info['eco']}
    DOPPLER: {info['doppler']}
    
    ESTRUCTURA OBLIGATORIA:
    1. 'HALLAZGOS': DESCRIBE LAS DIMENSIONES DE LAS CAVIDADES Y LUEGO LOS HALLAZGOS DEL DOPPLER.
    2. 'CONCLUSIÓN': RESUMEN TÉCNICO DEL DIAGNÓSTICO.
    
    PROHIBICIONES:
    - NO SUGERIR TRATAMIENTOS NI PRUEBAS ADICIONALES.
    - NO USAR LA PALABRA 'SUGIERE' O 'RECOMIENDA'.
    - NO USAR SALUDOS NI INTRODUCCIONES.
    - TODO EL TEXTO DEBE ESTAR EN MAYÚSCULAS.
    """
    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return res.choices[0].message.content

def generar_word_senior_final(info, texto_ia, f_pdf):
    doc = Document()
    
    # Título Principal
    tit = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Datos del Paciente
    p_cab = doc.add_paragraph()
    p_cab.add_run("PACIENTE: ").bold = True
    p_cab.add_run(f"{info['paciente']['Nombre']}\n")
    p_cab.add_run("FECHA: ").bold = True
    p_cab.add_run(f"{info['paciente']['Fecha']}\n")
    p_cab.add_run("S/C: ").bold = True
    p_cab.add_run(f"{info['paciente']['SC']} m²")

    # Cuerpo del Informe
    partes = texto_ia.upper().split("CONCLUSIÓN")
    
    doc.add_heading('HALLAZGOS', level=1)
    h_para = doc.add_paragraph(partes[0].replace("HALLAZGOS:", "").strip())
    h_para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    if len(partes) > 1:
        doc.add_heading('CONCLUSIÓN', level=1)
        c_para = doc.add_paragraph(partes[1].replace(":", "").strip())
        c_para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Imágenes
    if f_pdf:
        doc.add_page_break()
        doc.add_heading('ANEXO DE IMÁGENES', level=1)
        try:
            f_pdf.seek(0)
            pdf = fitz.open(stream=f_pdf.read(), filetype="pdf")
            table = doc.add_table(rows=0, cols=2)
            for page in pdf:
                for img_info in page.get_images():
                    img_data = io.BytesIO(pdf.extract_image(img_info[0])["image"])
                    row_cells = table.add_row().cells
                    row_cells[0].paragraphs[0].add_run().add_picture(img_data, width=Inches(2.5))
        except: pass

    # BLOQUE DE FIRMA (ESTILO SENIOR: TABLA DE POSICIONAMIENTO)
    doc.add_paragraph("\n\n\n")
    table_f = doc.add_table(rows=1, cols=2)
    table_f.columns[0].width = Inches(4.5) # Espacio vacío a la izquierda
    celda_firma = table_f.rows[0].cells[1]
    
    f_p = celda_firma.paragraphs[0]
    f_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f_p.add_run("__________________________\n").bold = True
    f_p.add_run("FIRMA Y SELLO DEL MÉDICO").bold = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# Streamlit UI
st.title("CardioReport Senior V8 🩺")
f_xl = st.file_uploader("Subir Mejor.xlsx", type=["xlsx"])
f_pd = st.file_uploader("Subir Imágenes PDF", type="pdf")

if f_xl and f_pd:
    if st.button("GENERAR INFORME PROFESIONAL"):
        datos = extraer_datos_quirurgico(f_xl)
        texto = redactar_ia_senior_estricta(datos)
        word = generar_word_senior_final(datos, texto, f_pd)
        st.download_button("📥 Descargar Informe", word, f"Informe_{datos['paciente']['Nombre']}.docx")
