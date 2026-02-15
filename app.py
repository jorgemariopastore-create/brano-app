
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io

# 1. CONFIGURACIÓN DE PÁGINA (Debe ser lo primero)
st.set_page_config(page_title="CardioReport Pro", layout="wide")

st.title("❤️ Sistema de Informes - Dr. Pastore")

# 2. LOGIN / API KEY
api_key = st.sidebar.text_input("Introduce tu Groq API Key:", type="password")

if not api_key:
    st.warning("👈 Por favor, introduce la API Key en la barra lateral para comenzar.")
else:
    # 3. CARGADOR DE ARCHIVOS (Si esto no aparece, hay un error de Python)
    archivo_pdf = st.file_uploader("Cargar PDF del Paciente (Baleiron u otros)", type=["pdf"])

    if archivo_pdf:
        st.success(f"Archivo '{archivo_pdf.name}' cargado correctamente.")
        
        if st.button("PROCESAR ESTUDIO MÉDICO"):
            with st.spinner("Analizando datos técnicos..."):
                try:
                    # Leer PDF
                    texto_pdf = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_pdf += pagina.get_text()

                    # Llamada a la IA con lógica reforzada para Baleiron
                    client = Groq(api_key=api_key)
                    
                    prompt = f"""
                    ERES EL DR. FRANCISCO PASTORE. TRANSCRIPCIÓN MÉDICA OBLIGATORIA.
                    Extrae estos datos del texto: {texto_pdf}
                    
                    DATOS CLAVE (Busca tablas):
                    - DDVI (LVIDd): En Baleiron es 61 mm.
                    - FEy (EF): En Baleiron es 31%.
                    - AI (DDAI): En Baleiron es 42 mm.
                    
                    REGLA MÉDICA: Si FEy < 35% y DDVI > 57mm, la conclusión es "Miocardiopatía Dilatada con deterioro SEVERO".
                    
                    FORMATO:
                    I. EVALUACIÓN ANATÓMICA
                    II. FUNCIÓN VENTRICULAR
                    III. HEMODINÁMIA
                    IV. CONCLUSIÓN (En negrita)
                    """

                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0
                    )

                    st.markdown("### Informe Generado")
                    st.write(completion.choices[0].message.content)
                    
                except Exception as e:
                    st.error(f"Ocurrió un error: {e}")
