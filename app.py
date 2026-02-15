
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="CardioReport Pro", layout="wide")
st.title("❤️ Sistema de Informes - Dr. Pastore")

# 1. Recuperar clave de Secrets
api_key = st.secrets.get("GROQ_API_KEY")

if api_key:
    archivo_pdf = st.file_uploader("Cargar PDF del Paciente", type=["pdf"])

    if archivo_pdf:
        if st.button("PROCESAR ESTUDIO MÉDICO"):
            with st.spinner("Analizando tablas técnicas..."):
                try:
                    # --- AQUÍ SE CREA LA VARIABLE texto_pdf ---
                    texto_pdf = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_pdf += pagina.get_text()

                    # --- AHORA QUE texto_pdf EXISTE, DEFINIMOS EL PROMPT ---
                    prompt_pastore = f"""
                    ERES EL DR. FRANCISCO ALBERTO PASTORE. TU TAREA ES TRANSCRIBIR UN INFORME MÉDICO 
                    BASADO EN EL TEXTO DEL ECOCARDIOGRAMA ADJUNTO: {texto_pdf}

                    INSTRUCCIONES DE EXTRACCIÓN (BUSCA EN LAS TABLAS):
                    - DDVI (LVIDd): mm.
                    - DSVI (LVIDs): mm.
                    - AI (DDAI/LA): mm.
                    - Septum (DDSIV): mm.
                    - Pared Posterior (DDPP): mm.
                    - FEy (EF): % (Búscalo también en el texto descriptivo).

                    REGLAS DE DIAGNÓSTICO:
                    - Si FEy < 35% y DDVI > 57mm: "Miocardiopatía Dilatada con deterioro SEVERO de la función sistólica".
                    - Si DDVI > 57mm pero FEy normal: "Dilatación del ventrículo izquierdo".

                    FORMATO DE SALIDA:
                    DATOS DEL PACIENTE:
                    I. EVALUACIÓN ANATÓMICA
                    II. FUNCIÓN VENTRICULAR (Incluir Motilidad y FEy)
                    III. EVALUACIÓN HEMODINÁMICA
                    IV. CONCLUSIÓN (En Negrita)
                    
                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    # 2. Conexión con Groq
                    client = Groq(api_key=api_key)
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt_pastore}],
                        temperature=0
                    )

                    st.markdown("---")
                    st.markdown(completion.choices[0].message.content)
                    
                except Exception as e:
                    st.error(f"Error técnico: {e}")
else:
    st.error("Falta la GROQ_API_KEY en los Secrets de Streamlit.")
