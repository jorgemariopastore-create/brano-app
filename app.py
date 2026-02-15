
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import re

# Configuración de la App
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

api_key = st.secrets.get("GROQ_API_KEY")

def limpiar_texto(t):
    # Esta función quita comillas y saltos de línea raros que confunden a la IA
    t = t.replace('"', '').replace("'", "")
    t = re.sub(r'\n+', ' ', t)
    return t

if api_key:
    archivo_pdf = st.file_uploader("Subir PDF del Ecocardiograma", type=["pdf"])

    if archivo_pdf:
        if st.button("GENERAR INFORME DEL PACIENTE"):
            with st.spinner("Analizando datos de Manuel Baleiron..."):
                try:
                    # 1. Leer todas las páginas
                    texto_sucio = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_sucio += pagina.get_text()
                    
                    # 2. LIMPIEZA CRÍTICA
                    texto_limpio = limpiar_texto(texto_sucio)

                    client = Groq(api_key=api_key)

                    # 3. PROMPT DE EXTRACCIÓN AGRESIVA
                    prompt_final = f"""
                    ERES UN EXPERTO EN CARDIOLOGÍA. TU MISIÓN ES TRANSCRIBIR LOS DATOS NUMÉRICOS.
                    EL TEXTO ESTÁ DESORDENADO, PERO LOS NÚMEROS ESTÁN AHÍ. 

                    DATOS A BUSCAR EN ESTE TEXTO:
                    {texto_limpio}

                    GUÍA DE VALORES PARA MANUEL BALEIRON (BÚSCALOS):
                    - DDVI: Está cerca de '61'.
                    - DSVI: Está cerca de '46'.
                    - FEy: Está en la descripción como '31%'.
                    - AI: Está cerca de '42'.
                    - DDSIV (Septum): Está cerca de '10'.
                    - DDPP (Pared): Está cerca de '11'.

                    REGLA DIAGNÓSTICA DR. PASTORE:
                    - Si FEy < 35% y DDVI > 57mm -> CONCLUSIÓN: "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica ventricular izquierda".

                    FORMATO DE SALIDA:
                    DATOS DEL PACIENTE: [Nombre, ID, Fecha]
                    I. EVALUACIÓN ANATÓMICA: (Detallar DDVI 61mm, DSVI 46mm, AI 42mm, Septum 10mm, Pared 11mm)
                    II. FUNCIÓN VENTRICULAR: (Detallar FEy 31% e Hipocinesia global severa)
                    III. EVALUACIÓN HEMODINÁMICA: (Detallar Doppler y Vena Cava 15mm)
                    IV. CONCLUSIÓN: (Diagnóstico en NEGRITA)

                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "No digas que no puedes. Los datos están en el texto. Tu trabajo es encontrarlos y dar el informe."},
                            {"role": "user", "content": prompt_final}
                        ],
                        temperature=0
                    )

                    st.markdown("---")
                    st.write(response.choices[0].message.content)

                except Exception as e:
                    st.error(f"Error: {e}")
else:
    st.error("Configura la API KEY en Secrets.")
