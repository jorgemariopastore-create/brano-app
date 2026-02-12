
import streamlit as st
import google.generativeai as genai
from PIL import Image
import fitz

st.title("❤️ CardioReport AI")

key = st.text_input("API Key:", type="password")

if key:
   genai.configure(api_key=key, transport='rest') 
    # ESTA LINEA ES LA QUE DA EL ERROR SI DICE BETA. 
    # ASEGÚRATE QUE QUEDE ASÍ:
    model = genai.GenerativeModel('gemini-1.5-flash')

    file = st.file_uploader("Subir PDF o Imagen", type=["jpg", "png", "pdf"])

    if file:
        if file.type == "application/pdf":
            doc = fitz.open(stream=file.read(), filetype="pdf")
            img = Image.frombytes("RGB", [doc[0].get_pixmap().width, doc[0].get_pixmap().height], doc[0].get_pixmap().samples)
        else:
            img = Image.open(file)
        
        st.image(img, use_container_width=True)
        
        if st.button("Analizar"):
            with st.spinner("Analizando..."):
                try:
                    res = model.generate_content(["Explica este informe médico de forma simple:", img])
                    st.write(res.text)
                except Exception as e:
                    st.error(f"Error: {e}")

