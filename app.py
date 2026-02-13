
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF para PDFs
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI", page_icon="❤️", layout="wide")
st.title("❤️ CardioReport AI - Versión Profesional")

api_key = st.sidebar.text_input("Groq API Key:", type="password")

def generar_docx_profesional(texto_ia, imagenes):
    doc = Document()
    
    # 1. Estilo General
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)

    # 2. Encabezado
    hdr = doc.add_heading('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR', 0)
    hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 3. Procesar Contenido con Formato Estricto
    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea: continue
        
        p = doc.add_paragraph()
        # Detectar si es un título según tu modelo INFORMEJORGE1
        es_titulo = any(linea.startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"])
        
        if es_titulo:
            run = p.add_run(linea)
            run.bold = True
            run.underline = True
            p.paragraph_format.space_before = Pt(12)
        else:
            p.add_run(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(3)

    # 4. ANEXO: 8 IMÁGENES POR HOJA (2 col x 4 filas)
    if imagenes:
        doc.add_page_break()
        tit_anexo = doc.add_paragraph()
        r_anexo = tit_anexo.add_run('ANEXO: IMÁGENES DEL ESTUDIO')
        r_anexo.bold = True
        r_anexo.underline = True
        
        table = doc.add_table(rows=0, cols=2)
        for i in range(0, len(imagenes), 2):
            row_cells = table.add_row().cells
            for j in range(2):
                if i + j < len(imagenes):
                    img_data = imagenes[i+j]
                    cell_p = row_cells[j].paragraphs[0]
                    cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run_img = cell_p.add_run()
                    # Tamaño exacto para que entren 4 filas por hoja
                    run_img.add_picture(io.BytesIO(img_data), width=Inches(2.3))
                    cell_p.add_run(f"\nFig. {i + j + 1}")
    
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()

if api_key:
    client = Groq(api_key=api_key)
    archivos = st.file_uploader("Subir estudio", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        full_text = ""
        imgs_bytes = []
        for a in archivos:
            if a.type == "application/pdf":
                with fitz.open(stream=a.read(), filetype="pdf") as d:
                    for pag in d:
                        full_text += pag.get_text() + "\n"
                        pix = pag.get_pixmap()
                        imgs_bytes.append(pix.tobytes("png"))
            else:
                b = a.read()
                imgs_bytes.append(b)
                # Nota: Aquí se necesitaría OCR para leer texto de fotos puras

        if st.button("🚀 Generar Informe con Calidad Gemini"):
            with st.spinner("Procesando datos médicos..."):
                # PROMPT ULTIMATUM: Prohibido decir "no hay datos"
                prompt = f"""
                Eres un cardiólogo. Redacta el informe basado en este texto técnico: {full_text}
                
                ESTRUCTURA OBLIGATORIA (Modelo INFORMEJORGE1):
                DATOS DEL PACIENTE: Nombre, Edad, ID, Fecha.
                I. EVALUACIÓN ANATÓMICA Y CAVIDADES: Raíz Aórtica, Aurícula Izquierda, Vena Cava.
                II. FUNCIÓN VENTRICULAR IZQUIERDA: FEy (%) Simpson, VDF, VSF.
                III. EVALUACIÓN HEMODINÁMICA: Onda E, A, E/A, Doppler Tisular.
                IV. HALLAZGOS EXTRACARDÍACOS: Vena Porta, Renal.
                CONCLUSIÓN FINAL: Resumen de patologías.

                REGLA DE ORO: No inventes datos, pero no digas 'no se proporcionan'. 
                Si un dato no está en el texto, simplemente no menciones esa línea.
                Usa un tono asertivo como: 'Se observa...', 'Se evidencia...'.
                """
                
                try:
                    res = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0
                    )
                    
                    texto_final = res.choices[0].message.content
                    st.markdown(texto_final)
                    
                    word_file = generar_docx_profesional(texto_final, imgs_bytes)
                    st.download_button("📥 DESCARGAR WORD FINAL", word_file, "Informe_Cardio_Final.docx")
                except Exception as e:
                    st.error(f"Error de IA: {e}")
