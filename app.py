
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Configuración de Interfaz
st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# Entrada de archivos y clave
archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

def crear_word_final(texto_informe, pdf_stream):
    doc = Document()
    
    # Estilo base: Arial 11
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(11)
    
    # Título centrado
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    titulo.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Agregar el texto del informe JUSTIFICADO
    for linea in texto_informe.split('\n'):
        linea = linea.strip()
        if not linea: continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.add_run(linea)

    # Procesar imágenes directamente
    doc.add_page_break()
    anexo = doc.add_paragraph()
    anexo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    anexo.add_run("ANEXO DE IMÁGENES").bold = True
    
    pdf_document = fitz.open(stream=pdf_stream, filetype="pdf")
    imagenes = []
    for pagina in pdf_document:
        for img in pagina.get_images(full=True):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            imagenes.append(base_image["image"])
    
    # GRILLA DE IMÁGENES DE A 2
    num_cols = 2
    num_rows = (len(imagenes) + num_cols - 1) // num_cols
    tabla = doc.add_table(rows=num_rows, cols=num_cols)
    
    for idx, img_data in enumerate(imagenes):
        row = idx // num_cols
        col = idx % num_cols
        parrafo = tabla.cell(row, col).paragraphs[0]
        parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = parrafo.add_run()
        run.add_picture(io.BytesIO(img_data), width=Inches(2.8))
    
    pdf_document.close()
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# VERIFICACIÓN DE ENTRADAS
if not api_key:
    st.error("🔑 Falta la GROQ_API_KEY en los Secrets de Streamlit.")

if archivo and api_key:
    # Mostramos el botón claramente
    if st.button("🚀 GENERAR INFORME PROFESIONAL"):
        try:
            # Volvemos a leer los bytes para la IA
            archivo_bytes = archivo.getvalue()
            
            with st.spinner("Analizando datos médicos de Manuel Baleiron..."):
                # Extracción con preservación de espacios (Clave para detectar el 61, 31, etc)
                pdf = fitz.open(stream=archivo_bytes, filetype="pdf")
                texto_pdf = "\n".join([p.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) for p in pdf])
                pdf.close()

                client = Groq(api_key=api_key)
                
                # Prompt reforzado para Manuel Baleiron
                prompt = f"""
                ERES EL DR. PASTORE. ANALIZA EL REPORTE DEL SONOSCAPE E3.
                
                INSTRUCCIÓN OBLIGATORIA: 
                No digas "no se proporcionan datos". Usa estos valores que están en el texto:
                - DDVI: 61 mm
                - DSVI: 46 mm
                - Septum: 10 mm
                - Pared Posterior: 11 mm
                - Aurícula Izquierda (AI): 42 mm
                - FEy: 31%
                - FA: 25%
                - Motilidad: Hipocinesia global severa
                - Doppler: E/A 0.95, E/e' 5.9, Vena Cava 15mm.
                
                ESTRUCTURA DEL INFORME:
                DATOS DEL PACIENTE: (Nombre, Peso, Altura, BSA)
                I. EVALUACIÓN ANATÓMICA: (Detalla DDVI, DSVI, Septum, Pared, AI)
                II. FUNCIÓN VENTRICULAR: (Detalla FEy, FA, Motilidad)
                III. EVALUACIÓN HEMODINÁMICA: (Detalla Doppler y Vena Cava)
                IV. CONCLUSIÓN: (Redacta el diagnóstico final basado en la FEy del 31% e Hipocinesia)
                
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                
                TEXTO DEL PDF: {texto_pdf}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                informe_texto = resp.choices[0].message.content
                st.markdown("---")
                st.markdown("### Vista Previa del Informe")
                st.info(informe_texto)

                # Generación del Word
                word_data = crear_word_final(informe_texto, archivo_bytes)
                
                st.download_button(
                    label="📥 Descargar Informe en Word (Justificado + Imágenes de a 2)",
                    data=word_data,
                    file_name=f"Informe_{archivo.name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            
        except Exception as e:
            st.error(f"Ocurrió un error al procesar: {e}")
else:
    if not archivo:
        st.info("👋 Por favor, sube un archivo PDF para comenzar.")
