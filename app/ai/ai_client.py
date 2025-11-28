import google.generativeai as genai
import logging
from app.config import Config

logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self):
        self.config = Config
        if not self.config.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not found.")
        else:
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-flash-latest')

    def _sanitize_text(self, text):
        """Removes surrogate characters and ensures valid UTF-8"""
        if not text:
            return ""
        try:
            # Encode to utf-8 ignoring errors (strips surrogates), then decode back
            return text.encode('utf-8', 'ignore').decode('utf-8')
        except Exception:
            return str(text)

    def analyze_data(self, data_summary, email_body=""):
        """
        Sends the data summary and email body to Gemini and gets an analysis.
        """
        try:
            # Sanitize inputs to avoid encoding errors
            email_body = self._sanitize_text(email_body)
            data_summary = self._sanitize_text(data_summary)

            prompt = f"""
            Actúa como un Analista Senior yAsistente Ejecutivo. Tu tarea es procesar un correo electrónico y un resumen de datos adjuntos (si existen) para generar un reporte profesional.

            ENTRADAS:
            ----------------
            📧 CUERPO DEL CORREO:
            {email_body}
            
            📊 DATOS DEL ADJUNTO (Resumen/Estructura):
            {data_summary}
            ----------------

            INSTRUCCIONES:
            1. Analiza el tono y la intención principal del correo.
            2. Si hay datos adjuntos, analízalos en busca de métricas clave, tendencias, totales o anomalías. No solo describas el archivo, interpreta qué dicen los números.
            3. Cruza la información: ¿Los datos del adjunto responden a lo que se pide en el correo?

            FORMATO DE SALIDA (Estilo Chat/Telegram):
            Genera una respuesta estructurada, sin saludos innecesarios, usando estos bloques:

            📩 **RESUMEN EJECUTIVO**
            *   **Remitente/Intención:** [Quién escribe y qué quiere lograr específicamente]
            *   **Puntos Clave:** [Lista breve de requerimientos o fechas importantes]

            📊 **ANÁLISIS DE DATOS** (Solo si hay información del adjunto)
            *   **Contenido:** [De qué trata el archivo: Ventas, Inventario, Reporte HR, etc.]
            *   **Hallazgos Clave:** [Menciona cifras totales, promedios, el valor más alto/bajo o patrones detectados]
            *   **Observación Técnica:** [Calidad de los datos o columnas relevantes]
            *(Si no hay datos relevantes, indica: "No se detectó información analizable en el adjunto").*

            💡 **CONCLUSIÓN / ACCIÓN SUGERIDA**
            [Un breve veredicto profesional o sugerencia de respuesta basada en el análisis conjunto]

            REGLAS:
            - Mantén un tono objetivo y profesional.
            - Sé conciso pero informativo.
            - Responde SIEMPRE en ESPAÑOL.
            """
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error analyzing data with AI: {e}")
            return "Error generating AI analysis."
