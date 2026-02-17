
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="CardioReport Pro", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 30px; border-radius: 15px; border: 1px solid #ccc; color: black; font-family: 'Arial', sans-serif; line-height: 1.5; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; border: none; }
    .stButton>button:hover { background-color: #b71c1c; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - MN 74144")

# 2. CARGADOR DE ARCHIVOS
archivo = st.file_uploader("📂 Subir PDF del ecógrafo SonoScape E3", type=["pdf"])

def generar_word_oficial(texto_informe, imagenes_bytes):
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

    # Procesar el texto
    for linea in texto_informe.split('\n'):
        linea = linea.strip()
        if not linea: continue
        
        # Salto de página antes de la Conclusión
        if "IV. CONCLUSIÓN" in linea.upper():
            doc.add_page_break()
            
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        
        # Negritas automáticas
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "PACIENTE", "FIRMA"]):
            run.bold = True

    # Añadir Firma si existe
    if os.path.exists("firma.jpg"):
        doc.add_paragraph()
        p_firma = doc.add_paragraph()
        p_firma.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_firma.add_run().add_picture("firma.jpg", width=Inches(1.8))

    # Anexo de Imágenes (Máximo 2 para estabilidad)
    if imagenes_bytes:
        doc.add_page_break()
        a = doc.add_paragraph()
        a.alignment = WD_ALIGN_PARAGRAPH.CENTER
        a.add_run("ANEXO DE IMÁGENES").bold = True
        
        for img in imagenes_bytes[:2]:
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.add_run().add_picture(io.BytesIO(img), width=Inches(4.5))

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 3. LÓGICA DE EXTRACCIÓN Y IA
api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    # Cacheamos el procesamiento del PDF para evitar el botón rojo
    if "pdf_text" not in st.session_state or st.session_state.get("pdf_name") != archivo.name:
        with st.spinner("Leyendo datos estructurados..."):
            pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            
            # Extraer texto bloque por bloque (evita desorden de tablas)
            bloques_texto = []
            for pagina in pdf:
                for b in pagina.get_text("blocks"):
                    bloques_texto.append(b[4])
            
            st.session_state.pdf_text = "\n".join(bloques_texto)
            st.session_state.pdf_name = archivo.name
            
            # Guardar solo miniaturas de imágenes para ahorrar memoria
            imgs = []
            for p in pdf:
                for img in p.get_images():
                    if len(imgs) < 2:
                        imgs.append(pdf.extract_image(img[0])["image"])
            st.session_state.pdf_imgs = imgs
            pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            
            # PROMPT CON "MAPEO DE ETIQUETAS"
            prompt = f"""
            ERES EL DR. FRANCISCO ALBERTO PASTORE. ANALIZA ESTE ESTUDIO DE SONOSCAPE E3.
            
            INSTRUCCIONES DE EXTRACCIÓN:
            1. Busca los números a la derecha de estas etiquetas: DDVI, DSVI, FA, DDSIV, DDPP, DRAO, DDAI.
            2. En el texto narrativo busca: FEy (ej. 31%), Motilidad (ej. Hipocinesia global severa), Vena Cava (ej. 15mm).
            3. En el Doppler busca: Relación E/A y Relación E/e'.

            FORMATO REQUERIDO:
            DATOS DEL PACIENTE: Nombre, Peso, Altura, BSA.
            I. EVALUACIÓN ANATÓMICA: (Valores de DDVI, DSVI, Septum, Pared, Aurícula, Vena Cava)
            II. FUNCIÓN VENTRICULAR: (FEy, FA, Motilidad, Hipertrofia)
            III. EVALUACIÓN HEMODINÁMICA: (Relación E/A, Relación E/e', Doppler valvular)
            IV. CONCLUSIÓN: (Diagnóstico médico final)

            REGLA DE ORO: NO inventes recomendaciones. Termina en: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO DEL PDF:
            {st.session_state.pdf_text}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            informe_final = resp.choices[0].message.content
            st.markdown(f'<div class="report-container">{informe_final}</div>', unsafe_allow_html=True)

            # Preparar descarga
            datos_word = generar_word_oficial(informe_final, st.session_state.pdf_imgs)
            st.download_button
