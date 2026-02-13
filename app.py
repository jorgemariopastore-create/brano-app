
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(page_title="CardioReport AI", page_icon="❤️", layout="wide")
st.title("❤️ CardioReport AI")

api_key = st.sidebar.text_input("Groq API Key:", type="password")

def generar_docx(texto_informe, imagenes):
    doc = Document()
    
    # Título principal centrado
    titulo_doc = doc.add_heading('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR', 0)
    titulo_doc.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Procesamiento de texto con NEGRILLA Y SUBRAYADO real para títulos
    for linea in texto_informe.split('\n'):
        linea = linea.strip()
        if not linea: continue
        
        p = doc.add_paragraph()
        # Detecta secciones basadas en tu modelo Gemini
        es_seccion = any(linea.startswith(s) for s in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"])
        
        if es_seccion:
            run = p.add_run(linea)
            run.bold = True
            run.underline = True
            p.paragraph_format.space_before = Pt(12)
        else:
            p.add_run(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(4)

    # ANEXO: 8 IMÁGENES POR HOJA (2 COLUMNAS X 4 FILAS)
    if imagenes:
        doc.add_page_break()
        p_anexo = doc.add_paragraph()
        r_anexo = p_anexo.add_run('ANEXO: IMÁGENES DEL ESTUDIO')
        r_anexo.bold = True
        r_anexo.underline = True
        
        # Tabla de 2 columnas
        table = doc.add_table(rows=0, cols=2)
        for i in range(0, len(imagenes), 2):
            row_cells = table.add_row().cells
            for j in range(2):
                if i + j < len(imagenes):
                    img_data = imagenes[i+j]
                    temp_img = io.BytesIO(img_data)
                    cell_p = row_cells[j].paragraphs[0]
                    cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run_img = cell_p.add_run()
                    # Tamaño 2.4 para asegurar 4 filas por página
                    run_img.add_picture(temp_img, width=Inches(2.4))
                    cell_p.add_run(f"\nFig. {i + j + 1}")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

if api_key:
    client = Groq(api_key=api_key)
    archivos = st.file_uploader("Subir estudio", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_para_ia = ""
        imagenes_lista = []
        for arch in archivos:
            if arch.type == "application/pdf":
                with fitz.open(stream=arch.read(), filetype="pdf") as d:
                    for pag in d:
                        texto_para_ia += pag.get_text()
                        pix = pag.get_pixmap()
                        imagenes_lista.append(pix.tobytes("png"))
            else:
                img_bytes = arch.read()
                imagenes_lista.append(img_bytes)

        if st.button("Generar Informe Profesional"):
            with st.spinner("Analizando..."):
                # PROMPT REFORZADO PARA REPLICAR GEMINI
                instrucciones = f"""
                Eres un cardiólogo experto. Tu tarea es organizar los datos técnicos en un informe final.
                IMPORTANTE: Usa un lenguaje asertivo. No digas 'no se proporcionan datos'. 
                Si los datos faltan, omite la sección o descríbela de forma técnica profesional.
                
                Sigue este formato exacto de tu modelo previo:
                DATOS DEL PACIENTE: Nombre, Edad, ID, Fecha.
                I. EVALUACIÓN ANATÓMICA Y CAVIDADES: Reporta diámetros de Raíz Aórtica, Aurícula Izquierda y Vena Cava.
                II. FUNCIÓN VENTRICULAR IZQUIERDA: Reporta FEy (%) por método Simpson y volúmenes VDF/VSF.
                III. EVALUACIÓN HEMODINÁMICA: Detalla Onda E, A y relación E/A.
                IV. HALLAZGOS EXTRACARDÍACOS: Vena Porta y Arteria Renal.
                CONCLUSIÓN FINAL: Resumen de hallazgos patológicos.
                """
                
                chat = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": instrucciones},
                              {"role": "user", "content": f"Datos del estudio: {texto_para_ia}"}],
                    temperature=0.1
                )
                
                respuesta = chat.choices[0].message.content
                st.markdown(respuesta)
                
                doc_bin = generar_docx(respuesta, imagenes_lista)
                st.download_button("📥 Descargar Word Profesional", doc_bin, "Informe_Cardio.docx")
