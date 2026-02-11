
import streamlit as st
import google.generativeai as genai
from PIL import Image
import fitz  # PyMuPDF

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")
st.subtitle("Análisis inteligente de informes cardiológicos")

# --- CONFIGURACIÓN DE IA ---
clave_api_os = st.text_input("Introduce tu clave API de Gemini:", type="password")

if clave_api_os:
    # Esta configuración actualizada evita el error 404
    genai.configure(api_key=clave_api_os)
    # Usamos el modelo v1 estable
    modelo = genai.GenerativeModel('gemini-1.5-flash')

    # --- CARGADOR DE ARCHIVOS ---
    archivo = st.file_uploader("Sube tu estudio (JPG, PNG o PDF)", type=["jpg", "png", "jpeg", "pdf"])

    if archivo is not None:
        if archivo.type == "application/pdf":
            # Procesar PDF
            doc = fitz.open(stream=archivo.read(), filetype="pdf")
            pagina = doc.load_page(0)
            pix = pagina.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            # Procesar Imagen
            img = Image.open(archivo)

        st.image(img, caption="Documento cargado", use_container_width=True)

        if st.button("Analizar con IA"):
            with st.spinner("La IA está leyendo tu informe..."):
                try:
                    prompt = "Actúa como un asistente médico experto. Analiza esta imagen de un estudio cardiológico y explica los puntos clave en un lenguaje sencillo."
                    # Nueva forma de enviar la imagen al modelo
                    respuesta = modelo.generate_content([prompt, img])
                    
                    st.success("Análisis completado")
                    st.write(respuesta.text)
                except Exception as e:
                    st.error(f"Hubo un error: {e}")
else:
    st.warning("Por favor, introduce tu clave API para comenzar.")
