# Documentación de Traspaso del TFG: AnyLogistix AI Assistant

Bienvenido/a al proyecto. Este documento recoge todo el trabajo de Ingeniería de Software e IA realizado durante la Fase 3 y 4 del TFG. El objetivo de este proyecto es dotar al simulador logístico AnyLogistix de un "Cerebro" de IA que permita orquestar todo su flujo de trabajo de forma completamente autónoma (End-to-End).

## Arquitectura del Proyecto
El proyecto no es un simple script de ChatGPT; es un **Agente ReAct** desarrollado en Python con arquitectura escalable:

1.  **Frontend (Chainlit):** Provee una interfaz conversacional amigable para el usuario.
2.  **Motor de Estados Finitos (LangGraph):** Orquesta el flujo de toma de decisiones de la IA. Le permite pensar, ejecutar herramientas y volver a pensar antes de responder. Además, utiliza `MemorySaver` para mantener un contexto a largo plazo ("Thread ID") durante toda la sesión.
3.  **LLM Core (Google Gemini 2.5 Flash):** El cerebro que razona las instrucciones. Seleccionado por su ventana de contexto de 1 millón de tokens, lo que le permite ingerir documentos RAG y excels inmensos sin olvidarse de nada. Además, está programado nativamente con el principio **"Caveman"**, obligándole a omitir palabras de relleno para ahorrar un ~65% de tokens y hacer que sus respuestas sean extremadamente analíticas, técnicas y directas, pero sin perder la estructura (siempre con razonamiento de negocio y unidades).
4.  **Backend RAG (Retrieval-Augmented Generation):** El agente tiene acceso a una base de datos vectorial (ChromaDB + HuggingFace Embeddings) que lee documentos de teoría logística. Esto evita que la IA alucine conceptos.
5.  **Herramientas Python (`alx_tools.py`):** Un conjunto de herramientas que el agente puede usar autónomamente:
    *   Cliente OpenAPI generado automáticamente que habla con el servidor Java de AnyLogistix (sube archivos, crea escenarios, lanza simulaciones).
    *   Gestor de Excels (`openpyxl` / `xlwings`) que modifica escenarios. Destaca su **Escáner Dinámico de Filas**, que lo hace 100% inmune a los cambios de formato de exportación de ALX.

## Configuración y Arranque
1.  **Entorno Virtual:** Asegúrate de tener instalado Anaconda o Miniconda.
    ```bash
    conda create -n tfg_anylogistix python=3.10
    conda activate tfg_anylogistix
    pip install -r requirements.txt
    ```
2.  **Variables de Entorno:** Debes setear la clave `GOOGLE_API_KEY` con un token válido de Google AI Studio.
3.  **Ejecución:** Sitúate en la carpeta del Chatbot y arranca el frontend:
    ```bash
    chainlit run app.py -w
    ```

## Dónde modificar qué cosa
*   **Si quieres añadir nuevas APIs de AnyLogistix:** Debes usar la librería cliente de Swagger en `alx_tools.py`.
*   **Si la IA "habla mucho" o no calcula bien algo:** Debes ajustar las reglas matemáticas o gramaticales en la variable `SYSTEM_PROMPT` del archivo `agent.py`.
*   **Si quieres revisar los errores ocultos:** Abre el archivo `sistema_funcional.log` generado automáticamente; la interfaz web solo muestra lo que le importa al usuario, los errores del servidor se quedan en el log.
*   **Si AnyLogistix cambia el exportador de Excel:** Probablemente debas actualizar la función `modify_scenario_excel` en `alx_tools.py`, aunque el escáner láser actual por filas está hecho para aguantar la inmensa mayoría de reestructuraciones.
