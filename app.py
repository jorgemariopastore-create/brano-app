
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
st.subheader("Generador de Informes Profesionales Estilo Gemini")

# Barra lateral para la clave
api_key = st.sidebar.text_input("Groq API Key:", type="password")

def agregar_seccion_titulo(doc, titulo):
    """Agrega un título en negrita, subrayado y evita que quede solo al final de la hoja"""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.keep_with_next = True  # Evita que el título quede solo al pie
    run = p.add_run(titulo)
    run.bold = True
    run.underline = True
    run.font.size = Pt(12)

def generar_docx(texto_informe, imagenes):
    doc = Document()
    
    # Título Principal centrado
    titulo_principal = doc.add_heading('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR', 0)
    titulo_principal.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Procesar el texto por secciones para aplicar formato
    lineas = texto_informe.split('\n')
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
            
        # Detectar si es un título (I., II., III., IV. o Mayúsculas)
        if any(linea.startswith(prefijo) for prefijo in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"]):
            agregar_seccion_titulo(doc, linea)
        else:
            p = doc.add_paragraph(linea)
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY # Texto Justificado

    # Anexo de Imágenes (Grilla de 2 por fila)
    if imagenes:
        doc.add_page_break()
        agregar_seccion_titulo(doc, 'ANEXO: IMÁGENES DEL ESTUDIO')
        table = doc.add_table(rows=0, cols=2)
        
        for i in range(0, len(imagenes), 2):
            row_cells = table.add_row().cells
            for j in range(2):
                if i + j < len(imagenes):
                    img_data = imagenes[i+j]
                    temp_img = io.BytesIO(img_data)
                    paragraph = row_cells[j].paragraphs[0]
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run = paragraph.add_run()
                    run.add_picture(temp_img, width=Inches(3.5)) # Tamaño aumentado
                    paragraph.add_run(f"\nFig. {i + j + 1}")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

if api_key:
    client = Groq(api_key=api_key)
    archivos = st.file_uploader("Sube las imágenes o el PDF del estudio", 
                               type=["pdf", "jpg", "jpeg", "png"], 
                               accept_multiple_files=True)

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
                img_data = archivo.read()
                imagenes_anexo.append(img_data)

        if st.button("Generar Informe y Word"):
            with st.spinner("Creando informe profesional..."):
                try:
                    prompt_instrucciones = """
                    Eres un cardiólogo experto redactando un informe técnico final asertivo. 
                    NO cuestiones el estudio ni sugieras dudas. 
                    Sigue estrictamente este formato de secciones:
                    DATOS DEL PACIENTE: (Nombre, Edad, ID, Fecha)
                    I. EVALUACIÓN ANATÓMICA Y CAVIDADES
                    II. FUNCIÓN VENTRICULAR IZQUIERDA
                    III. EVALUACIÓN HEMODINÁMICA
                    IV. HALLAZGOS EXTRACARDÍACOS
                    CONCLUSIÓN FINAL
                    """

                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": prompt_instrucciones},
                            {"role": "user", "content": f"Organiza estos datos en el informe: {texto_extraido}"}
                        ],
                        temperature=0.1
                    )
                    
                    resultado_ia = completion.choices[0].message.content
                    st.markdown(resultado_ia)
                    
                    word_data = generar_docx(resultado_ia, imagenes_anexo)
                    
                    st.download_button(
                        label="📥 Descargar Informe en Word (.docx)",
                        data=word_data,
                        file_name="Informe_Cardiologico.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.error(f"Error: {e}")
else:
    st.info("Introduce tu Groq API Key en la izquierda para comenzar.")
