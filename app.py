
import streamlit as st
import google.generativeai as genai
from PIL import Image
import fitz

# Configuración de la página
st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")
st.subheader("Análisis inteligente de informes cardiológicos")

# --- CONFIGURACIÓN DE IA ---
os_api_key = st.text_input("Introduce tu Gemini API Key:", type="password")

if os_api_key:
    try:
        # 1. Forzamos la configuración a la versión estable 'v1'
        genai.configure(api_key=os_api_key, transport='rest')
        
        # 2. Usamos el modelo con la ruta completa y específica
        model = genai.GenerativeModel(model_name='models/gemini-1.5-flash')

        # --- CARGADOR DE ARCHIVOS ---
        archivo = st.file_uploader("Sube tu estudio (JPG, PNG o PDF)", type=["jpg", "png", "jpeg", "pdf"])

        if archivo is not None:
            if archivo.type == "application/pdf":
                doc = fitz.open(stream=archivo.read(), filetype="pdf")
                pagina = doc.load_page(0)
                pix = pagina.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            else:
                img = Image.open(archivo)

            st.image(img, caption="Documento cargado", use_container_width=True)

            if st.button("Analizar con IA"):
                with st.spinner("La IA está leyendo tu informe..."):
                    try:
                        # 3. Prompt directo
                        prompt = "Actúa como un asistente médico experto. Analiza este informe cardiológico y explica los puntos clave."
                        # Generamos contenido forzando la comunicación estable
                        response = model.generate_content([prompt, img])
                        
                        st.success("Análisis completado:")
                        st.markdown(response.text)
                    except Exception as e:
                        # Si falla, te mostrará el mensaje exacto para saber qué pasa
                        st.error(f"Error en el análisis: {e}")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
else:
    st.warning("Por favor, introduce tu API Key para comenzar.")
