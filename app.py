
import streamlit as st
import google.generativeai as genai
from PIL import Image
import fitz  # Esta es la librería PyMuPDF que ya tienes en requisitos

st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")

api_key = st.text_input("Introduce tu Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    archivo = st.file_uploader("Sube tu estudio (Imagen o PDF)", type=["jpg", "png", "jpeg", "pdf"])

    if archivo is not None:
        # Si es PDF, lo convertimos a imagen para que la IA lo vea
        if archivo.type == "application/pdf":
            doc = fitz.open(stream=archivo.read(), filetype="pdf")
            pagina = doc.load_page(0)
            pix = pagina.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            img = Image.open(archivo)

        st.image(img, caption="Documento listo para analizar", use_container_width=True)

        if st.button("Analizar con IA"):
            with st.spinner("Leyendo informe..."):
                try:
                    response = model.generate_content(["Actúa como un cardiólogo experto. Explica este informe en lenguaje sencillo:", img])
                    st.success("Análisis completado:")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Error en el análisis: {e}")
