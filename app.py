
import streamlit as st
import google.generativeai as genai
from PIL import Image
import fitz

# 1. Configuración de la página
st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")

# 2. Entrada de la llave API
api_key = st.text_input("Introduce tu Gemini API Key:", type="password")

if api_key:
    try:
        # 3. Configuración forzada para evitar errores de conexión
        genai.configure(api_key=api_key, transport='rest')
        
        # 4. Definición del modelo con RUTA COMPLETA (Solución al error 404)
        model = genai.GenerativeModel(model_name='models/gemini-1.5-flash')

        # 5. Subida de archivos
        archivo = st.file_uploader("Sube tu estudio (Imagen o PDF)", type=["jpg", "png", "jpeg", "pdf"])

        if archivo is not None:
            if archivo.type == "application/pdf":
                doc = fitz.open(stream=archivo.read(), filetype="pdf")
                pagina = doc.load_page(0)
                pix = pagina.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            else:
                img = Image.open(archivo)

            st.image(img, caption="Estudio cargado", use_container_width=True)

            # 6. Botón de análisis
            if st.button("Analizar con IA"):
                with st.spinner("Analizando informe..."):
                    try:
                        prompt = "Actúa como un cardiólogo experto. Analiza este informe y explica los resultados en lenguaje muy sencillo para el paciente."
                        response = model.generate_content([prompt, img])
                        st.success("Análisis completado:")
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Error en el análisis: {e}")
    except Exception as e:
        st.error(f"Error de configuración: {e}")
else:
    st.info("Por favor, introduce tu API Key para comenzar.")
