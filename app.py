import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz
import io
from groq import Groq

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
# REEMPLAZA "TU_CLAVE_AQUI" POR TU CLAVE REAL DE GROQ
API_KEY_MANUAL = "TU_CLAVE_AQUI" 

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = API_KEY_MANUAL

if api_key == "TU_CLAVE_AQUI":
    st.error("⚠️ Error: Debes editar la línea 13 del código y pegar tu clave de Groq.")
    st.stop()

client = Groq(api_key=api_key)

# ==========================================
# 2. MOTOR DE EXTRACCIÓN (Corregido para floats)
# ==========================================
def extraer_datos_estacion(file):
    res = {"paciente": {}, "mediciones": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        
        # Hoja Ecodato
        df_eco = pd.read_excel(xls, "Ecodato", header=None)
        
        # Función auxiliar para convertir a string seguro
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

        # Hoja Doppler
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler")
            for _, row in df_dop.iterrows():
                valvula = str(row.iloc[0]).upper()
                velocidad = str(row.iloc[1]).replace("nan", "")
                # Convertimos la fila a string para buscar la 'x'
                fila_texto = str(row.values).lower()
                if 'x' in fila_texto:
                    res["doppler"].append(f"{valvula}: VEL {velocidad} CM/S - HALLAZGO POSITIVO")
    except Exception as e:
        st.error(f"Error técnico leyendo Excel: {e}")
        st.stop()
    return res

# ==========================================
# 3. REDACCIÓN MÉDICA
# ==========================================
def redactar_ia(datos):
    prompt = f"ERES CARDIOLOGO. REDACTA INFORME TECNICO EN MAYUSCULAS. DATOS: {datos['mediciones']} {datos['doppler']}"
    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return res.choices[0].message.content
    except Exception as e:
        st.error(f"Error de conexión con IA: {e}")
        st.stop()

# ==========================================
# 4. GENERADOR DE WORD
# ==========================================
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

# ==========================================
# 5. UI
# ==========================================
st.title("CardioReport 🩺")
f_xl = st.file_uploader("1. Excel (Ecodato + Doppler)", type=["xlsx", "xls"])
f_pd = st.file_uploader("2. PDF (Imágenes)", type=["pdf"])

if f_xl and f_pd:
    if st.button("GENERAR INFORME"):
        with st.spinner("Procesando..."):
            datos = extraer_datos_estacion(f_xl)
            texto = redactar_ia(datos)
            doc_final = generar_word(datos, texto, f_pd)
            st.success("¡Informe generado!")
            st.download_button("📥 DESCARGAR WORD", doc_final, "Informe_Medico.docx")
