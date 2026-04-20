import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz  # PyMuPDF
import io
from groq import Groq

# ==========================================
# 1. CONFIGURACIÓN DE SEGURIDAD
# ==========================================
# Si tienes problemas con los "Secrets" de Streamlit, pega tu clave aquí abajo:
API_KEY_MANUAL = "TU_CLAVE_GSAK_AQUÍ" 

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = API_KEY_MANUAL

client = Groq(api_key=api_key)

# ==========================================
# 2. MOTOR DE EXTRACCIÓN (2 HOJAS)
# ==========================================
def extraer_datos_estacion(file):
    res = {"paciente": {}, "mediciones": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        
        # --- Hoja Ecodato ---
        df_eco = pd.read_excel(xls, "Ecodato", header=None).astype(str)
        res["paciente"]["nombre"] = df_eco.iloc[0, 1].replace("nan", "").strip().upper()
        res["paciente"]["fecha"] = df_eco.iloc[1, 1].replace("nan", "").split(" ")[0]
        res["paciente"]["sc"] = df_eco.iloc[10, 4].replace("nan", "").strip()

        for r in range(5, 20):
            sigla = df_eco.iloc[r, 0].strip().upper()
            val = df_eco.iloc[r, 1].replace("nan", "").strip()
            if sigla != "NAN" and val:
                res["mediciones"][sigla] = val

        # --- Hoja Doppler ---
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

# ==========================================
# 3. REDACCIÓN MÉDICA (IA)
# ==========================================
def redactar_ia(datos):
    prompt = f"""
    ERES CARDIÓLOGO. TRANSCRIPCIÓN TÉCNICA DE ESTUDIO.
    MEDICIONES: {datos['mediciones']}
    DOPPLER: {datos['doppler']}
    
    ESTRUCTURA:
    1. HALLAZGOS: DESCRIPCIÓN DE CAVIDADES Y VÁLVULAS.
    2. CONCLUSIÓN: DIAGNÓSTICO FINAL BREVE.
    
    REGLAS: TODO EN MAYÚSCULAS. LENGUAJE SECO Y TÉCNICO. SIN SUGERENCIAS.
    SI DDVI > 56 MM ESCRIBE 'DILATACIÓN DEL VI'.
    """
    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return res.choices[0].message.content

# ==========================================
# 4. GENERADOR DE WORD
# ==========================================
def generar_word(datos, texto_ia, f_pdf):
    doc = Document()
    
    # Cabecera
    h = doc.add_heading('Ecocardiograma 2D y Doppler Cardíaco Color', 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    p = doc.add_paragraph()
    p.add_run(f"PACIENTE: {datos['paciente']['nombre']}\n").bold = True
    p.add_run(f"FECHA: {datos['paciente']['fecha']} | S/C: {datos['paciente']['sc']} m²")

    # IA
    partes = texto_ia.upper().split("CONCLUSIÓN")
    doc.add_heading('HALLAZGOS', level=1)
    doc.add_paragraph(partes[0].replace("HALLAZGOS:", "").strip()).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    if len(partes) > 1:
        doc.add_heading('CONCLUSIÓN', level=1)
        doc.add_paragraph(partes[1].replace(":", "").strip()).bold = True

    # Imágenes 4x2
    if f_pdf:
        doc.add_page_break()
        doc.add_heading('ANEXO DE IMÁGENES', level=1)
        try:
            f_pdf.seek(0)
            pdf = fitz.open(stream=f_pdf.read(), filetype="pdf")
            imgs = []
            for page in pdf:
                for img in page.get_images():
                    imgs.append(io.BytesIO(pdf.extract_image(img[0])["image"]))
            
            tabla = doc.add_table(rows=0, cols=2)
            for i in range(0, min(len(imgs), 8), 2):
                row = tabla.add_row().cells
                for j in range(2):
                    if i + j < len(imgs):
                        row[j].paragraphs[0].add_run().add_picture(imgs[i+j], width=Inches(2.8))
        except: pass

    # Firma
    doc.add_paragraph("\n\n")
    tbl_f = doc.add_table(rows=1, cols=2)
    tbl_f.columns[0].width = Inches(4.5)
    celda = tbl_f.rows[0].cells[1]
    f_p = celda.paragraphs[0]
    f_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f_p.add_run("__________________________\n").bold = True
    f_p.add_run("FIRMA Y SELLO DEL MÉDICO").bold = True

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# ==========================================
# 5. INTERFAZ STREAMLIT
# ==========================================
st.set_page_config(page_title="CardioReport", layout="centered")
st.title("Generador de Informes Médicos 🩺")

# Aceptamos xls y xlsx para evitar problemas
f_xl = st.file_uploader("1. Subir Excel (Ecodato + Doppler)", type=["xlsx", "xls"])
f_pd = st.file_uploader("2. Subir PDF de Imágenes", type=["pdf"])

if f_xl and f_pd:
    if st.button("GENERAR INFORME FINAL"):
        with st.spinner("Procesando..."):
            datos = extraer_datos_estacion(f_xl)
            texto = redactar_ia(datos)
            doc_final = generar_word(datos, texto, f_pd)
            
            st.success(f"Informe de {datos['paciente']['nombre']} listo.")
            st.download_button("📥 DESCARGAR WORD", doc_final, file_name="Informe_Medico.docx")
