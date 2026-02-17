
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN
st.set_page_config(page_title="CardioReport Pro", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; color: black; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Generador de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - SonoScape E3")

# 2. CARGADOR
archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])

def generar_word(texto, imagenes):
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

    for linea in texto.split('\n'):
        linea = linea.strip()
        if not linea: continue
        if "IV. CONCLUSIÓN" in linea.upper():
            doc.add_page_break()
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    # Firma JPG si existe
    if os.path.exists("firma.jpg"):
        doc.add_paragraph()
        doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))

    # Anexo de imágenes (Optimizado para evitar error de memoria)
    if imagenes:
        doc.add_page_break()
        doc.add_paragraph().add_run("ANEXO DE IMÁGENES").bold = True
        tabla = doc.add_table(rows=(len(imagenes) + 1) // 2, cols=2)
        for i, img_bytes in enumerate(imagenes):
            row, col = i // 2, i % 2
            try:
                run_img = tabla.cell(row, col).paragraphs[0].add_run()
                run_img.add_picture(io.BytesIO(img_bytes), width=Inches(2.5))
            except:
                continue
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 3. PROCESAMIENTO
api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    # Usamos session_state para evitar que el botón rojo aparezca al recargar
    if "data_cache" not in st.session_state or st.session_state.get("last_file") != archivo.name:
        with st.spinner("Analizando PDF..."):
            pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            texto = ""
            for pagina in pdf:
                texto += pagina.get_text("text") # Modo texto simple para mejor lectura de tablas
            
            # Guardamos imágenes de forma optimizada
            imgs = []
            for pag in pdf:
                for img in pag.get_images():
                    imgs.append(pdf.extract_image(img[0])["image"])
            
            st.session_state.data_cache = texto
            st.session_state.imgs_cache = imgs
            st.session_state.last_file = archivo.name
            pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            # Prompt ultra-específico para SonoScape E3
            prompt = f"""
            ERES EL DR. FRANCISCO ALBERTO PASTORE. EXTRAE LOS VALORES DEL SIGUIENTE TEXTO.
            
            DATOS A BUSCAR:
            1. DDVI, DSVI, DDSIV (Septum), DDPP (Pared), DDAI (Aurícula).
            2. FEy (Fracción de eyección del VI).
            3. Relación E/A y Relación E/e'.
            4. Vena Cava.
            5. Conclusión (Diagnóstico final).

            FORMATO DE SALIDA (ESTRICTO):
            DATOS DEL PACIENTE: Nombre, Peso, Altura, BSA.
            I. EVALUACIÓN ANATÓMICA: (Muestra los mm de DDVI, DSVI, Septum, Pared, AI)
            II. FUNCIÓN VENTRICULAR: (Muestra % de FEy y descripción de motilidad)
            III. EVALUACIÓN HEMODINÁMICA: (Muestra Vena Cava y Relaciones Doppler)
            IV. CONCLUSIÓN: (El diagnóstico médico final)

            REGLA DE ORO: NO inventes recomendaciones. Termina en: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO:
            {st.session_state.data_cache}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            informe = resp.choices[0].message.content
            st.markdown(f'<div class="report-container">{informe}</div>', unsafe_allow_html=True)

            st.download_button(
                label="📥 Descargar Word",
                data=generar_word(informe, st.session_state.imgs_cache),
                file_name=f"Informe_{archivo.name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Error: {e}")
