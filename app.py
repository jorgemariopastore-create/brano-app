
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="CardioReport Pro - SonoScape E3", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; font-family: Arial; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Generador de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - Soporte SonoScape E3")

# 2. FUNCIÓN PARA EL WORD (ESTRICTA Y PROFESIONAL)
def generar_word_universal(texto, imagenes):
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
        
        # SALTO DE PÁGINA antes de Conclusión
        if "IV. CONCLUSIÓN" in linea.upper():
            doc.add_page_break()
            
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        
        # Negritas automáticas para secciones principales
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    # Espacio para Firma Física (si existe firma.jpg)
    if os.path.exists("firma.jpg"):
        doc.add_paragraph()
        p_firma = doc.add_paragraph()
        p_firma.add_run().add_picture("firma.jpg", width=Inches(1.8))

    # ANEXO DE IMÁGENES (2 por fila)
    if imagenes:
        doc.add_page_break()
        a = doc.add_paragraph()
        a.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_a = a.add_run("ANEXO DE IMÁGENES")
        run_a.bold = True
        
        # Creamos la tabla de anexo
        tabla = doc.add_table(rows=(len(imagenes) + 1) // 2, cols=2)
        for i, img_bytes in enumerate(imagenes):
            row, col = i // 2, i % 2
            celda_p = tabla.cell(row, col).paragraphs[0]
            celda_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            try:
                celda_p.add_run().add_picture(io.BytesIO(img_bytes), width=Inches(2.8))
            except:
                continue

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 3. LÓGICA DE PROCESAMIENTO
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo = st.file_uploader("Subir PDF (SonoScape E3)", type=["pdf"])
    
    if archivo:
        # Extraer una sola vez para evitar "Botón Rojo"
        if "session_id" not in st.session_state or st.session_state.get("file_id") != archivo.name:
            with st.spinner("Analizando reporte del ecógrafo..."):
                pdf = fitz.open(stream=archivo.read(), filetype="pdf")
                st.session_state.texto_raw = "".join([p.get_text() for p in pdf])
                st.session_state.imgs = [pdf.extract_image(img[0])["image"] for p in pdf for img in p.get_images()]
                st.session_state.file_id = archivo.name
                pdf.close()

        if st.button("GENERAR INFORME"):
            try:
                client = Groq(api_key=api_key)
                
                # Prompt mejorado: Universal y restrictivo
                prompt = f"""
                ACTÚA COMO EL DR. FRANCISCO ALBERTO PASTORE. 
                TRANSCOPIE LOS DATOS DEL ESTUDIO (SonoScape E3) AL SIGUIENTE FORMATO:

                FORMATO REQUERIDO:
                DATOS DEL PACIENTE: (Nombre, Peso, Altura, BSA)
                I. EVALUACIÓN ANATÓMICA: (Valores de cavidades: DDVI, DSVI, Septum, Pared, AI, etc.)
                II. FUNCIÓN VENTRICULAR: (FEy y Motilidad)
                III. EVALUACIÓN HEMODINÁMICA: (Vena Cava, Relación E/A, Relación E/e', Valvulopatías)
                IV. CONCLUSIÓN: (Diagnóstico médico final)

                REGLAS DE ORO:
                1. NO agregues secciones de 'Recomendaciones', 'Comentarios' o 'Sugerencias'.
                2. TERMINA el informe inmediatamente después de la firma: 'Dr. FRANCISCO ALBERTO PASTORE - MN 74144'.
                3. Usa términos técnicos correctos: DDSIV es Septum, DDPP es Pared Posterior.
                4. Si un dato no existe en el texto, omite esa línea. No inventes.

                TEXTO DEL ESTUDIO:
                {st.session_state.texto_raw}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )

                informe = resp.choices[0].message.content
                st.markdown(f'<div class="report-container">{informe}</div>', unsafe_allow_html=True)

                # El botón de descarga ahora usa los datos guardados en session_state
                st.download_button(
                    label="📥 Descargar Informe en Word",
                    data=generar_word_universal(informe, st.session_state.imgs),
                    file_name=f"Informe_{archivo.name.replace('.pdf', '')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"Error técnico: {e}")
else:
    st.error("Configura la API KEY en Streamlit Cloud.")
