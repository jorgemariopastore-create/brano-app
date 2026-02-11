
import streamlit as st
import google.generativeai as genai
from PIL import Image
import fitz

st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")

api_key = st.text_input("Introduce tu Gemini API Key:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        # ESTA LÍNEA ES LA CLAVE: No usa v1beta
        model = genai.GenerativeModel('gemini-1.5-flash')

        archivo = st.file_uploader("Sube tu estudio", type=["jpg", "png", "jpeg", "pdf"])

        if archivo is not None:
            if archivo.type == "application/pdf":
                doc = fitz.open(stream=archivo.read(), filetype="pdf")
                pagina = doc.load_page(0)
                pix = pagina.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            else:
                img = Image.open(archivo)

            st.image(img, caption="Estudio cargado", use_container_width=True)

            if st.button("Analizar con IA"):
                with st.spinner("Analizando informe..."):
                    try:
                        response = model.generate_content(["Actúa como cardiólogo y explica este informe:", img])
                        st.success("Análisis:")
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error en el análisis: {e}")
    except Exception as e:
        st.error(f"Error: {e}")
