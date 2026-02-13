
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

def generar_word_perfecto(texto_ia, imagenes):
    doc = Document()
    
    # Configurar márgenes estrechos para que entren las 8 fotos
    section = doc.sections[0]
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)
    section.top_margin = Inches(0.5)
    section.bottom_margin = Inches(0.5)

    # Título Principal
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_tit = p_tit.add_run('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR')
    run_tit.bold = True
    run_tit.font.size = Pt(14)

    # Cuerpo del Informe: Negrita y Subrayado forzado
    for linea in texto_ia.split('\n'):
        linea = linea.strip()
        if not linea: continue
        
        p = doc.add_paragraph()
        # Forzar formato en títulos de sección
        if any(linea.startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"]):
            run = p.add_run(linea)
            run.bold = True
            run.underline = True
            p.paragraph_format.space_before = Pt(8)
        else:
            p.add_run(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(2)

    # ANEXO: 8 IMÁGENES (2 COLUMNAS X 4 FILAS)
    if imagenes:
        doc.add_page_break()
        p_an = doc.add_paragraph()
        r_an = p_an.add_run('ANEXO: IMÁGENES DEL ESTUDIO')
        r_an.bold = True
        r_an.underline = True
        
        table = doc.add_table(rows=0, cols=2)
        # Ajustar ancho de tabla
        table.autofit = False 
        
        for i in range(0, len(imagenes), 2):
            row_cells = table.add_row().cells
            for j in range(2):
                if i + j < len(imagenes):
                    img_data = imagenes[i+j]
                    cell_p = row_cells[j].paragraphs[0]
                    cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run_i = cell_p.add_run()
                    # Tamaño 2.35 para asegurar 4 filas por página
                    run_i.add_picture(io.BytesIO(img_data), width=Inches(2.35))
                    cell_p.add_run(f"\nFig. {i + j + 1}")
    
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()

if api_key:
    client = Groq(api_key=api_key)
    archivos = st.file_uploader("Subir estudio", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_crudo = ""
        fotos = []
        for a in archivos:
            if a.type == "application/pdf":
                with fitz.open(stream=a.read(), filetype="pdf") as d:
                    for pag in d:
                        texto_crudo += pag.get_text() + "\n"
                        # Extraer imágenes del PDF
                        for img_index, img in enumerate(pag.get_images(full=True)):
                            xref = img[0]
                            base_image = d.extract_image(xref)
                            fotos.append(base_image["image"])
            else:
                fotos.append(a.read())

        if st.button("Generar Informe Profesional"):
            with st.spinner("Analizando datos médicos..."):
                # PROMPT PARA MODELOS SIN VISIÓN: Obligamos a usar datos específicos
                prompt = f"""
                Eres un cardiólogo experto. Redacta el informe basado en estos datos extraídos: {texto_crudo}
                ESTRUCTURA OBLIGATORIA (Sigue el estilo de Manuel Baleiron):
                DATOS DEL PACIENTE: Nombre, Edad, ID.
                I. EVALUACIÓN ANATÓMICA Y CAVIDADES: Raíz Aórtica, Aurícula Izquierda, Vena Cava.
                II. FUNCIÓN VENTRICULAR IZQUIERDA: FEy (%) Simpson, Volúmenes VDF/VSF.
                III. EVALUACIÓN HEMODINÁMICA: Onda E, A, relación E/A y Doppler tisular e'.
                IV. HALLAZGOS EXTRACARDÍACOS: Vena Porta y Renal.
                CONCLUSIÓN FINAL: Resumen asertivo.
                """
                
                chat = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                respuesta = chat.choices[0].message.content
                st.markdown(respuesta)
                
                word_bin = generar_word_perfecto(respuesta, fotos)
                st.download_button("📥 DESCARGAR INFORME WORD", word_bin, "Informe_Cardio.docx")
