
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI", layout="wide")
st.title("❤️ CardioReport AI - Versión Final")

api_key = st.sidebar.text_input("Groq API Key:", type="password")

def generar_word_profesional(texto_ia, imagenes):
    doc = Document()
    
    # Configuración de márgenes para que no se encime nada
    section = doc.sections[0]
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)

    # Título Principal con mucho aire
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_tit = p_tit.add_run('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR')
    run_tit.bold = True
    run_tit.font.size = Pt(16)
    p_tit.paragraph_format.space_after = Pt(20)

    # Procesamiento de líneas para Negritas, Subrayado y Espaciado
    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea: continue
        
        p = doc.add_paragraph()
        
        # Identificar Títulos (DATOS, I., II., III., IV., CONCLUSIÓN)
        es_titulo = any(linea.startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"])
        
        if es_titulo:
            run = p.add_run(linea)
            run.bold = True
            run.underline = True
            run.font.size = Pt(12)
            p.paragraph_format.space_before = Pt(18) # Espacio antes del título para que no se encime
            p.paragraph_format.space_after = Pt(10)  # Espacio después del título
        else:
            p.add_run(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.space_after = Pt(6) # Espacio entre párrafos de contenido

    # ANEXO: 8 IMÁGENES (2 COLUMNAS X 4 FILAS)
    if imagenes:
        doc.add_page_break()
        p_an = doc.add_paragraph()
        r_an = p_an.add_run('ANEXO: IMÁGENES DEL ESTUDIO')
        r_an.bold = True
        r_an.underline = True
        p_an.paragraph_format.space_after = Pt(15)
        
        table = doc.add_table(rows=0, cols=2)
        for i in range(0, len(imagenes), 2):
            row_cells = table.add_row().cells
            for j in range(2):
                if i + j < len(imagenes):
                    img_data = imagenes[i+j]
                    cell_p = row_cells[j].paragraphs[0]
                    cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run_i = cell_p.add_run()
                    # Tamaño 2.4 pulgadas para que entren 4 filas (8 fotos) por hoja
                    run_i.add_picture(io.BytesIO(img_data), width=Inches(2.4))
                    cell_p.add_run(f"\nFig. {i + j + 1}")
    
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

if api_key:
    client = Groq(api_key=api_key)
    archivos = st.file_uploader("Subir estudio (PDF o Imágenes)", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_crudo = ""
        fotos = []
        for a in archivos:
            if a.type == "application/pdf":
                with fitz.open(stream=a.read(), filetype="pdf") as d:
                    for pag in d:
                        texto_crudo += pag.get_text() + "\n"
                        # Extraer fotos del PDF
                        for img in pag.get_images(full=True):
                            xref = img[0]
                            base_image = d.extract_image(xref)
                            fotos.append(base_image["image"])
            else:
                fotos.append(a.read())

        if st.button("Generar Informe Profesional"):
            with st.spinner("Analizando y formateando..."):
                # Mantenemos el Prompt que ya empezó a darte mejores resultados
                prompt = f"""
                Actúa como cardiólogo. Organiza este texto en un informe técnico: {texto_crudo}
                Sigue este esquema:
                DATOS DEL PACIENTE
                I. EVALUACIÓN ANATÓMICA Y CAVIDADES
                II. FUNCIÓN VENTRICULAR IZQUIERDA
                III. EVALUACIÓN HEMODINÁMICA
                IV. HALLAZGOS EXTRACARDÍACOS
                CONCLUSIÓN FINAL
                Sé asertivo y usa terminología médica. No menciones que faltan datos.
                """
                
                chat = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                respuesta = chat.choices[0].message.content
                st.markdown(respuesta)
                
                word_bin = generar_word_profesional(respuesta, fotos)
                st.download_button("📥 DESCARGAR INFORME WORD", word_bin, "Informe_Cardiologico_Final.docx")
