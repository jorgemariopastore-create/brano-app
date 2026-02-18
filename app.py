
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
import docx2txt
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# 1. Configuración de la página
st.set_page_config(page_title="CardioReport Pro", layout="centered")
st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 2. Selectores de archivos
col1, col2 = st.columns(2)
with col1:
    archivo_datos = st.file_uploader("1. Reporte de Datos (TXT o DOCX)", type=["txt", "docx"])
with col2:
    archivo_pdf = st.file_uploader("2. Reporte PDF (Imágenes)", type=["pdf"])

api_key = st.secrets.get("GROQ_API_KEY")

def generar_docx_profesional(texto, pdf_bytes):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    # Título
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR").bold = True
    
    # Cuerpo del informe
    for linea in texto.split('\n'):
        linea = linea.strip()
        if not linea or any(x in linea.lower() for x in ["lo siento", "no hay datos", "especulativa"]):
            continue
            
        p = doc.add_paragraph()
        if any(h in linea.upper() for h in ["DATOS DEL PACIENTE", "I.", "II.", "III.", "IV.", "CONCLUSIÓN", "FIRMA"]):
            p.add_run(linea.replace("**", "")).bold = True
        else:
            p.add_run(linea.replace("**", ""))

    # Anexo de Imágenes
    if pdf_bytes:
        doc.add_page_break()
        par = doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.add_run("ANEXO DE IMÁGENES").bold = True
        
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

# 3. Lógica Principal
if archivo_datos and archivo_pdf and api_key:
    if st.button("🚀 GENERAR INFORME"):
        try:
            with st.spinner("Leyendo datos del archivo y procesando..."):
                # Extraer texto según el formato
                if archivo_datos.name.endswith('.docx'):
                    texto_crudo = docx2txt.process(archivo_datos)
                else:
                    texto_crudo = archivo_datos.read().decode("latin-1", errors="ignore")
                
                client = Groq(api_key=api_key)
                
                # Prompt Dinámico
                prompt = f"""
                ERES EL DR. FRANCISCO ALBERTO PASTORE. TU TAREA ES TRASCRIBIR LOS DATOS DEL REPORTE TÉCNICO AL INFORME MÉDICO FINAL.
                
                DATOS A EXTRAER:
                1. IDENTIFICACIÓN: Nombre del paciente, Edad, Peso, Altura y BSA (están en [PATINET INFO]).
                2. MEDICIONES: Busca LVIDd, LVIDs, IVSd, LVPWd, EF (FEy) y FS (FA).
                3. CONCLUSIÓN: 
                   - Si la FEy (EF) es >= 55%: "Función ventricular izquierda conservada".
                   - Si es menor, describe el grado de disfunción.
                
                FORMATO REQUERIDO:
                DATOS DEL PACIENTE:
                I. EVALUACIÓN ANATÓMICA:
                II. FUNCIÓN VENTRICULAR:
                III. EVALUACIÓN HEMODINÁMICA:
                IV. CONCLUSIÓN:
                
                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                
                REPORTE TÉCNICO PARA PROCESAR:
                {texto_crudo[:15000]}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                resultado = resp.choices[0].message.content
                st.markdown("### Vista Previa del Informe")
                st.info(resultado)
                
                # Generar archivo Word
                docx_out = generar_docx_profesional(resultado, archivo_pdf.getvalue())
                st.download_button(
                    label="📥 Descargar Informe Word",
                    data=docx_out,
                    file_name=f"Informe_{archivo_datos.name.split('.')[0]}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
        except Exception as e:
            st.error(f"Se produjo un error: {e}")
