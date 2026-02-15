
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Configuración de página
st.set_page_config(page_title="CardioReport AI v2.0", layout="wide")

# Estilo CSS para mejorar la interfaz
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #ff4b4b; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ CardioReport AI - Sistema Dr. Pastore")
st.subheader("Generación de Informes de Ecocardiograma con Criterio Médico")

# Manejo de API Key
api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Introducir Groq API Key:", type="password")

def crear_word_profesional(texto):
    """Genera un archivo Word con formato limpio y profesional."""
    doc = Document()
    
    # Encabezado
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = titulo.add_run("INFORME DE ECOCARDIOGRAMA DOPPLER COLOR")
    run.bold = True
    run.font.size = Pt(14)
    run.font.name = 'Arial'

    # Cuerpo del informe
    for linea in texto.split('\n'):
        linea = linea.replace('**', '').strip()
        if not linea:
            continue
            
        parrafo = doc.add_paragraph()
        run_linea = parrafo.add_run(linea)
        run_linea.font.name = 'Arial'
        run_linea.font.size = Pt(11)

        # Resaltar secciones principales
        if any(linea.startswith(x) for x in ["I.", "II.", "III.", "IV.", "DATOS", "CONCLUSIÓN"]):
            run_linea.bold = True
            if "CONCLUSIÓN" in linea:
                run_linea.font.size = Pt(12)
                
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

if api_key:
    client = Groq(api_key=api_key.strip())
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        archivos = st.file_uploader("Subir archivos del ecógrafo (PDF o Imágenes)", accept_multiple_files=True)
        
    if archivos and st.button("🚀 PROCESAR E INTERPRETAR INFORME"):
        with st.spinner("Analizando datos y aplicando criterio médico..."):
            texto_extraido = ""
            for archivo in archivos:
                if archivo.type == "application/pdf":
                    with fitz.open(stream=archivo.read(), filetype="pdf") as doc_pdf:
                        for pagina in doc_pdf:
                            texto_extraido += pagina.get_text()
                else:
                    texto_extraido += " [Contenido de imagen no procesable directamente por OCR básico] "

            # PROMPT MAESTRO CON CRITERIO DE GRAVEDAD
            prompt_medico = f"""
            Actúa como el Dr. Francisco Alberto Pastore, cardiólogo experto. 
            Tu tarea es transcribir y diagnosticar basándote en los datos crudos del ecógrafo:
            
            DATOS CRUDOS EXTRAÍDOS:
            {texto_extraido[:8000]}

            INSTRUCCIONES DE FORMATO Y LÓGICA MÉDICA:
            1. IDENTIFICACIÓN: Extrae Nombre, Edad, ID y Fecha.
            2. MEDIDAS: Convierte siempre cm a mm (ej: LVIDd 6.1cm -> DDVI 61mm). 
            3. CRITERIO DE GRAVEDAD (ESTRICTO):
               - Si FEy (EF) < 35%: Debes usar el término "Deterioro SEVERO".
               - Si FEy (EF) entre 35-44%: "Deterioro Moderado".
               - Si DDVI > 57mm: Debes diagnosticar "Dilatación" o "Miocardiopatía Dilatada".
               - Si hay hipocinesia global, menciónalo explícitamente.
            4. ESTILO: No uses introducciones como "Aquí tienes el informe". Empieza directo con el título.
            5. FIRMA: Siempre finaliza con "Dr. FRANCISCO ALBERTO PASTORE - MN 74144".

            ESTRUCTURA DEL INFORME:
            INFORME DE ECOCARDIOGRAMA DOPPLER COLOR
            DATOS DEL PACIENTE: (Nombre, Edad, ID, Fecha)
            I. EVALUACIÓN ANATÓMICA: (Detallar DDVI, DSVI, AI, Septum y Pared en mm).
            II. FUNCIÓN VENTRICULAR: (FEy exacta y descripción de motilidad).
            III. EVALUACIÓN HEMODINÁMICA: (Hallazgos Doppler, valvulares y vena cava).
            IV. CONCLUSIÓN: (Diagnóstico final en negrita basado en los hallazgos anteriores).
            """

            try:
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt_medico}],
                    temperature=0.1 # Baja temperatura para evitar inventos
                )
                
                informe_final = response.choices[0].message.content
                
                with col2:
                    st.success("Informe Generado con Éxito")
                    st.markdown(informe_final)
                    
                    word_file = crear_word_profesional(informe_final)
                    st.download_button(
                        label="📥 Descargar Informe en Word",
                        data=word_file,
                        file_name=f"Informe_Cardio.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            except Exception as e:
                st.error(f"Error en el procesamiento: {str(e)}")
else:
    st.warning("Por favor, introduce tu Groq API Key en la barra lateral para comenzar.")
