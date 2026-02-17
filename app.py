
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Configuración de la Página
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# Carga de archivos y API Key
archivo = st.file_uploader("📂 Subir PDF del ecógrafo (Sonoscape E3)", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

def crear_word_profesional(texto_informe, pdf_stream):
    """Genera el documento Word con texto justificado e imágenes de a 2."""
    doc = Document()
    
    # Estilo General: Arial 11
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    # Título Principal
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Cuerpo del Informe
    for linea in texto_informe.split('\n'):
        linea = linea.strip()
        # Filtro para que no pasen comentarios de la IA al Word
        if not linea or any(x in linea.lower() for x in ["lo siento", "disculpa", "nota:", "aquí tienes"]):
            continue
            
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        # Negritas automáticas para encabezados
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS DEL PACIENTE", "FIRMA:"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    # Anexo de Imágenes (Siempre en hoja nueva)
    doc.add_page_break()
    anexo_titulo = doc.add_paragraph()
    anexo_titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    anexo_titulo.add_run("ANEXO DE IMÁGENES").bold = True
    
    # Extraer imágenes del PDF
    pdf_document = fitz.open(stream=pdf_stream, filetype="pdf")
    imagenes = []
    for pagina in pdf_document:
        for img_index, img in enumerate(pagina.get_images(full=True)):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            imagenes.append(base_image["image"])
    
    # Grilla de 2 columnas (4 filas de 2 o las que necesite)
    if imagenes:
        num_cols = 2
        num_rows = (len(imagenes) + num_cols - 1) // num_cols
        tabla = doc.add_table(rows=num_rows, cols=num_cols)
        
        for idx, img_data in enumerate(imagenes):
            row = idx // num_cols
            col = idx % num_cols
            cell_p = tabla.cell(row, col).paragraphs[0]
            cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_img = cell_p.add_run()
            run_img.add_picture(io.BytesIO(img_data), width=Inches(2.8))
    
    pdf_document.close()
    
    # Guardar en buffer
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

# Lógica Principal
if not api_key:
    st.warning("⚠️ Configura la GROQ_API_KEY en los Secrets de Streamlit.")

if archivo and api_key:
    if st.button("🚀 GENERAR INFORME"):
        try:
            with st.spinner("Leyendo datos del ecógrafo y redactando..."):
                # Leer PDF
                pdf_bytes = archivo.read()
                pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
                # Extraemos texto preservando espacios para no perder valores de tablas
                texto_pdf = "\n".join([p.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) for p in pdf])
                pdf.close()

                client = Groq(api_key=api_key)
                
                # PROMPT DINÁMICO: Ya no tiene valores fijos. Ahora busca los del paciente actual.
                prompt = f"""
                ERES EL DR. PASTORE, MÉDICO CARDIÓLOGO.
                TU MISIÓN: Redactar un informe médico basado ÚNICAMENTE en el texto del PDF adjunto.
                
                INSTRUCCIONES CRÍTICAS:
                1. Extrae Nombre, ID, Peso, Altura y BSA de la sección de datos del paciente.
                2. Busca en las tablas de mediciones los valores de: DDVI, DSVI, Septum, Pared, AI, FEy y FA.
                3. Busca en la sección Doppler los valores de: E/A, E/e' y Vena Cava.
                4. Redacta una CONCLUSIÓN médica profesional acorde a la FEy y la motilidad encontrada.
                5. NO agregues notas al pie, disculpas ni comentarios personales. Solo el informe.
                
                ESTRUCTURA DEL INFORME:
                DATOS DEL PACIENTE:
                I. EVALUACIÓN ANATÓMICA:
                II. FUNCIÓN VENTRICULAR:
                III. EVALUACIÓN HEMODINÁMICA:
                IV. CONCLUSIÓN:
                
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                
                TEXTO DEL PDF:
                {texto_pdf}
                """
                
                # Llamada a la IA (Llama 3.3 70B para máxima precisión)
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0 # Temperatura 0 para evitar que invente datos
                )
                
                texto_final = completion.choices[0].message.content
                
                # Mostrar vista previa
                st.markdown("---")
                st.markdown("### Vista Previa del Informe")
                st.info(texto_final)

                # Crear el Word
                word_data = crear_word_profesional(texto_final, pdf_bytes)
                
                st.download_button(
                    label="📥 Descargar Word (Justificado + Imágenes)",
                    data=word_data,
                    file_name=f"Informe_{archivo.name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
        except Exception as e:
            st.error(f"Error técnico: {e}")
else:
    if not archivo:
        st.info("👋 Por favor, suba el archivo PDF del paciente para comenzar.")
