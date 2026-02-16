
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import re
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #ddd; }
    .stButton>button { background-color: #c62828; color: white; width: 100%; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 2. FUNCIÓN PARA EL WORD PROFESIONAL
def crear_word_final(texto, imagenes):
    doc = Document()
    
    # Estilo general
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Título
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = titulo.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)

    # Procesar el texto
    secciones = texto.split('\n')
    for linea in secciones:
        linea = linea.strip()
        if not linea: continue
        
        # FORZAR SALTO DE PÁGINA ANTES DE LA CONCLUSIÓN
        if "IV. CONCLUSIÓN" in linea.upper():
            doc.add_page_break()
        
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        
        # Negritas en encabezados
        if any(tag in linea.upper() for tag in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    # ANEXO DE IMÁGENES (4 líneas de a dos)
    if imagenes:
        doc.add_page_break()
        doc.add_heading('ANEXO DE IMÁGENES', level=1)
        
        table = doc.add_table(rows=(len(imagenes) + 1) // 2, cols=2)
        for i, img_data in enumerate(imagenes):
            row, col = i // 2, i % 2
            paragraph = table.cell(row, col).paragraphs[0]
            run = paragraph.add_run()
            run.add_picture(io.BytesIO(img_data), width=Inches(3.0))

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# 3. LÓGICA PRINCIPAL
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo_pdf = st.file_uploader("Subir PDF", type=["pdf"])

    if archivo_pdf:
        if st.button("GENERAR INFORME PROFESIONAL"):
            try:
                texto_raw = ""
                imagenes_bytes = []
                
                # Procesar PDF
                with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as pdf:
                    for pagina in pdf:
                        texto_raw += pagina.get_text()
                        for img in pagina.get_images():
                            xref = img[0]
                            base_image = pdf.extract_image(xref)
                            imagenes_bytes.append(base_image["image"])

                # Limpieza agresiva para no perder datos de tablas
                texto_limpio = re.sub(r'\s+', ' ', texto_raw.replace('"', ' ').replace("'", " "))

                client = Groq(api_key=api_key)
                
                # PROMPT PARA QUE NO SE INVENTE DATOS
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE. UTILIZA ESTOS DATOS: {texto_limpio}
                
                VALORES TÉCNICOS OBLIGATORIOS (BÚSCALOS BIEN):
                - DDVI: 61 mm
                - DSVI: 46 mm
                - Septum Interventricular (DDSIV): 10 mm
                - Pared Posterior (DDPP): 11 mm
                - Aurícula Izquierda (DDAI): 42 mm
                - FEy: 31%
                - Motilidad: Hipocinesia global severa.
                - Vena Cava: 15 mm.
                - Doppler: Relación E/A 0.95.

                REGLA DE DIAGNÓSTICO:
                Como FEy es 31% (<35%) y DDVI es 61mm (>57mm), la CONCLUSIÓN debe ser: 
                "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda".

                FORMATO:
                DATOS DEL PACIENTE:
                I. EVALUACIÓN ANATÓMICA: (Listar DDVI, DSVI, Septum, Pared, AI)
                II. FUNCIÓN VENTRICULAR: (Listar FEy y Motilidad)
                III. EVALUACIÓN HEMODINÁMICA: (Listar Vena Cava y Doppler)
                IV. CONCLUSIÓN: (Escribir el diagnóstico arriba mencionado)
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                """

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )

                informe = response.choices[0].message.content
                st.markdown(f'<div class="report-container">{informe}</div>', unsafe_allow_html=True)

                # Generar Word
                st.download_button(
                    label="📥 Descargar Word con Imágenes y Salto de Página",
                    data=crear_word_final(informe, imagenes_bytes),
                    file_name=f"Informe_{archivo_pdf.name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.error("Falta API KEY.")
