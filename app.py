
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io

# Configuración de la App
st.set_page_config(page_title="CardioReport Pro - Dr. Pastore", layout="wide")

st.markdown("""
    <style>
    .report-container { background-color: #ffffff; padding: 30px; border-radius: 15px; border: 1px solid #e0e0e0; box-shadow: 2px 2px 15px rgba(0,0,0,0.05); }
    .stButton>button { background-color: #c62828; color: white; border-radius: 10px; font-weight: bold; width: 100%; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

st.title("❤️ Sistema de Informes Médicos")
st.subheader("Dr. Francisco Alberto Pastore")

# 1. Obtener API KEY de los Secrets de Streamlit
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    # 2. Subida del archivo
    archivo_pdf = st.file_uploader("Subir PDF del Ecocardiograma", type=["pdf"])

    if archivo_pdf:
        if st.button("GENERAR INFORME DEL PACIENTE"):
            with st.spinner("Procesando datos de Manuel Baleiron..."):
                try:
                    # 3. Leer TODAS las páginas del PDF
                    texto_completo = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_completo += pagina.get_text()

                    # 4. Configurar Groq con el modelo más potente
                    client = Groq(api_key=api_key)

                    # 5. EL PROMPT REFORZADO (Instrucciones exactas)
                    prompt_final = f"""
                    ERES UN ANALISTA MÉDICO EXPERTO. TU TRABAJO ES EXTRAER DATOS DEL SIGUIENTE TEXTO.
                    EL TEXTO TIENE TABLAS Y PÁRRAFOS. BUSCA EN AMBOS.

                    TEXTO DEL ESTUDIO:
                    {texto_completo}

                    INSTRUCCIONES DE BÚSQUEDA:
                    - DDVI: Busca 'DDVI' o 'LVIDd'. (En el texto verás 61).
                    - DSVI: Busca 'DSVI' o 'LVIDs'. (En el texto verás 46).
                    - AI: Busca 'DDAI' o 'LA'. (En el texto verás 42).
                    - SEPTUM: Busca 'DDSIV' o 'IVSd'. (En el texto verás 10).
                    - PARED: Busca 'DDPP' o 'LVPWd'. (En el texto verás 11).
                    - FEy: Busca el % o 'Fracción de eyección'. (En el texto verás 31%).

                    REGLAS MÉDICAS DEL DR. PASTORE:
                    1. Si FEy es menor a 35% y DDVI es mayor a 57mm: CONCLUSIÓN = "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica".
                    2. Menciona siempre la Motilidad (Ej: Hipocinesia global severa).

                    FORMATO DE SALIDA (ESTRICTO):
                    DATOS DEL PACIENTE: [Nombre, ID, Fecha]
                    I. EVALUACIÓN ANATÓMICA: [Menciona DDVI, DSVI, AI, Septum y Pared con sus mm]
                    II. FUNCIÓN VENTRICULAR: [Menciona FEy % y Motilidad]
                    III. EVALUACIÓN HEMODINÁMICA: [Resumen corto del Doppler y Vena Cava]
                    IV. CONCLUSIÓN: [Diagnóstico en Negrita]

                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    # Llamada a la IA
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "Eres un transcriptor médico preciso. Tu misión es encontrar los números perdidos en el texto y no inventar nada."},
                            {"role": "user", "content": prompt_final}
                        ],
                        temperature=0
                    )

                    # Mostrar resultado
                    st.markdown("---")
                    st.markdown(f'<div class="report-container">{response.choices[0].message.content}</div>', unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Hubo un error al leer el archivo: {e}")
else:
    st.error("⚠️ No se encontró la API Key en los Secrets de Streamlit.")
