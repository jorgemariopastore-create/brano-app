
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI", layout="wide")
st.title("❤️ CardioReport AI - Versión Profesional")

api_key = st.sidebar.text_input("Groq API Key:", type="password")

def generar_docx_final(texto_ia, imagenes):
    doc = Document()
    
    # Márgenes equilibrados
    section = doc.sections[0]
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)

    # Título Principal
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_tit = p_tit.add_run('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR')
    run_tit.bold = True
    run_tit.font.size = Pt(14)
    p_tit.paragraph_format.space_after = Pt(15)

    # Procesamiento de líneas: Limpieza de Markdown y aplicación de formato médico
    for linea in texto_ia.split('\n'):
        linea = linea.replace('**', '').strip() # Limpia negritas de la IA para poner las nuestras
        if not linea: continue
        
        p = doc.add_paragraph()
        
        # Lógica de detección de títulos (Secciones de tu modelo)
        es_titulo = any(linea.upper().startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"])
        
        if es_titulo:
            run = p.add_run(linea.upper()) # Forzamos mayúsculas en títulos
            run.bold = True
            run.underline = True
            run.font.size = Pt(11)
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(8)
        else:
            p.add_run(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.space_after = Pt(4)

    # ANEXO: 8 IMÁGENES (Sin saltos de hoja excesivos)
    if imagenes:
        doc.add_page_break() # Solo un salto para el anexo
        p_an = doc.add_paragraph()
        r_an = p_an.add_run('ANEXO: IMÁGENES DEL ESTUDIO')
        r_an.bold = True
        r_an.underline = True
        p_an.paragraph_format.space_after = Pt(10)
        
        table = doc.add_table(rows=0, cols=2)
        for i in range(0, len(imagenes), 2):
            row_cells = table.add_row().cells
            for j in range(2):
                if i + j < len(imagenes):
                    img_data = imagenes[i+j]
                    cell_p = row_cells[j].paragraphs[0]
                    cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run_i = cell_p.add_run()
                    # Tamaño optimizado para 4 filas por hoja
                    run_i.add_picture(io.BytesIO(img_data), width=Inches(2.4))
                    cell_p.add_run(f"\nFig. {i + j + 1}")
    
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

if api_key:
    client = Groq(api_key=api_key)
    archivos = st.file_uploader("Subir archivos", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_ext = ""
        fotos = []
        for a in archivos:
            if a.type == "application/pdf":
                with fitz.open(stream=a.read(), filetype="pdf") as d:
                    for pag in d:
                        texto_ext += pag.get_text() + "\n"
                        for img in pag.get_images(full=True):
                            xref = img[0]
                            fotos.append(d.extract_image(xref)["image"])
            else:
                fotos.append(a.read())

        if st.button("Generar Informe"):
            with st.spinner("Formateando..."):
                prompt = f"Actúa como cardiólogo. Redacta el informe basado en este texto técnico: {texto_ext}. Sigue el esquema: DATOS DEL PACIENTE, I. EVALUACIÓN ANATÓMICA, II. FUNCIÓN VENTRICULAR, III. EVALUACIÓN HEMODINÁMICA, IV. HALLAZGOS EXTRACARDÍACOS y CONCLUSIÓN FINAL. Usa un tono médico asertivo."
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                texto_final = res.choices[0].message.content
                st.markdown(texto_final)
                
                wb = generar_docx_final(texto_final, fotos)
                st.download_button("📥 Descargar Word Corregido", wb, "Informe_Final_Pro.docx")
