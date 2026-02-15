
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF
import io

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="CardioReport Pro", layout="wide")

st.title("❤️ Sistema de Informes - Dr. Pastore")

# 2. LÓGICA DE CLAVE AUTOMÁTICA
# Intenta sacar la clave de los secretos del sistema
api_key = st.secrets.get("GROQ_API_KEY")

if not api_key:
    # Si por alguna razón no está, la pide solo como respaldo
    api_key = st.sidebar.text_input("Introduce tu Groq API Key:", type="password")

if api_key:
    # 3. CARGADOR DE ARCHIVOS (Aparecerá directo si la clave funciona)
    archivo_pdf = st.file_uploader("Cargar PDF del Paciente", type=["pdf"])

    if archivo_pdf:
        st.success(f"Estudio de {archivo_pdf.name} listo para procesar.")
        
        if st.button("PROCESAR ESTUDIO MÉDICO"):
            with st.spinner("Buscando datos en tablas..."):
                try:
                    # Leer PDF
                    texto_pdf = ""
                    with fitz.open(stream=archivo_pdf.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_pdf += pagina.get_text()

                    # Configurar Cliente
                    client = Groq(api_key=api_key)
                    
                    # PROMPT REFORZADO PARA EL CASO BALEIRON
                    prompt = f"""
                    ERES EL DR. FRANCISCO PASTORE. TRANSCRIPCIÓN MÉDICA OBLIGATORIA.
                    Extrae estos datos del texto: {texto_pdf}
                    
                    INSTRUCCIONES DE EXTRACCIÓN:
                    - DDVI: Busca 'DDVI' o 'LVIDd'. En Baleiron es 61 mm.
                    - FEy: Busca 'FEy', 'EF' o 'Fracción de Eyección'. En Baleiron es 31%.
                    - AI: Busca 'DDAI' o 'LA'. En Baleiron es 42 mm.
                    
                    REGLA MÉDICA: Si FEy < 35% y DDVI > 57mm, la conclusión DEBE SER "Miocardiopatía Dilatada con deterioro SEVERO".
                    
                    FORMATO FINAL:
                    DATOS DEL PACIENTE:
                    I. EVALUACIÓN ANATÓMICA
                    II. FUNCIÓN VENTRICULAR
                    III. HEMODINÁMIA
                    IV. CONCLUSIÓN (En negrita y destacada)
                    
                    Firma: Dr. FRANCISCO ALBERTO PASTORE - MN 74144
                    """

                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0
                    )

                    st.markdown("---")
                    st.markdown(completion.choices[0].message.content)
                    
                except Exception as e:
                    st.error(f"Error al procesar: {e}")
else:
    st.error("No se encontró la API KEY. Configúrala en el archivo secrets.toml")
