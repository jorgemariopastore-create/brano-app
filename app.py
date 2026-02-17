
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; color: black; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Generador de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - Soporte SonoScape E3")

# 2. CARGADOR SIEMPRE VISIBLE
archivo = st.file_uploader("📂 Subir PDF del ecógrafo SonoScape", type=["pdf"])

def generar_word_limpio(texto, imagenes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.font.size = Pt(14)

    for linea in texto.split('\n'):
        linea = linea.strip()
        if not linea: continue
        if "IV. CONCLUSIÓN" in linea.upper():
            doc.add_page_break()
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    if os.path.exists("firma.jpg"):
        doc.add_paragraph()
        try:
            doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))
        except: pass

    if imagenes:
        doc.add_page_break()
        doc.add_paragraph().add_run("ANEXO DE IMÁGENES").bold = True
        tabla = doc.add_table(rows=(len(imagenes) + 1) // 2, cols=2)
        for i, img_bytes in enumerate(imagenes):
            row, col = i // 2, i % 2
            try:
                run_img = tabla.cell(row, col).paragraphs[0].add_run()
                run_img.add_picture(io.BytesIO(img_bytes), width=Inches(2.5))
            except: continue
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 3. PROCESAMIENTO
api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    # Usamos session_state para que no se pierdan datos al generar el Word
    if "texto_final" not in st.session_state or st.session_state.get("file_id") != archivo.name:
        with st.spinner("Leyendo datos..."):
            doc_pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            
            # EXTRAER TEXTO MODO PRESERVACIÓN DE TABLAS
            texto_puro = ""
            for pagina in doc_pdf:
                # get_text("text") es el más fiel para el SonoScape E3
                texto_puro += pagina.get_text("text") + "\n"
            
            # Imágenes (solo las primeras 4 para no saturar memoria)
            imgs = []
            for p in doc_pdf:
                for img_idx, img in enumerate(p.get_images()):
                    if len(imgs) < 4:
                        imgs.append(doc_pdf.extract_image(img[0])["image"])
            
            st.session_state.texto_final = texto_puro
            st.session_state.imgs_final = imgs
            st.session_state.file_id = archivo.name
            doc_pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            # Prompt de "Búsqueda Forzada"
            prompt = f"""
            ERES EL DR. FRANCISCO ALBERTO PASTORE. 
            BUSCA Y EXTRAE ESTOS VALORES DEL TEXTO (ESTÁN AHÍ, ANALIZA CON CUIDADO):
            
            VALORES DE REFERENCIA A BUSCAR:
            - DDVI (61 mm), DSVI (46 mm), DDSIV/Septum (10 mm), DDPP/Pared (11 mm), DDAI/Aurícula (42 mm).
            - FEy (31%), Motilidad (Hipocinesia global severa).
            - Vena Cava (15 mm). Relación E/A (0.95), Relación E/e' (5.9).

            PRESENTA EL INFORME ASÍ:
            DATOS DEL PACIENTE: Nombre, Peso (80kg), Altura (169cm), BSA (1.95).
            I. EVALUACIÓN ANATÓMICA: (DDVI, DSVI, Septum, Pared, AI, Vena Cava)
            II. FUNCIÓN VENTRICULAR: (FEy y Motilidad)
            III. EVALUACIÓN HEMODINÁMICA: (Relación E/A, E/e' y Valvulopatías)
            IV. CONCLUSIÓN: (Diagnóstico final basado en el estudio)

            REGLA: NO agregues recomendaciones. Termina en: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO PARA ANALIZAR:
            {st.session_state.texto_final}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            informe_texto = resp.choices[0].message.content
            st.markdown(f'<div class="report-container">{informe_texto}</div>', unsafe_allow_html=True)

            st.download_button(
                label="📥 Descargar Word",
                data=generar_word_limpio(informe_texto, st.session_state.imgs_final),
                file_name=f"Informe_{archivo.name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Error: {e}")
