
import streamlit as st
import google.generativeai as genai
from PIL import Image
import fitz  # Esto lee tus PDFs sin pagar nada

st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")

# Entrada de la clave que termina en j5cw
api_key = st.text_input("Introduce tu Gemini API Key:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        # USAMOS EL MODELO DIRECTO PARA EVITAR EL ERROR 404
        model = genai.GenerativeModel('gemini-1.5-flash')

        archivo = st.file_uploader("Sube tu estudio (Imagen o PDF)", type=["jpg", "png", "jpeg", "pdf"])

        if archivo is not None:
            if archivo.type == "application/pdf":
                # Este código convierte el PDF en imagen automáticamente
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
                        # Instrucción para la IA
                        response = model.generate_content(["Actúa como cardiólogo. Explica este informe de forma sencilla:", img])
                        st.success("Análisis:")
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error en el análisis: {e}")
    except Exception as e:
        st.error(f"Error de configuración: {e}")
