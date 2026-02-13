
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
from PIL import Image
import io
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Configuración de la interfaz
st.set_page_config(page_title="CardioReport AI", page_icon="❤️", layout="wide")
st.title("❤️ CardioReport AI")

api_key = st.sidebar.text_input("Groq API Key:", type="password")

def generar_docx(texto_informe, imagenes):
    doc = Document()
    
    # Encabezado centrado
    titulo_h = doc.add_heading('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR', 0)
    titulo_h.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Procesar líneas para aplicar Negrita y Subrayado a los títulos
    for linea in texto_informe.split('\n'):
        linea = linea.strip()
        if not linea:
            continue
        
        p = doc.add_paragraph()
        # Lógica mejorada para detectar títulos del modelo Gemini
        es_titulo = any(linea.startswith(pref) for pref in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"]) or linea.isupper()
        
        if es_titulo:
            run = p.add_run(linea)
            run.bold = True
            run.underline = True
            p.paragraph_format.space_before = Pt(14)
        else:
            p.add_run(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        p.paragraph_format.space_after = Pt(6)

    # Anexo de Imágenes (8 por hoja: 2 columnas x 4 filas)
    if imagenes:
        doc.add_page_break()
        p_anexo = doc.add_paragraph()
        r_anexo = p_anexo.add_run('ANEXO: IMÁGENES DEL ESTUDIO')
        r_anexo.bold = True
        r_anexo.underline = True
        
        table = doc.add_table(rows=0, cols=2)
        for i in range(0, len(imagenes), 2):
            row_cells = table.add_row().cells
            for j in range(2):
                if i + j < len(imagenes):
                    img_data = imagenes[i+j]
                    temp_img = io.BytesIO(img_data)
                    p_img = row_cells[j].paragraphs[0]
                    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run_i = p_img.add_run()
                    # Tamaño 2.6 para asegurar 4 filas por hoja
                    run_i.add_picture(temp_img, width=Inches(2.6)) 
                    p_img.add_run(f"\nFig. {i + j + 1}")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

if api_key:
    client = Groq(api_key=api_key)
    archivos = st.file_uploader("Subir archivos", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_extraido = ""
        imagenes_anexo = []
        for archivo in archivos:
            if archivo.type == "application/pdf":
                with fitz.open(stream=archivo.read(), filetype="pdf") as doc_pdf:
                    for pagina in doc_pdf:
                        texto_extraido += pagina.get_text()
                        pix = pagina.get_pixmap()
                        imagenes_anexo.append(pix.tobytes("png"))
            else:
                imagenes_anexo.append(archivo.read())

        if st.button("Generar Informe Estilo Gemini"):
            try:
                # PROMPT REFINADO BASADO EN TU ARCHIVO MODELO
                prompt_estilo_gemini = """
                Actúa como un cardiólogo de élite. Redacta un informe médico basado EXCLUSIVAMENTE en los datos técnicos.
                Tu redacción debe ser idéntica a un informe de laboratorio profesional: asertiva, descriptiva y estructurada.
                
                ESTRUCTURA OBLIGATORIA:
                DATOS DEL PACIENTE: Extrae Nombre, Edad, ID y Fecha.
                I. EVALUACIÓN ANATÓMICA Y CAVIDADES: Reporta diámetros de Raíz Aórtica, Aurícula Izquierda y Vena Cava.
                II. FUNCIÓN VENTRICULAR IZQUIERDA: Reporta VDF, VSF y la FRACCIÓN DE EYECCIÓN (FEy) con el método Simpson. Clasifica la disfunción (Leve, Moderada o Severa).
                III. EVALUACIÓN HEMODINÁMICA: Detalla Flujo Mitral (Onda E, A, relación E/A) y Doppler Tisular (e').
                IV. HALLAZGOS EXTRACARDÍACOS: Menciona hallazgos en Vena Porta o Arteria Renal.
                CONCLUSIÓN FINAL: Resume los hallazgos patológicos principales.

                IMPORTANTE: No uses frases como 'podría ser' o 'se sugiere'. Usa 'Se evidencia', 'Se observa' o 'Presenta'.
                """
                
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": prompt_estilo_gemini},
                        {"role": "user", "content": f"Datos extraídos: {texto_extraido}"}
                    ],
                    temperature=0.1
                )
                
                informe = completion.choices[0].message.content
                st.markdown(informe)
                
                doc_word = generar_docx(informe, imagenes_anexo)
                st.download_button("📥 Descargar Word (Estilo Gemini)", doc_word, "Informe_Profesional.docx")
            except Exception as e:
                st.error(f"Error: {e}")
