
import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import fitz
import io
import os
from groq import Groq

# Inicialización segura de cliente
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def get_value_safe(df, row, col, default="N/A"):
    """Extrae valor de celda manejando nulos y errores de índice."""
    try:
        val = df.iloc[row, col]
        if pd.isna(val) or str(val).strip().lower() in ['nan', '']:
            return default
        return str(val).strip()
    except:
        return default

def extraer_datos_senior(file):
    info = {"paciente": {}, "eco": {}, "doppler": []}
    try:
        xls = pd.ExcelFile(file)
        df_eco = pd.read_excel(xls, "Ecodato", header=None)
        
        # 1. Extracción de Cabecera (Baleiron, Fecha, etc.)
        # Buscamos 'Paciente' y 'Fecha' en las primeras filas por si se desplazan
        info["paciente"]["Nombre"] = get_value_safe(df_eco, 0, 1)
        info["paciente"]["Fecha"] = get_value_safe(df_eco, 1, 1).split(' ')[0]
        
        # 2. Superficie Corporal (S/C) - Búsqueda Dinámica en la fila 11 o 12
        sc_val = "N/A"
        for r in range(8, 15): # Rango de seguridad donde suele estar S/C
            fila_str = " ".join(map(str, df_eco.iloc[r].values)).lower()
            if "masa" in fila_str or "dubois" in fila_str or "sup." in fila_str:
                # El valor suele estar en la columna E (4)
                potential_val = df_eco.iloc[r, 4]
                if pd.notnull(potential_val) and isinstance(potential_val, (int, float)):
                    sc_val = f"{float(potential_val):.2f}"
                    break
        info["paciente"]["SC"] = sc_val

        # 3. Mediciones de Cavidades (Mapeo por siglas en Columna A)
        claves = {
            "DDVI": "Diámetro Diastólico VI",
            "DSVI": "Diámetro Sistólico VI",
            "FA": "Fracción de Acortamiento",
            "DDVD": "Ventrículo Derecho",
            "DDAI": "Aurícula Izquierda",
            "DDSIV": "Septum",
            "DDPP": "Pared Posterior"
        }
        for r in range(len(df_eco)):
            etiqueta = str(df_eco.iloc[r, 0]).strip().upper()
            if etiqueta in claves:
                val = df_eco.iloc[r, 1]
                info["eco"][claves[etiqueta]] = f"{val:.1f}" if isinstance(val, (int, float)) else str(val)

        # 4. Doppler (Hoja Doppler)
        if "Doppler" in xls.sheet_names:
            df_dop = pd.read_excel(xls, "Doppler")
            # Limpiamos nombres de columnas para evitar errores de espacios
            df_dop.columns = [str(c).strip() for c in df_dop.columns]
            for _, row in df_dop.iterrows():
                valvula = str(row.iloc[0])
                velocidad = str(row.iloc[1])
                if any(v in valvula for v in ["Tric", "Pulm", "Mit", "Aór"]) and velocidad != "nan":
                    info["doppler"].append(f"{valvula}: {velocidad} cm/seg")

    except Exception as e:
        st.error(f"Error crítico de lectura: {e}")
    return info

def redactar_ia_senior(info):
    if not info["eco"]: return "DATOS INSUFICIENTES PARA HALLAZGOS."
    
    # Prompt de Ingeniería: Forzamos el rol de experto y eliminamos la "creatividad" de la IA
    prompt = f"""
    ESTABLECE UN TONO MÉDICO FORMAL Y CONCISO. 
    DATOS DEL ECOCARDIOGRAMA: {info['eco']}
    DOPPLER: {info['doppler']}
    
    TAREA: Escribe los 'HALLAZGOS' y la 'CONCLUSIÓN'.
    REQUISITOS:
    - TODO EL TEXTO EN MAYÚSCULAS.
    - SIN INTRODUCCIONES NI DESPEDIDAS.
    - USA TERMINOLOGÍA TÉCNICA (EJ. 'DILATACIÓN VENTRICULAR', 'FUNCIÓN PRESERVADA').
    - SI DDVI > 56 MM, ES DILATACIÓN. SI FA < 27%, ES DISFUNCIÓN SISTÓLICA.
    """
    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Eres un cardiólogo experto redactando informes para colegas."},
                      {"role": "user", "content": prompt}],
            temperature=0.1
        )
        return res.choices[0].message.content
    except:
        return "ERROR EN PROCESAMIENTO CLÍNICO."

def generar_doc_senior(info, texto_ia, f_pdf):
    doc = Document()
    
    # Configuración de márgenes y estilo
    section = doc.sections[0]
    section.left_margin = Inches(1)
    
    # Título
    h = doc.add_heading('INFORME ECOCARDIOGRÁFICO', 0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Cuadro de Datos (Encabezado limpio)
    p = doc.add_paragraph()
    p.add_run("PACIENTE: ").bold = True
    p.add_run(f"{info['paciente']['Nombre']}\n")
    p.add_run("FECHA: ").bold = True
    p.add_run(f"{info['paciente']['Fecha']}\n")
    p.add_run("S/C: ").bold = True
    p.add_run(f"{info['paciente']['SC']} m²")

    # Contenido Médico (Justificado)
    texto_ia = texto_ia.upper()
    secciones = texto_ia.split("CONCLUSIÓN")
    
    doc.add_heading('HALLAZGOS', level=1)
    para_h = doc.add_paragraph(secciones[0].replace("HALLAZGOS:", "").strip())
    para_h.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    if len(secciones) > 1:
        doc.add_heading('CONCLUSIÓN', level=1)
        para_c = doc.add_paragraph(secciones[1].replace(":", "").strip())
        para_c.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Imágenes (Optimizado)
    if f_pdf:
        try:
            doc.add_page_break()
            doc.add_heading('ANEXO DE IMÁGENES', level=1)
            f_pdf.seek(0)
            pdf = fitz.open(stream=f_pdf.read(), filetype="pdf")
            table = doc.add_table(rows=0, cols=2)
            imgs = []
            for page in pdf:
                for img in page.get_images():
                    imgs.append(io.BytesIO(pdf.extract_image(img[0])["image"]))
            
            for i in range(0, min(len(imgs), 6), 2):
                row_cells = table.add_row().cells
                for j in range(2):
                    if i + j < len(imgs):
                        p = row_cells[j].paragraphs[0]
                        p.add_run().add_picture(imgs[i+j], width=Inches(2.8))
        except: pass

    # FIRMA (Solución Definitiva)
    # Se agrega una tabla invisible para anclar la firma a la derecha
    doc.add_paragraph("\n\n\n")
    table_firma = doc.add_table(rows=1, cols=2)
    table_firma.columns[0].width = Inches(4)
    celda_firma = table_firma.rows[0].cells[1]
    
    p_firma = celda_firma.paragraphs[0]
    p_firma.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_firma.add_run("__________________________\n").bold = True
    p_firma.add_run("FIRMA Y SELLO DEL MÉDICO").bold = True

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="CardioReport Senior", layout="centered")
st.title("CardioReport Senior 🩺")

xl = st.file_uploader("Excel Médico", type="xlsx")
pd_file = st.file_uploader("PDF Imágenes", type="pdf")

if xl and pd_file:
    if st.button("GENERAR INFORME MÉDICO"):
        with st.spinner("Ejecutando lógica de extracción..."):
            datos = extraer_datos_senior(xl)
            texto = redactar_ia_senior(datos)
            doc_final = generar_doc_senior(datos, texto, pd_file)
            
            st.success(f"Informe de {datos['paciente']['Nombre']} listo.")
            st.download_button("📥 Descargar Informe Word", doc_final, 
                             file_name=f"Informe_{datos['paciente']['Nombre']}.docx")
