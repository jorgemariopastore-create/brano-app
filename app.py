
import streamlit as st
from google import genai
from PIL import Image
import fitz

# 1. Configuración de la página
st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")

# 2. Entrada de la llave API
api_key = st.text_input("Introduce tu Gemini API Key:", type="password")

if api_key:
    try:
        # 3. Conexión Forzada a Versión Estable (Evita el Error 404)
        # Usamos la sintaxis más moderna compatible con google-genai 1.63.0
        client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})
        
        # 4. Subida de archivos
        archivo = st.file_uploader("Sube tu estudio (Imagen o PDF)", type=["jpg", "png", "jpeg", "pdf"])

        if archivo is not None:
            # Procesamiento de PDF o Imagen
            if archivo.type == "application/pdf":
                doc = fitz.open(stream=archivo.read(), filetype="pdf")
                pagina = doc.load_page(0)
                pix = pagina.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            else:
                img = Image.open(archivo)

            # Mostramos la imagen con el formato de ancho corregido
            st.image(img, caption="Estudio cargado", width='stretch')

            # 5. Botón de análisis
            if st.button("Analizar con IA"):
                with st.spinner("Analizando informe..."):
                    try:
                        prompt = "Actúa como un cardiólogo experto. Analiza este informe y explica los resultados en lenguaje muy sencillo para el paciente."
                        
                        # Llamada al modelo usando la nueva librería
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
    st.info("Por favor, introduce tu API Key para comenzar.")
