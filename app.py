
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
from docx import Document
from docx.shared import Inches

# Configuración de página
st.set_page_config(page_title="CardioReport AI", page_icon="❤️", layout="wide")
st.title("❤️ CardioReport AI - Generador de Informes Profesionales")

# 1. Configuración de API y Estilos
api_key = st.sidebar.text_input("Groq API Key:", type="password")

def generar_docx(texto_informe, imagenes):
    doc = Document()
    doc.add_heading('INFORME DE ECOCARDIOGRAMA DOPPLER COLOR', 0)
    
    # Contenido del informe
    doc.add_paragraph(texto_informe)
    
    # Anexo de Imágenes (2 por fila como se solicitó)
    if imagenes:
        doc.add_page_break()
        doc.add_heading('ANEXO: IMÁGENES DEL ESTUDIO', 1)
        table = doc.add_table(rows=0, cols=2)
        
        for i in range(0, len(imagenes), 2):
            row_cells = table.add_row().cells
            for j in range(2):
                if i + j < len(imagenes):
                    img_data = imagenes[i+j]
                    # Guardar temporalmente para insertar en docx
                    temp_img = io.BytesIO(img_data)
                    paragraph = row_cells[j].paragraphs[0]
                    run = paragraph.add_run()
                    run.add_picture(temp_img, width=Inches(3.0))
                    paragraph.add_run(f"\nFig. {i + j + 1}")
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

if api_key:
    client = Groq(api_key=api_key)
    
    # 2. Carga de Archivos (Múltiples para el anexo)
    archivos = st.file_uploader("Sube las imágenes o el PDF del estudio", 
                               type=["pdf", "jpg", "jpeg", "png"], 
                               accept_multiple_files=True)

    if archivos:
        texto_extraido = ""
        imagenes_anexo = []
        
        for archivo in archivos:
            if archivo.type == "application/pdf":
                with fitz.open(stream=archivo.read(), filetype="pdf") as doc:
                    for pagina in doc:
                        texto_extraido += pagina.get_text()
                        # Extraer imágenes del PDF para el anexo si existen
                        pix = pagina.get_pixmap()
                        imagenes_anexo.append(pix.tobytes("png"))
            else:
                img_data = archivo.read()
                imagenes_anexo.append(img_data)
                # Para fotos, el texto se extrae mediante la instrucción a la IA
                # asumiendo que el modelo 3.3-70b analizará el contexto.

        if st.button("Generar Informe Médico Profesional"):
            with st.spinner("Procesando datos y formateando informe..."):
                try:
                    # Instrucción detallada para replicar el modelo Gemini
                    prompt_sistema = """Actúa como un cardiólogo experto. Tu tarea es redactar un informe médico basado EXCLUSIVAMENTE en los datos proporcionados. 
                    Sigue estrictamente esta estructura:
                    I. EVALUACIÓN ANATÓMICA Y CAVIDADES: Detalles de Raíz Aórtica, Aurículas y Vena Cava.
                    II. FUNCIÓN VENTRICULAR IZQUIERDA: Método de Simpson, FEy, y volúmenes.
                    III. EVALUACIÓN HEMODINÁMICA: Doppler mitral, tisular y presiones de llenado.
                    IV. HALLAZGOS EXTRACARDÍACOS: Datos vasculares o renales.
                    CONCLUSIÓN FINAL: Resumen de los hallazgos más importantes.
                    Usa un tono profesional pero claro para el paciente."""

                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": prompt_sistema},
                            {"role": "user", "content": f"Datos del informe: {texto_extraido if texto_extraido else 'Analiza la información clínica contenida en este estudio.'}"}
                        ],
                        temperature=0.1
                    )
                    
                    informe_final = completion.choices[0].message.content
                    st.session_state['informe'] = informe_final
                    
                    st.success("Informe Generado con Éxito")
                    st.markdown(informe_final)
                    
                    # 3. Generación y Descarga de Word
                    word_bin = generar_docx(informe_final, imagenes_anexo)
                    st.download_button(
                        label="📄 Descargar Informe en Word (.docx)",
                        data=word_bin,
                        file_name="Informe_Cardiologico_Final.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                    
                except Exception as e:
                    st.error(f"Error al generar el informe: {e}")
else:
    st.info("Ingresa tu Groq API Key para comenzar.")
