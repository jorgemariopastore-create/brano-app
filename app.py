
import streamlit as st
import google.generativeai as genai
from PIL import Image
import fitz

st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")

api_key = st.text_input("Introduce tu Gemini API Key:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key, transport='rest')
        model = genai.GenerativeModel('gemini-1.5-flash')
        archivo = st.file_uploader("Sube tu estudio", type=["jpg", "png", "pdf"])

        if archivo is not None:
            if archivo.type == "application/pdf":
                doc = fitz.open(stream=archivo.read(), filetype="pdf")
                img = Image.frombytes("RGB", [doc[0].get_pixmap().width, doc[0].get_pixmap().height], doc[0].get_pixmap().samples)
            else:
                img = Image.open(archivo)
            st.image(img, use_container_width=True)

            if st.button("Analizar"):
                with st.spinner("Analizando..."):
                    res = model.generate_content(["Explica este informe médico:", img])
                    st.write(res.text)
    except Exception as e:
        st.error(f"Error: {e}")
