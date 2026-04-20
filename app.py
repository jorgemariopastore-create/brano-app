import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz
import io
from groq import Groq

# 1. SEGURIDAD: Leemos la clave de los Secrets (se configura en .streamlit/secrets.toml o en la nube)
if "GROQ_API_KEY" in st.secrets:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
else:
    st.error("⚠️ Error: No se encontró la clave API. Asegúrate de tener el archivo .streamlit/secrets.toml o configurarla en Streamlit Cloud.")
    st.stop()

# 2. MOTOR DE EXTRACCIÓN (Robusto para distintos formatos)
def extraer_datos_estacion(file):
    res = {"paciente": {}, "mediciones": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        df_eco = pd.read_excel(xls, "Ecodato", header=None)
        
        def get_val(r, c):
            val = df_eco.iloc[r, c]
            return str(val).replace("nan", "").strip()

        res["paciente"]["nombre"] = get_val(0, 1).upper()
        res["paciente"]["fecha"] = get_val(1, 1).split(" ")[0]
        res["paciente"]["sc"] = get_val(10, 4)

        for r in range(5, 20):
            sigla = str(df_eco.iloc[r, 0]).strip().upper()
            val = get_val(r, 1)
            if sigla != "NAN" and val:
                res["mediciones"][sigla] = val

        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler")
            for _, row in df_dop.iterrows():
                valvula = str(row.iloc[0]).upper()
                velocidad = str(row.iloc[1]).replace("nan", "")
                fila_texto = str(row.values).lower()
                if 'x' in fila_texto:
                    res["doppler"].append(f"{valvula}: VEL {velocidad} CM/S - HALLAZGO POSITIVO")
    except Exception as e:
        st.error(f"Error procesando el Excel: {e}")
        st.stop()
    return res

# 3. REDACCIÓN CON IA
def redactar_ia(datos):
    prompt = f"ERES CARDIÓLOGO. REDACTA INFORME TÉCNICO EN MAYÚSCULAS. DATOS: {datos['mediciones']} {datos['doppler']}"
    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return res.choices[0].message.content

# 4. GENERADOR DE WORD
def generar_word(datos, texto_ia, f_pdf):
    doc = Document()
    doc.add_heading('INFORME MÉDICO', 0)
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
f_xl = st.file_uploader("1. Excel (Ecodato + Doppler)", type=["xlsx", "xls"])
f_pd = st.file_uploader("2. PDF (Imágenes)", type=["pdf"])

if f_xl and f_pd:
    if st.button("GENERAR INFORME FINAL"):
        with st.spinner("Procesando datos y redactando..."):
            datos = extraer_datos_estacion(f_xl)
            texto = redactar_ia(datos)
            doc_final = generar_word(datos, texto, f_pd)
            st.success("¡Informe generado con éxito!")
            st.download_button("📥 DESCARGAR WORD", doc_final, "Informe_Medico.docx")
