
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io
from docx import Document
# ... (mantén tus importaciones de docx)

# Configuración y Estilos
st.set_page_config(page_title="CardioReport AI Pro", layout="wide")

# ... (mantén tu estilo CSS)

api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key:", type="password")

if api_key:
    client = Groq(api_key=api_key.strip())
    archivo = st.file_uploader("Cargar PDF de Manuel Baleiron u otro paciente", type=["pdf"])

    if archivo and st.button("GENERAR INFORME MÉDICO"):
        with st.spinner("EXTRAYENDO DATOS DE TABLAS TÉCNICAS..."):
            # 1. Extracción de texto
            texto_pdf = ""
            with fitz.open(stream=archivo.read(), filetype="pdf") as doc:
                for pagina in doc:
                    texto_pdf += pagina.get_text()

            # 2. EL PROMPT DEFINITIVO (Lógica Anti-Bloqueo)
            prompt_maestro = f"""
            ERES UN EXPERTO EN EXTRACCIÓN DE DATOS DE ECOCARDIOGRAMAS.
            TU OBJETIVO: Generar el informe del Dr. Pastore. No puedes decir "No disponible".
            
            TEXTO PARA ANALIZAR:
            {texto_pdf}

            PASO 1: LOCALIZA ESTOS VALORES EN LAS TABLAS (Mapeo de sinónimos):
            - DDVI = Busca 'DDVI', 'LVIDd', 'Diastolic' o 'Diast'. (Ej: 61 mm o 6.1 cm)
            - DSVI = Busca 'DSVI', 'LVIDs', 'Systolic' o 'Syst'. (Ej: 46 mm o 4.6 cm)
            - FEy = Busca 'FEy', 'EF', 'Fracción de eyección' o 'Simpson'. (Ej: 31%)
            - AI = Busca 'AI', 'Aurícula Izq', 'DDAI' o 'LA'. (Ej: 42 mm)
            - SEPTUM = Busca 'DDSIV', 'IVSd' o 'Tabique'. (Ej: 10 mm)

            PASO 2: APLICA LA LÓGICA DE DIAGNÓSTICO (OBLIGATORIO):
            - REGLA A: Si FEy es <= 35%, escribe "Deterioro SEVERO de la función sistólica".
            - REGLA B: Si DDVI es > 57mm, escribe "DILATACIÓN del ventrículo izquierdo".
            - REGLA C: Si hay ambas, usa "Miocardiopatía Dilatada".
            - REGLA D: Si FEy está entre 31-35% e hipocinesia global, es SEVERO.

            PASO 3: FORMATO DE SALIDA (ESTRICTO):
            DATOS DEL PACIENTE:
            Nombre: 
            ID: 
            Fecha: 

            I. EVALUACIÓN ANATÓMICA:
            - DDVI: [Valor] mm
            - DSVI: [Valor] mm
            - AI: [Valor] mm
            - Septum: [Valor] mm
            - Pared: [Valor] mm

            II. FUNCIÓN VENTRICULAR:
            - FEy: [Valor]%
            - Motilidad: [Describir si hay hipocinesia]

            III. EVALUACIÓN HEMODINÁMICA:
            [Resumen del Doppler y válvulas]

            IV. CONCLUSIÓN:
            [Tu diagnóstico basado en las REGLAS A, B y C en NEGRITA]

            Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
            """

            try:
                # Usamos el modelo más potente (70b) para que no ignore las tablas
                chat = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "No eres un chat, eres un transcriptor médico. Si ves números en una tabla, úsalos. Prohibido omitir datos."},
                        {"role": "user", "content": prompt_maestro}
                    ],
                    temperature=0
                )
                
                informe = chat.choices[0].message.content
                st.markdown(f"### Informe Generado\n\n{informe}")
                # ... (resto del código para descargar Word)
            except Exception as e:
                st.error(f"Error: {e}")
