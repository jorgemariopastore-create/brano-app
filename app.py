
def redactar_con_ia(datos_dict):
    if not datos_dict:
        return "No se detectaron datos numéricos suficientes."

    datos_texto = "\n".join([f"{k}: {v}" for k, v in datos_dict.items() if v and v.lower() != "nan"])

    prompt = f"""
    Actúa como un cardiólogo. Redacta los hallazgos técnicos de un ecocardiograma.
    DATOS:
    {datos_texto}
    
    REGLAS:
    - Redacción técnica formal.
    - SIN recomendaciones ni tratamientos.
    - Si el médico escribió observaciones, inclúyelas.
    - Sé breve y profesional.
    """
    
    try:
        completion = client.chat.completions.create(
            # MODELO ACTUALIZADO: llama-3.1-8b-instant
            model="llama-3.1-8b-instant", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error en Groq: {str(e)}"
