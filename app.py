
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF

st.set_page_config(page_title="CardioReport Pro", layout="wide")

# Clave automática desde Secrets
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo_pdf = st.file_uploader("Cargar PDF del Paciente", type=["pdf"])

    if archivo_pdf:
        if st.button("GENERAR INFORME"):
            with st.spinner("Extrayendo datos de tablas..."):
                try:
                    # 1. Extraer el texto del PDF
                    texto_pdf = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_pdf += pagina.get_text()

                    # 2. Configurar el cliente
                    client = Groq(api_key=api_key)

                    # 3. PROMPT DE EXTRACCIÓN FORZADA
                    # Aquí le damos ejemplos de cómo vienen los datos en el PDF
                    prompt_instrucciones = f"""
                    ERES UN ANALISTA TÉCNICO DE ECOCARDIOGRAMAS. 
                    TU OBJETIVO ES EXTRAER LOS VALORES NUMÉRICOS DEL SIGUIENTE TEXTO CRUDO.

                    TEXTO A ANALIZAR:
                    {texto_pdf}

                    INSTRUCCIONES CRÍTICAS:
                    - Busca "DDVI" y toma el número que sigue (ej. 61).
                    - Busca "DSVI" y toma el número que sigue (ej. 46).
                    - Busca "FEy" o "Fracción de eyección" (ej. 31%).
                    - Busca "DDSIV" (Septum) y "DDPP" (Pared).
                    - Busca "DDAI" (Aurícula).

                    APLICA EL CRITERIO DEL DR. PASTORE:
                    - Si FEy < 35% y DDVI > 57mm -> CONCLUSIÓN: "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica".

                    FORMATO DE SALIDA:
                    DATOS DEL PACIENTE:
                    Nombre: MANUEL BALEIRON
                    ID: 12563493
                    Fecha: 27/01/2026

                    I. EVALUACIÓN ANATÓMICA:
                    - DDVI: [valor] mm
                    - DSVI: [valor] mm
                    - AI: [valor] mm
                    - Septum: [valor] mm
                    - Pared Posterior: [valor] mm

                    II. FUNCIÓN VENTRICULAR:
                    - FEy: [valor]%
                    - Motilidad: [hallazgos]

                    III. EVALUACIÓN HEMODINÁMICA:
                    [Hallazgos de Doppler/Vena Cava]

                    IV. CONCLUSIÓN:
                    [Diagnóstico en negrita]

                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    # 4. Llamada a la IA (Usamos temperature 0 para que no invente nada)
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "No eres un asistente, eres un extractor de datos médicos preciso. No respondas con disculpas, responde solo con el informe completo."},
                            {"role": "user", "content": prompt_instrucciones}
                        ],
                        temperature=0
                    )

                    st.markdown("---")
                    st.markdown(response.choices[0].message.content)

                except Exception as e:
                    st.error(f"Error: {e}")
