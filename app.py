
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN
st.set_page_config(page_title="CardioReport Pro", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; font-family: Arial; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 2. FUNCIÓN DE GENERACIÓN DE WORD (CON SALTO DE PÁGINA)
def generar_word(texto, imagenes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Título Principal
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)

    lineas = texto.split('\n')
    for linea in lineas:
        linea = linea.strip()
        if not linea: continue
        
        # Salto de página automático antes de la conclusión
        if "IV. CONCLUSIÓN" in linea.upper():
            doc.add_page_break()
        
        p = doc.add_paragraph()
        texto_limpio = linea.replace('**', '')
        run = p.add_run(texto_limpio)
        
        # Negritas para secciones
        if any(enc in texto_limpio.upper() for enc in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    # Anexo de Imágenes (2 por fila)
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
            run_img.add_picture(io.BytesIO(img_bytes), width=Inches(2.8))

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 3. LÓGICA DE PROCESAMIENTO
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo = st.file_uploader("Subir PDF del Estudio", type=["pdf"])
    
    if archivo:
        # Extraer datos solo si no están en memoria
        if 'texto_raw' not in st.session_state:
            with fitz.open(stream=archivo.read(), filetype="pdf") as pdf:
                st.session_state.texto_raw = "".join([pag.get_text() for pag in pdf])
                st.session_state.imagenes = [pdf.extract_image(img[0])["image"] for pag in pdf for img in pag.get_images()]
        
        if st.button("GENERAR INFORME PROFESIONAL"):
            try:
                client = Groq(api_key=api_key)
                
                # Prompt forzado para incluir Peso y Altura
                prompt = f"""
                ERES EL DR. PASTORE. REDACTA EL INFORME CON ESTOS DATOS: {st.session_state.texto_raw}
                
                DATOS OBLIGATORIOS:
                - Nombre: MANUEL BALEIRON
                - Peso: 80 kg, Altura: 169 cm, BSA: 1.95 m2.
                - DDVI: 61mm, DSVI: 46mm, Septum (DDSIV): 10mm, Pared Posterior (DDPP): 11mm, Aurícula: 42mm.
                - FEy: 31%, Motilidad: Hipocinesia global severa.
                - Vena Cava: 15mm, Relación E/A: 0.95.

                ESTRUCTURA:
                DATOS DEL PACIENTE:
                I. EVALUACIÓN ANATÓMICA:
                II. FUNCIÓN VENTRICULAR:
                III. EVALUACIÓN HEMODINÁMICA:
                IV. CONCLUSIÓN: (Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda)
                FIRMA: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )

                informe = resp.choices[0].message.content
                st.session_state.informe_generado = informe
                
                st.markdown(f'<div class="report-container">{informe}</div>', unsafe_allow_html=True)

                st.download_button(
                    label="📥 Descargar Informe en Word",
                    data=generar_word(informe, st.session_state.imagenes),
                    file_name=f"Informe_{archivo.name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.error("Configura la API KEY en los Secrets.")
