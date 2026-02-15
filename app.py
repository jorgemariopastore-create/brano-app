
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("❤️ Sistema de Informes - Dr. Pastore")

api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo_pdf = st.file_uploader("Cargar PDF del Paciente", type=["pdf"])

    if archivo_pdf:
        if st.button("PROCESAR ESTUDIO MÉDICO"):
            with st.spinner("Extrayendo datos de las tablas del PDF..."):
                try:
                    # 1. Extracción de texto crudo del PDF
                    texto_pdf = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_pdf += pagina.get_text()

                    # 2. Configuración del cliente Groq
                    client = Groq(api_key=api_key)

                    # 3. PROMPT "MÁQUINA DE EXTRACCIÓN" (Sin excusas)
                    prompt_final = f"""
                    ACTÚA COMO UN TRANSCRIPTOR MÉDICO. NO DES EXPLICACIONES.
                    TU MISIÓN: Extraer los números de las tablas de este texto:
                    --- INICIO DEL TEXTO ---
                    {texto_pdf}
                    --- FIN DEL TEXTO ---

                    DATOS OBLIGATORIOS A BUSCAR:
                    - DDVI: (LVIDd) en mm.
                    - DSVI: (LVIDs) en mm.
                    - AI: (DDAI) en mm.
                    - Septum: (DDSIV) en mm.
                    - Pared Posterior: (DDPP) en mm.
                    - FEy: (%)

                    CRITERIOS MÉDICOS (DR. PASTORE):
                    1. Si FEy < 35% y DDVI > 57mm -> "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica".
                    2. Si Septum o Pared > 11mm -> "Hipertrofia".

                    FORMATO DE SALIDA (ESTRICTO):
                    DATOS DEL PACIENTE: [Nombre, ID, Fecha]
                    I. EVALUACIÓN ANATÓMICA: [Mencionar todos los mm extraídos]
                    II. FUNCIÓN VENTRICULAR: [Mencionar FEy % y Motilidad si aparece]
                    III. EVALUACIÓN HEMODINÁMICA: [Resumen corto]
                    IV. CONCLUSIÓN: [Diagnóstico en Negrita según criterios]

                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": "Eres un experto en lectura de ecocardiogramas. Tu prioridad es encontrar los valores numéricos dentro de las tablas."},
                            {"role": "user", "content": prompt_final}
                        ],
                        temperature=0
                    )

                    st.markdown("---")
                    st.markdown(completion.choices[0].message.content)
                    
                except Exception as e:
                    st.error(f"Error técnico: {e}")
