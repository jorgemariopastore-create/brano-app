
import streamlit as st
import google.generativeai as genai
from PIL import Image
import fitz

# Configuración de la página
st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")
st.subheader("Análisis inteligente de informes cardiológicos")

# --- CONFIGURACIÓN DE IA ---
os_api_key = st.text_input("Introduce tu Gemini API Key:", type="password")

if os_api_key:
    # Líneas 18 y 19 corregidas con transport='rest' para evitar el error 404
    genai.configure(api_key=os_api_key, transport='rest')
    model = genai.GenerativeModel('gemini-1.5-flash')

    # --- CARGADOR DE ARCHIVOS ---
    archivo = st.file_uploader("Sube tu estudio (JPG, PNG o PDF)", type=["jpg", "png", "jpeg", "pdf"])

    if archivo is not None:
        if archivo.type == "application/pdf":
            doc = fitz.open(stream=archivo.read(), filetype="pdf")
            pagina = doc.load_page(0)
            pix = pagina.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            img = Image.open(archivo)

        st.image(img, caption="Documento cargado", use_container_width=True)

        if st.button("Analizar con IA"):
            with st.spinner("La IA está leyendo tu informe..."):
                try:
                    prompt = "Actúa como un asistente médico experto. Analiza esta imagen de un estudio cardiológico y explica los puntos clave en lenguaje sencillo. Si hay valores fuera de lo normal, menciónalo con cautela y aclara que esto no reemplaza la consulta médica."
                    response = model.generate_content([prompt, img])
                    
                    st.success("Análisis completado:")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Hubo un error: {e}")
else:
    st.warning("Por favor, introduce tu API Key para comenzar.")
