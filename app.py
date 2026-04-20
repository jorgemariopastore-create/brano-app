import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz
import io
from groq import Groq

# 1. SEGURIDAD: Pega tu clave AQUI (sin acentos)
# Ejemplo: API_KEY_MANUAL = "gsk_1234567890abcdef"
API_KEY_MANUAL = "TU_CLAVE_AQUI" 

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = API_KEY_MANUAL

client = Groq(api_key=api_key)

# 2. MOTOR DE EXTRACCIÓN
def extraer_datos_estacion(file):
    res = {"paciente": {}, "mediciones": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        df_eco = pd.read_excel(xls, "Ecodato", header=None).astype(str)
        res["paciente"]["nombre"] = df_eco.iloc[0, 1].replace("nan", "").strip().upper()
        res["paciente"]["fecha"] = df_eco.iloc[1, 1].replace("nan", "").split(" ")[0]
        res["paciente"]["sc"] = df_eco.iloc[10, 4].replace("nan", "").strip()

        for r in range(5, 20):
            sigla = df_eco.iloc[r, 0].strip().upper()
            val = df_eco.iloc[r, 1].replace("nan", "").strip()
            if sigla != "NAN" and val:
                res["mediciones"][sigla] = val

        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler").astype(str)
            for _, row in df_dop.iterrows():
                valvula = row.iloc[0].upper()
                velocidad = row.iloc[1].replace("nan", "")
                if row.str.contains('x', case=False).any():
                    res["doppler"].append(f"{valvula}: VEL {velocidad} CM/S - HALLAZGO POSITIVO")
    except Exception as e:
        st.error(f"Error leyendo Excel: {e}")
    return res

# 3. REDACCIÓN (Sin caracteres raros)
def redactar_ia(datos):
    prompt = f"ERES CARDIOLOGO. REDACTA INFORME TECNICO EN MAYUSCULAS. DATOS: {datos['mediciones']} {datos['doppler']}"
    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return res.choices[0].message.content

# 4. WORD (Sin errores)
def generar_word(datos, texto_ia, f_pdf):
    doc = Document()
    doc.add_heading('INFORME', 0)
    doc.add_paragraph(f"PACIENTE: {datos['paciente']['nombre']}")
    doc.add_paragraph(texto_ia)
    
    if f_pdf:
        doc.add_page_break()
        pdf = fitz.open(stream=f_pdf.read(), filetype="pdf")
        tabla = doc.add_table(rows=0, cols=2)
        for page in pdf:
            for img_info in page.get_images():
                img_data = io.BytesIO(pdf.extract_image(img_info[0])["image"])
                row = tabla.add_row().cells
                row[0].paragraphs[0].add_run().add_picture(img_data, width=Inches(2.5))
    
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# 5. UI
st.title("CardioReport 🩺")
f_xl = st.file_uploader("Excel", type=["xlsx", "xls"])
f_pd = st.file_uploader("PDF", type=["pdf"])

if f_xl and f_pd:
    if st.button("GENERAR"):
        datos = extraer_datos_estacion(f_xl)
        texto = redactar_ia(datos)
        doc_final = generar_word(datos, texto, f_pd)
        st.download_button("DESCARGAR", doc_final, "Informe.docx")
