
import streamlit as st
from groq import Groq
import fitz  # PyMuPDF para extraer texto de PDF
from PIL import Image
import io

st.set_page_config(page_title="CardioReport AI", page_icon="❤️")
st.title("❤️ CardioReport AI")
st.subheader("Análisis Profesional Multiformato")

api_key = st.text_input("Introduce tu Groq API Key (gsk_...):", type="password")

if api_key:
    try:
        client = Groq(api_key=api_key)
        archivo = st.file_uploader("Sube tu estudio (Imagen o PDF)", type=["pdf", "jpg", "jpeg", "png"])

        if archivo is not None:
            texto_extraido = ""
            
            with st.spinner("Procesando documento..."):
                if archivo.type == "application/pdf":
                    # Extraer texto de PDF
                    with fitz.open(stream=archivo.read(), filetype="pdf") as doc:
                        for pagina in doc:
                            texto_extraido += pagina.get_text()
                else:
                    # Si es imagen, mostramos la previsualización
                    img = Image.open(archivo)
                    st.image(img, caption="Imagen cargada", width=500)
                    st.warning("Para imágenes, la precisión depende de la claridad del texto. Se recomienda PDF.")
                    # Nota: Para OCR real en la nube se requiere configuración extra de Tesseract.
                    # Por ahora, procesaremos el texto si viene de un PDF generado por el estudio.

            if st.button("Generar Informe Detallado"):
                if texto_extraido.strip():
                    with st.spinner("La IA está analizando los datos médicos..."):
                        try:
                            # Usamos el modelo más potente que tenés disponible
                            completion = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[
                                    {
                                        "role": "system", 
                                        "content": "Eres un cardiólogo experto. Tu tarea es analizar el texto de un informe médico y explicar cada valor, conclusión y observación de forma exhaustiva pero comprensible para el paciente."
                                    },
                                    {
                                        "role": "user", 
                                        "content": f"Realiza un análisis profundo del siguiente informe: {texto_extraido}"
                                    }
                                ],
                                temperature=0.2 # Menor temperatura = mayor precisión médica
                            )
                            st.success("Análisis Médico Completo:")
                            st.markdown(completion.choices[0].message.content)
                        except Exception as e:
                            st.error(f"Error en el análisis: {e}")
                else:
                    st.error("No se detectó texto en el archivo. Intenta subir un PDF original del laboratorio.")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
