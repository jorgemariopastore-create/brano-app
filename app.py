
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
    .report-container { background-color: white; padding: 30px; border-radius: 10px; border: 1px solid #ccc; color: black; font-family: Arial; line-height: 1.6; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; border: none; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - MN 74144")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])

def crear_word_profesional(texto_informe, imagenes_bytes):
    doc = Document()
    
    # Título Principal
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_t = t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run_t.bold = True
    run_t.underline = True
    run_t.size = Pt(14)

    # Procesar Texto con Negritas y Subrayados en Títulos
    for linea in texto_informe.split('\n'):
        linea = linea.strip()
        if not linea: continue
        
        p = doc.add_paragraph()
        # Detectar encabezados para darles formato
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "PACIENTE", "CONCLUSIÓN"]):
            run = p.add_run(linea)
            run.bold = True
            run.underline = True
        else:
            p.add_run(linea)

    # Firma a la derecha
    if os.path.exists("firma.jpg"):
        doc.add_paragraph()
        p_firma = doc.add_paragraph()
        p_firma.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_firma.add_run().add_picture("firma.jpg", width=Inches(1.5))

    # ANEXO DE IMÁGENES (Grilla de 4 por fila)
    if imagenes_bytes:
        doc.add_page_break()
        titulo_anexo = doc.add_paragraph()
        titulo_anexo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        titulo_anexo.add_run("ANEXO DE IMÁGENES").bold = True
        
        num_cols = 4
        num_rows = (len(imagenes_bytes) + num_cols - 1) // num_cols
        tabla = doc.add_table(rows=num_rows, cols=num_cols)
        
        for idx, img_data in enumerate(imagenes_bytes):
            row = idx // num_cols
            col = idx % num_cols
            celda = tabla.cell(row, col)
            parrafo_img = celda.paragraphs[0]
            parrafo_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_img = parrafo_img.add_run()
            run_img.add_picture(io.BytesIO(img_data), width=Inches(1.5))

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    # Usamos la extracción que SÍ funcionó para ver los datos (Mapeo Espacial)
    if "pdf_data" not in st.session_state or st.session_state.get("last_file") != archivo.name:
        with st.spinner("Leyendo reporte médico..."):
            pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            st.session_state.pdf_text = "\n".join([p.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) for p in pdf])
            
            # Extraer imágenes para el anexo
            imgs = []
            for pagina in pdf:
                for img in pagina.get_images(full=True):
                    base_img = pdf.extract_image(img[0])
                    imgs.append(base_img["image"])
            
            st.session_state.pdf_imgs = imgs
            st.session_state.last_file = archivo.name
            pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            prompt = f"""
            ACTÚA COMO EL DR. PASTORE. EXTRAE LOS DATOS DEL SONOSCAPE E3.
            
            IMPORTANTE: Los números están en el texto. Busca DDVI (61), FEy (31%), etc.
            
            FORMATO:
            DATOS DEL PACIENTE:
            I. EVALUACIÓN ANATÓMICA:
            II. FUNCIÓN VENTRICULAR:
            III. EVALUACIÓN HEMODINÁMICA:
            IV. CONCLUSIÓN:
            
            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO:
            {st.session_state.pdf_text}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            st.session_state.informe_final = resp.choices[0].message.content
            st.markdown(f'<div class="report-container">{st.session_state.informe_final}</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error: {e}")

    if "informe_final" in st.session_state:
        # Generar el Word con el formato recuperado y las imágenes
        word_data = crear_word_profesional(st.session_state.informe_final, st.session_state.pdf_imgs)
        st.download_button(
            label="📥 Descargar Informe en Word",
            data=word_data,
            file_name=f"Informe_{archivo.name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
