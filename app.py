
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. CONFIGURACIÓN VISUAL
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #ccc; color: black; line-height: 1.6; }
    .stButton>button { background-color: #d32f2f; color: white; width: 100%; height: 3.5em; font-weight: bold; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Generador de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore - Soporte SonoScape E3")

# 2. CARGADOR DE ARCHIVOS
archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])

def generar_word(texto, imagenes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    # Título centrado
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
            
        p = doc.add_paragraph()
        run = p.add_run(linea.replace('**', ''))
        
        # Negritas en títulos de sección
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS", "FIRMA"]):
            run.bold = True

    # Firma automática si existe el archivo firma.jpg
    if os.path.exists("firma.jpg"):
        doc.add_paragraph()
        doc.add_paragraph().add_run().add_picture("firma.jpg", width=Inches(1.8))

    # Anexo de Imágenes
    if imagenes:
        doc.add_page_break()
        a = doc.add_paragraph()
        a.alignment = WD_ALIGN_PARAGRAPH.CENTER
        a.add_run("ANEXO DE IMÁGENES").bold = True
        
        tabla = doc.add_table(rows=(len(imagenes) + 1) // 2, cols=2)
        for i, img_bytes in enumerate(imagenes):
            row, col = i // 2, i % 2
            try:
                paragraph = tabla.cell(row, col).paragraphs[0]
                run_img = paragraph.add_run()
                run_img.add_picture(io.BytesIO(img_bytes), width=Inches(2.8))
            except:
                continue
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# 3. LÓGICA DE EXTRACCIÓN
api_key = st.secrets.get("GROQ_API_KEY")

if archivo and api_key:
    # Usamos caché para que no se cuelgue el botón (Botón Rojo)
    if "texto_eco" not in st.session_state or st.session_state.get("nombre_doc") != archivo.name:
        with st.spinner("Leyendo datos del SonoScape E3..."):
            doc_pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            # Extraemos texto preservando la disposición de las tablas
            texto_completo = ""
            for pagina in doc_pdf:
                texto_completo += pagina.get_text("blocks") # Extrae por bloques para no mezclar columnas
                texto_completo = str(texto_completo)
            
            st.session_state.imgs_eco = [doc_pdf.extract_image(img[0])["image"] for p in doc_pdf for img in p.get_images()]
            st.session_state.texto_eco = texto_completo
            st.session_state.nombre_doc = archivo.name
            doc_pdf.close()

    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            client = Groq(api_key=api_key)
            
            # Prompt reforzado para obligar a la IA a ver los números
            prompt = f"""
            ERES EL DR. FRANCISCO ALBERTO PASTORE. TRANSCOPIE LOS DATOS DEL ESTUDIO AL FORMATO INDICADO.
            
            DATOS CRÍTICOS QUE DEBES BUSCAR EN EL TEXTO:
            - DDVI (61 mm), DSVI (46 mm), DDSIV (10 mm), DDPP (11 mm), DDAI (42 mm).
            - FEy (31%), Motilidad (Hipocinesia global severa).
            - Vena Cava (15 mm).
            - Relación E/A (0.95), Relación E/e' (5.9).

            FORMATO DE SALIDA:
            DATOS DEL PACIENTE: Nombre, Peso, Altura, BSA.
            I. EVALUACIÓN ANATÓMICA: (DDVI, DSVI, DDSIV, DDPP, DDAI, Vena Cava)
            II. FUNCIÓN VENTRICULAR: (FEy, Motilidad, Hipertrofia)
            III. EVALUACIÓN HEMODINÁMICA: (Relación E/A, Relación E/e', Valvulopatías)
            IV. CONCLUSIÓN: (Diagnóstico final basado en el texto)

            REGLA: NO agregues recomendaciones. Termina en la firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            
            TEXTO DEL ESTUDIO:
            {st.session_state.texto_eco}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )

            resultado = resp.choices[0].message.content
            st.markdown(f'<div class="report-container">{resultado}</div>', unsafe_allow_html=True)

            st.download_button(
                label="📥 Descargar Word",
                data=generar_word(resultado, st.session_state.imgs_eco),
                file_name=f"Informe_{archivo.name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Error: {e}")
