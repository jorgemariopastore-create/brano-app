
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# Selectores de archivos
col1, col2 = st.columns(2)
with col1:
    archivo_datos = st.file_uploader("1. Reporte de Datos (TXT o DOCX)", type=["txt", "docx"])
with col2:
    archivo_pdf = st.file_uploader("2. Reporte PDF (Imágenes)", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY")

def extraer_texto_datos(archivo):
    """Extrae texto de TXT o DOCX de forma limpia."""
    if archivo.name.endswith('.docx'):
        return docx2txt.process(archivo)
    return archivo.read().decode("latin-1", errors="ignore")

def generar_docx(texto, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    for linea in texto.split('\n'):
        linea = linea.strip()
        # Filtramos frases de error o duda de la IA
        if not linea or any(x in linea.lower() for x in ["especulativa", "no se proporciona", "lo siento"]): 
            continue
            
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["I.", "II.", "III.", "IV.", "DATOS DEL PACIENTE", "FIRMA:"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    if pdf_bytes:
        doc.add_page_break()
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
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

if archivo_datos and archivo_pdf and api_key:
    if st.button("🚀 GENERAR INFORME"):
        try:
            with st.spinner("Analizando datos del nuevo paciente..."):
                texto_crudo = extraer_texto_datos(archivo_datos)
                
                client = Groq(api_key=api_key)
                
                # PROMPT 100% DINÁMICO (Sin nombres fijos)
                prompt = f"""
                ERES EL DR. PASTORE. REDACTA EL INFORME BASADO EN LOS DATOS TÉCNICOS ADJUNTOS.
                
                INSTRUCCIONES CRÍTICAS:
                1. DATOS GENERALES: Busca y escribe el Nombre del Paciente, Peso, Altura y BSA que aparecen en el archivo.
                2. MEDICIONES: Busca en las secciones [MEASUREMENT] los valores de: 
                   - LVIDd (DDVI), LVIDs (DSVI), IVSd (Septum), LVPWd (Pared).
                   - EF (FEy) y FS (FA).
                   - E/A y E/e' (si están disponibles).
                3. LÓGICA DE CONCLUSIÓN: 
                   - Si la FEy (EF) es mayor o igual a 55%: "Función ventricular conservada".
                   - Si la FEy (EF) es menor a 50%: "Disfunción ventricular".
                4. FORMATO: 
                   DATOS DEL PACIENTE:
                   I. EVALUACIÓN ANATÓMICA
                   II. FUNCIÓN VENTRICULAR
                   III. EVALUACIÓN HEMODINÁMICA
                   IV. CONCLUSIÓN
                
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144

                DATOS DEL ARCHIVO:
                {texto_crudo[:15000]}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = resp.choices[0].message.content
                st.markdown("### Previsualización del Informe")
                st.info(resultado)
                
                docx_out = generar_docx(resultado, archivo_pdf.getvalue())
                st.download_button("📥 Descargar Word", docx_out, "Informe_Cardiologico.docx")
                
        except Exception as e:
            st.error(f"Error: {e}")
