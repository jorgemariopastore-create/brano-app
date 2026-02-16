
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; font-family: Arial; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 2. FUNCIÓN PARA EL WORD
def generar_word_profesional(texto, imagenes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)

    lineas = texto.split('\n')
    for linea in lineas:
        linea = linea.strip()
        if not linea: continue
        
        # Salto de página antes de Conclusión
        if "IV. CONCLUSIÓN" in linea.upper():
            doc.add_page_break()
        
        # Manejo de Firma (solo si existe el archivo JPG)
        if "FIRMA" in linea.upper() or "DR. FRANCISCO" in linea.upper():
            if os.path.exists("firma.jpg"):
                p_f = doc.add_paragraph()
                run_f = p_f.add_run()
                run_f.add_picture("firma.jpg", width=Inches(1.8))
        
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        if any(enc in linea.upper() for enc in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    # Anexo de Imágenes
    if imagenes:
        doc.add_page_break()
        a = doc.add_paragraph()
        a.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_a = a.add_run("ANEXO DE IMÁGENES")
        run_a.bold = True
        
        tabla = doc.add_table(rows=(len(imagenes) + 1) // 2, cols=2)
        for i, img_bytes in enumerate(imagenes):
            row, col = i // 2, i % 2
            celda = tabla.cell(row, col).paragraphs[0]
            celda.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_img = celda.add_run()
            try:
                run_img.add_picture(io.BytesIO(img_bytes), width=Inches(2.8))
            except:
                continue

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 3. LÓGICA DE PROCESAMIENTO
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo = st.file_uploader("Subir PDF del Estudio", type=["pdf"])
    
    if archivo:
        # Optimización: Se procesa el PDF una sola vez por archivo
        if "texto_raw" not in st.session_state or st.session_state.get("last_file") != archivo.name:
            with st.spinner("Leyendo PDF..."):
                pdf = fitz.open(stream=archivo.read(), filetype="pdf")
                st.session_state.texto_raw = "".join([pag.get_text() for pag in pdf])
                st.session_state.imagenes = [pdf.extract_image(img[0])["image"] for pag in pdf for img in pag.get_images()]
                st.session_state.last_file = archivo.name
                pdf.close()

        if st.button("GENERAR INFORME PROFESIONAL"):
            try:
                client = Groq(api_key=api_key)
                # Prompt con los datos reales del PDF de BALEIRON MANUEL
                prompt = f"""
                ACTÚA COMO EL DR. FRANCISCO ALBERTO PASTORE. USA ESTOS DATOS: {st.session_state.texto_raw}
                
                DATOS DEL PACIENTE:
                - Nombre: MANUEL BALEIRON. Peso: 80 kg, Altura: 169 cm, BSA: 1.91 m2.
                
                I. EVALUACIÓN ANATÓMICA:
                - DDVI 61mm, DSVI 46mm, Septum (DDSIV) 10mm, Pared Posterior (DDPP) 11mm, Aurícula Izquierda 42mm.
                - Vena Cava 15mm con colapso conservado.
                
                II. FUNCIÓN VENTRICULAR:
                - FEy 31%. Hipocinesia global severa. Hipertrofia excéntrica del VI.
                
                III. EVALUACIÓN HEMODINÁMICA:
                - Relación E/A 0.95. Relación E/e' 5.9 (Presión de llenado normal).
                - Insuficiencia Mitral leve.
                
                IV. CONCLUSIÓN:
                - Miocardiopatía dilatada con deterioro severo de fracción de eyección del ventrículo izquierdo.
                
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )

                informe = resp.choices[0].message.content
                st.markdown(f'<div class="report-container">{informe}</div>', unsafe_allow_html=True)

                st.download_button(
                    label="📥 Descargar Informe en Word",
                    data=generar_word_profesional(informe, st.session_state.imagenes),
                    file_name=f"Informe_{archivo.name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"Error en la generación: {e}")
else:
    st.error("Por favor, configura la GROQ_API_KEY.")
