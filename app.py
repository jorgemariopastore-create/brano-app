
import streamlit as st
import google.generativeai as genai
from PIL import Image
import os

st.set_page_config(page_title="CardioReport AI")
st.title("❤️ CardioReport AI")

# Entrada de la clave
api_key = st.text_input("Introduce tu Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    # USAMOS EL MODELO NORMAL, NO EL BETA
    model = genai.GenerativeModel('gemini-1.5-flash')

    archivo = st.file_uploader("Sube tu estudio", type=["jpg", "png", "jpeg", "pdf"])

    if archivo is not None:
        img = Image.open(archivo)
        st.image(img, caption="Documento cargado")

        if st.button("Analizar con IA"):
            with st.spinner("Analizando..."):
                try:
                    # Esta es la forma correcta de generar contenido
                    response = model.generate_content(["Analiza este informe médico:", img])
                    st.success("Análisis:")
                    st.write(response.text)
                except Exception as e:
                    st.error(f"Error: {e}")
