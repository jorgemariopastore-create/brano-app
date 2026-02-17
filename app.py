
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Configuración de la interfaz
st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

archivo = st.file_uploader("📂 Subir PDF del ecógrafo", type=["pdf"])
api_key = st.secrets.get("GROQ_API_KEY")

def generar_docx_profesional(texto, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    for linea in texto.split('\n'):
        linea = linea.strip()
        # Filtro de seguridad para eliminar frases de "disculpa" de la IA
        if not linea or any(x in linea.lower() for x in ["lo siento", "no puedo", "falta de información", "espero que"]):
            continue
            
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        if any(h in linea.upper() for h in ["DATOS DEL PACIENTE", "I.", "II.", "III.", "IV.", "FIRMA:"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    doc.add_page_break()
    a = doc.add_paragraph()
    a.alignment = WD_ALIGN_PARAGRAPH.CENTER
    a.add_run("ANEXO DE IMÁGENES").bold = True
    
    pdf_file = fitz.open(stream=pdf_bytes, filetype="pdf")
    imgs = []
    for page in pdf_file:
        for img in page.get_images(full=True):
            imgs.append(pdf_file.extract_image(img[0])["image"])
    
    if imgs:
        tabla = doc.add_table(rows=(len(imgs)+1)//2, cols=2)
        for i, img_data in enumerate(imgs):
            run = tabla.cell(i//2, i%2).paragraphs[0].add_run()
            run.add_picture(io.BytesIO(img_data), width=Inches(2.8))
    pdf_file.close()
    
    target = io.BytesIO()
    doc.save(target)
    return target.getvalue()

if archivo and api_key:
    if st.button("🚀 GENERAR INFORME"):
        try:
            with st.spinner("Analizando tablas de mediciones con alta precisión..."):
                pdf = fitz.open(stream=archivo.read(), filetype="pdf")
                texto_pdf = ""
                for pagina in pdf:
                    # CAMBIO CLAVE: Extraemos palabras con su posición para no mezclar columnas
                    words = pagina.get_text("words", sort=True)
                    texto_pdf += " ".join([w[4] for w in words]) + "\n"
                pdf.close()

                client = Groq(api_key=api_key)
                
                # Prompt mejorado para detectar valores entre paréntesis y tablas Sonoscape
                prompt = f"""
ERES EL DR. FRANCISCO ALBERTO PASTORE. TU TAREA ES TRASCRIBIR LOS DATOS DEL PDF AL INFORME.

REGLAS DE EXTRACCIÓN PARA TABLAS SONOSCAPE:
1. DATOS DEL PACIENTE: Extrae Nombre, ID, Peso, Altura y BSA.
2. CAVIDADES: Busca DDVI, DSVI, Septum (DDSIV), Pared (DDPP) y AI (DDAI). Ignora los valores entre paréntesis (rangos de referencia).
3. FUNCIÓN: Extrae FEy (EF) y FA. 
4. DOPPLER: Extrae E/A, E/e' y Vena Cava.

LÓGICA MÉDICA:
- Si la FEy es >= 55% (como el 67% de Alicia): "Función ventricular conservada".
- Si la FEy es < 50%: "Disfunción ventricular".

FORMATO OBLIGATORIO:
DATOS DEL PACIENTE:
I. EVALUACIÓN ANATÓMICA:
II. FUNCIÓN VENTRICULAR:
III. EVALUACIÓN HEMODINÁMICA:
IV. CONCLUSIÓN:
Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144

TEXTO EXTRAÍDO DEL PDF:
{texto_pdf}
"""

                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = resp.choices[0].message.content
                st.info(resultado)
                
                docx_out = generar_docx_profesional(resultado, archivo.getvalue())
                st.download_button("📥 Descargar Informe Oficial", docx_out, f"Informe_{archivo.name}.docx")
                
        except Exception as e:
            st.error(f"Error: {e}")
