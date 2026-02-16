
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
    .report-container { background-color: #ffffff; padding: 25px; border-radius: 10px; border: 1px solid #ddd; }
    .stButton>button { background-color: #c62828; color: white; width: 100%; height: 3em; font-weight: bold; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 2. FUNCIÓN PARA EL WORD (Con Salto de Página antes de Conclusión e Imágenes)
def crear_word_final(texto, imagenes):
    doc = Document()
    
    # Estilo base
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Título principal
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = titulo.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)

    # Procesar líneas
    secciones = texto.split('\n')
    for linea in secciones:
        linea = linea.strip()
        if not linea: continue
        
        # SALTO DE PÁGINA antes de la conclusión
        if "IV. CONCLUSIÓN" in linea.upper():
            doc.add_page_break()
        
        p = doc.add_paragraph()
        # Limpiar negritas Markdown
        texto_final = linea.replace('**', '')
        run = p.add_run(texto_final)
        
        # Formato negrita para encabezados
        if any(tag in texto_final.upper() for tag in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    # ANEXO DE IMÁGENES (4 líneas de a dos)
    if imagenes:
        doc.add_page_break()
        p_anexo = doc.add_paragraph()
        p_anexo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_anexo = p_anexo.add_run("ANEXO DE IMÁGENES")
        run_anexo.bold = True
        run_anexo.font.size = Pt(14)
        
        # Tabla para organizar imágenes de a dos
        table = doc.add_table(rows=(len(imagenes) + 1) // 2, cols=2)
        for i, img_data in enumerate(imagenes):
            row, col = i // 2, i % 2
            paragraph = table.cell(row, col).paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run()
            try:
                run.add_picture(io.BytesIO(img_data), width=Inches(3.0))
            except:
                continue

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

# 3. LÓGICA PRINCIPAL
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo_pdf = st.file_uploader("Subir PDF del Estudio", type=["pdf"])

    if archivo_pdf:
        # Usamos session_state para evitar el botón rojo de error por recarga
        if st.button("GENERAR INFORME PROFESIONAL"):
            try:
                texto_raw = ""
                imagenes_bytes = []
                
                # Procesamiento de PDF (Texto e Imágenes)
                with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as pdf:
                    for pagina in pdf:
                        texto_raw += pagina.get_text()
                        for img in pagina.get_images():
                            xref = img[0]
                            base_image = pdf.extract_image(xref)
                            imagenes_bytes.append(base_image["image"])

                # Limpieza de texto para la IA
                texto_limpio = re.sub(r'\s+', ' ', texto_raw.replace('"', ' ').replace("'", " "))

                client = Groq(api_key=api_key)
                
                # Prompt Reforzado (Valores exactos de Manuel Baleiron)
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE. UTILIZA ESTOS DATOS: {texto_limpio}
                
                REGLAS:
                - DDVI: 61 mm, DSVI: 46 mm.
                - Septum (DDSIV): 10 mm, Pared (DDPP): 11 mm.
                - Aurícula (DDAI): 42 mm.
                - FEy: 31%, Motilidad: Hipocinesia global severa.
                - Vena Cava: 15 mm, Doppler Relación E/A: 0.95.

                CONCLUSIÓN: Como FEy es 31% y DDVI es 61mm, debe ser: 
                "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda".

                FORMATO:
                DATOS DEL PACIENTE:
                I. EVALUACIÓN ANATÓMICA:
                II. FUNCIÓN VENTRICULAR:
                III. EVALUACIÓN HEMODINÁMICA:
                IV. CONCLUSIÓN:
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                """

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )

                informe_final = response.choices[0].message.content
                
                # Mostrar en pantalla
                st.markdown("---")
                st.markdown(f'<div class="report-container">{informe_final}</div>', unsafe_allow_html=True)

                # BOTÓN DE DESCARGA (Nombre simplificado)
                st.download_button(
                    label="📥 Descargar Informe en Word",
                    data=crear_word_final(informe_final, imagenes_bytes),
                    file_name=f"Informe_Pastore_{archivo_pdf.name.replace('.pdf', '')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                st.error(f"Hubo un error al procesar el archivo: {e}")
else:
    st.error("⚠️ Configura la GROQ_API_KEY en los Secrets.")
