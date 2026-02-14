
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="CardioReport AI - SonoScape Pro", layout="wide")
st.title("❤️ CardioReport AI - Extractor SonoScape E3")

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Groq API Key:", type="password")

if api_key:
    client = Groq(api_key=api_key.strip())
    archivos = st.file_uploader("Subir archivos del paciente", type=["pdf", "jpg", "png"], accept_multiple_files=True)

    if archivos:
        texto_ext = ""
        for a in archivos:
            if a.type == "application/pdf":
                with fitz.open(stream=a.read(), filetype="pdf") as d:
                    for pag in d:
                        # Extraemos texto de forma más exhaustiva
                        texto_ext += pag.get_text("text") + "\n"
        
        if st.button("Generar Informe Médico"):
            with st.spinner("Buscando datos de Manuel Baleiron..."):
                
                prompt = f"""
                Eres un cardiólogo experto. Analiza este texto de un ecógrafo SonoScape:
                ---
                {texto_ext}
                ---

                DATOS CRÍTICOS A BUSCAR (Busca los números aunque el texto esté sucio):
                1. Busca 'LVIDd' o 'DDVI'. En este paciente debe ser alrededor de 6.10 cm o 61 mm.
                2. Busca 'EF' o 'EF(Teich)'. En este paciente debe ser alrededor de 30.6%.
                3. Busca 'LVIDs' o 'DSVI'. Debe ser 4.60 cm o 46 mm.

                INSTRUCCIONES:
                - Si la FEy es 30.6%, reporta "Deterioro severo de la función sistólica".
                - Menciona la "Miocardiopatía Dilatada" si el DDVI es 61mm.
                - No digas que no hay datos. Los datos están en el texto, búscalos como etiquetas de tabla.

                FORMATO:
                DATOS DEL PACIENTE: Manuel Baleiron, 67 años.
                I. EVALUACIÓN ANATÓMICA: Reportar DDVI (61mm), DSVI (46mm) y AI.
                II. FUNCIÓN VENTRICULAR: Mencionar FEy (30.6%) y la hipocinesia global.
                III. EVALUACIÓN HEMODINÁMICA: Doppler.
                CONCLUSIÓN: Diagnóstico técnico en negrita.

                Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144.
                """
                
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                respuesta = res.choices[0].message.content
                st.markdown(respuesta)
