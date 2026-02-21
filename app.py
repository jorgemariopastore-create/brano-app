
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz  # PyMuPDF
import io
import os
from groq import Groq

# 1. CONFIGURACIÓN Y SEGURIDAD
st.set_page_config(page_title="Generador Cardio-IA", layout="wide")

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("Error: No se encontró la clave GROQ_API_KEY en los Secrets.")
    st.stop()

# --- FUNCIONES DE EXTRACCIÓN (SOLO EXCEL) ---

def buscar_dato_excel(datos, keywords):
    """Busca valores en el diccionario ignorando mayúsculas y caracteres extraños"""
    for k, v in datos.items():
        k_clean = str(k).lower().strip()
        if any(word in k_clean for word in keywords):
            return str(v).replace("nan", "").strip()
    return ""

def extraer_todo_el_excel(file):
    """Lee todas las hojas del Excel para captar Cálculos y Doppler"""
    datos_acumulados = {}
    try:
        # Cargamos todas las pestañas
        dict_dfs = pd.read_excel(file, sheet_name=None, header=None)
        for nombre_hoja, df in dict_dfs.items():
            for _, row in df.iterrows():
                if len(row) >= 2:
                    k = str(row[0]).strip()
                    v = row[1]
                    if k and k.lower() != "nan":
                        datos_acumulados[k] = v
        return datos_acumulados
    except Exception as e:
        st.error(f"Error crítico leyendo el Excel: {e}")
        return {}

def redactar_estilo_medico(datos_dict):
    """Convierte los datos del Excel en un informe narrativo técnico (Sin inventar)"""
    # Filtramos solo lo que tiene valor para no ensuciar el prompt
    contexto = "\n".join([f"{k}: {v}" for k, v in datos_dict.items() if str(v).strip() != ""])
    
    prompt = f"""
    Eres un cardiólogo redactando un informe real. 
    USA ÚNICAMENTE ESTOS DATOS DEL EXCEL:
    {contexto}

    INSTRUCCIONES DE FORMATO:
    1. Divide en: 'ECOCARDIOGRAMA 2D', 'DOPPLER CARDÍACO' y 'CONCLUSIÓN'.
    2. Redacta PÁRRAFOS con terminología médica, NO una lista de valores.
       - Si el Excel dice 'DDVI: 61', tú redactas 'Diámetro diastólico del ventrículo izquierdo de 61 mm'.
       - Si el Excel dice 'FE: 31%', tú redactas 'Deterioro severo de la función sistólica (FE 31%)'.
    3. El estilo debe ser sobrio y descriptivo. 
    4. La CONCLUSIÓN debe ser un resumen técnico de los valores más alterados presentes en los datos.
    5. NO inventes patologías que no se desprendan de los números entregados.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0 # Cero creatividad, máxima fidelidad al dato
        )
        return completion.choices[0].message.content
    except:
        return "Error en la conexión con la IA."

def generar_word_profesional(datos, texto_ia, pdf_file, firma_path):
    doc = Document()
    
    # --- CONFIGURACIÓN DE FUENTE ---
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)

    # 1. ENCABEZADO CENTRADO
    t = doc.add_heading('INFORME ECOCARDIOGRÁFICO Y DOPPLER COLOR', 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # 2. BLOQUE DE DATOS (Mapeo directo del Excel)
    nombre = buscar_dato_excel(datos, ["paciente", "nombre"])
    fecha = buscar_dato_excel(datos, ["fecha"])
    peso = buscar_dato_excel(datos, ["peso"])
    altura = buscar_dato_excel(datos, ["altura", "talla"])
    edad = buscar_dato_excel(datos, ["edad"])
    sc = buscar_dato_excel(datos, ["superficie", "s.c", "sc"])

    p_header = doc.add_paragraph()
    p_header.add_run(f"PACIENTE: {nombre}").bold = True
    p_header.add_run(f"\t\tFECHA: {fecha}").bold = True
    
    p_datos = doc.add_paragraph()
    p_datos.add_run(f"EDAD: {edad}  |  PESO: {peso} kg  |  ALTURA: {altura} cm  |  S.C: {sc} m²")
    
    doc.add_paragraph("_" * 75) # Línea divisoria técnica

    # 3. HALLAZGOS Y CONCLUSIÓN (JUSTIFICADO)
    for linea in texto_ia.split('\n'):
        if linea.strip():
            p = doc.add_paragraph(linea.strip())
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            # Resaltar encabezados de sección
            if any(x in linea for x in ["ECOCARDIOGRAMA 2D", "DOPPLER CARDÍACO", "CONCLUSIÓN"]):
                p.runs[0].bold = True

    # 4. ANEXO DE IMÁGENES (PDF - 4x2)
    doc.add_page_break()
    doc.add_heading('ANEXO DE IMÁGENES', level=1)
    try:
        pdf_doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        img_list = []
        for page in pdf_doc:
            for img_info in page.get_images(full=True):
                img_list.append(io.BytesIO(pdf_doc.extract_image(img_info[0])["image"]))

        if img_list:
            table = doc.add_table(rows=4, cols=2)
            for i in range(min(len(img_list), 8)):
                row, col = i // 2, i % 2
                paragraph = table.rows[row].cells[col].paragraphs[0]
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = paragraph.add_run()
                run.add_picture(img_list[i], width=Inches(2.8))
    except: pass

    # 5. FIRMA (Garantizada a la derecha)
    if os.path.exists(firma_path):
        doc.add_paragraph("\n\n")
        f_para = doc.add_paragraph()
        f_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        f_para.add_run().add_picture(firma_path, width=Inches(2.0))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- INTERFAZ ---
st.title("👨‍⚕️ Generador de Informes Médicos")

# Verificador de firma en pantalla
if os.path.exists("firma_doctor.png"):
    st.sidebar.success("✅ Firma cargada correctamente")
else:
    st.sidebar.error("❌ Falta 'firma_doctor.png' en el repositorio")

c1, c2 = st.columns(2)
with c1:
    f_excel = st.file_uploader("Subir Excel de Cálculos (Fuente de datos)", type=["xlsx", "xls"])
with c2:
    f_pdf = st.file_uploader("Subir PDF de Capturas (Fuente de imágenes)", type=["pdf"])

if f_excel and f_pdf:
    if st.button("🚀 Generar Informe Médico Final"):
        with st.spinner("Procesando datos del Excel..."):
            datos_excel = extraer_todo_el_excel(f_excel)
            texto_redactado = redactar_estilo_medico(datos_excel)
            docx_file = generar_word_profesional(datos_excel, texto_redactado, f_pdf, "firma_doctor.png")
            
            st.success("Informe generado con éxito.")
            st.download_button("📥 Descargar Word Justificado", docx_file, 
                               f"Informe_{buscar_dato_excel(datos_excel, ['paciente'])}.docx")
