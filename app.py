
import streamlit as st
from google import genai
from PIL import Image
import fitz

# Configuración de la página
st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")

api_key = st.text_input("Introduce tu Gemini API Key:", type="password")

if api_key:
    try:
        # Nueva forma de conectar (Versión 2026)
        client = genai.Client(api_key=api_key)
        
        archivo = st.file_uploader("Sube tu estudio (Imagen o PDF)", type=["jpg", "png", "jpeg", "pdf"])

        if archivo is not None:
            if archivo.type == "application/pdf":
                doc = fitz.open(stream=archivo.read(), filetype="pdf")
                pagina = doc.load_page(0)
                pix = pagina.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            else:
                img = Image.open(archivo)

            # Cambiamos 'use_container_width' por 'width' como pidió tu consola
            st.image(img, caption="Estudio cargado", width='stretch')

            if st.button("Analizar con IA"):
                with st.spinner("Analizando informe..."):
                    try:
                        prompt = "Actúa como un cardiólogo experto. Analiza este informe y explica los resultados en lenguaje muy sencillo."
                        # Nueva forma de generar contenido
                        response = client.models.generate_content(
                            model="gemini-1.5-flash",
                            contents=[prompt, img]
                        )
                        st.success("Análisis completado:")
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error en el análisis: {e}")
    except Exception as e:
        st.error(f"Error de configuración: {e}")
else:
    st.info("Por favor, introduce tu API Key.")

