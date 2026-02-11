
import streamlit as st
import google.generativeai as genai
from PIL import Image
import fitz  # Esta librería es la que lee tus PDFs gratis

# Configuración de la aplicación
st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")

# Entrada de tu nueva clave (la que termina en j5cw)
api_key = st.text_input("Introduce tu Gemini API Key:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        # Aquí está el truco: usamos el modelo directo para evitar el error 404
        model = genai.GenerativeModel('gemini-1.5-flash')

        archivo = st.file_uploader("Sube tu estudio (Imagen o PDF)", type=["jpg", "png", "jpeg", "pdf"])

        if archivo is not None:
            # Si subes un PDF, este código saca una "foto" de la primera página
            if archivo.type == "application/pdf":
                doc = fitz.open(stream=archivo.read(), filetype="pdf")
                pagina = doc.load_page(0)
                pix = pagina.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            else:
                img = Image.open(archivo)

            st.image(img, caption="Estudio cargado correctamente", use_container_width=True)

            if st.button("Analizar con IA"):
                with st.spinner("La IA está analizando tu informe..."):
                    try:
                        # Le pedimos a la IA que sea clara y sencilla
                        prompt = "Actúa como un cardiólogo experto. Analiza este informe y explica los resultados en lenguaje muy sencillo para el paciente."
                        response = model.generate_content([prompt, img])
                        
                        st.success("Análisis completado:")
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error en el análisis: {e}")
    except Exception as e:
        st.error(f"Error de configuración: {e}")
else:
    st.warning("Por favor, introduce tu API Key para comenzar.")
