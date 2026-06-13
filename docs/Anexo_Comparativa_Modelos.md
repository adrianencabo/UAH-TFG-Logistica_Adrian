# Anexo: Comparativa de Modelos de Lenguaje (LLMs) Evaluados

Durante el desarrollo de la Fase 3 y 4 del Trabajo de Fin de Grado, se evaluaron diferentes Modelos de Lenguaje Grande (LLMs) para orquestar el Agente ReAct encargado de la automatización en AnyLogistix. A continuación se expone la comparativa y justificación de la arquitectura final.

## 1. OpenAI (GPT-4 / GPT-3.5-Turbo)
**Evaluación Inicial:**
*   **Ventajas:** Excelente capacidad de razonamiento lógico ("Reasoning") y seguimiento estricto de JSON schemas para llamadas a herramientas (Tool Calling).
*   **Desventajas:** Coste por token elevado en un flujo de simulación completo donde se procesan miles de tokens por iteración (matrices de KPIs, lecturas de Excel, múltiples pasos RAG).
*   **Conclusión:** Se descartó para la versión de producción para garantizar que la herramienta final fuese escalable y gratuita para uso académico.

## 2. Canopy Wave (Pinecone / Custom LLMs)
**Evaluación Intermedia:**
*   **Ventajas:** Excelente integración para la ingesta rápida de documentos y generación de la base de conocimiento (RAG).
*   **Desventajas:** Servicio de pago con límites de cuota (rate limits) muy estrictos en su capa gratuita. Durante los tests de "Mega-Prompts" (ejecuciones end-to-end completas), el servicio bloqueaba la API frecuentemente, lo cual rompía la automatización.
*   **Conclusión:** Se abandonó debido a la inestabilidad por límites de uso comercial en entornos académicos.

## 3. Google Gemini 2.5 Flash (Elección Final)
**Evaluación Definitiva:**
*   **Ventajas Principales:**
    *   **Context Window (1 Millón de Tokens):** Permite procesar historiales enteros de conversación, lecturas completas de excels, y múltiples resultados de simulaciones sin perder contexto ni olvidar las instrucciones originales ("Lost in the middle").
    *   **Velocidad (Flash):** Tiempos de inferencia reducidos, ideal para un ciclo automatizado que requiere múltiples pasos intermedios (leer, razonar, modificar, subir, simular, comparar).
    *   **Tool Calling Nativo:** Integración perfecta con LangGraph para ejecutar funciones en Python (`alx_tools.py`).
    *   **Accesibilidad Académica:** Permite operar a un volumen altísimo de peticiones eludiendo los bloqueos típicos de pago.
*   **Ajuste "Caveman":** A pesar de que su ventana de contexto es enorme, se implementaron técnicas nativas de restricción de tokens (estilo telegráfico o "Caveman") en su System Prompt. Esto redujo el consumo de tokens de salida un 65%, acelerando las respuestas y optimizando la eficiencia algorítmica del Agente.

## Conclusión
La migración de Canopy Wave / OpenAI hacia **Google Gemini 2.5 Flash** emparejado con **LangGraph** proporcionó el equilibrio óptimo entre **razonamiento avanzado (ReAct)**, **memoria a largo plazo** y **estabilidad técnica** sin incurrir en bloqueos por costes de API, asegurando el éxito del flujo *End-to-End* de este TFG.
