# Diagrama Lógico Completo del Agente (Optimización E2E + RAG)

```mermaid
stateDiagram-v2
    [*] --> Recibir_Prompt_del_Usuario
    
    Recibir_Prompt_del_Usuario --> Analisis_de_Intencion: LLM Evalúa el requerimiento
    
    Analisis_de_Intencion --> Flujo_RAG: ¿Pregunta Teórica / Logística?
    Analisis_de_Intencion --> Flujo_Optimizacion: ¿Petición de Optimización?
    
    %% Flujo RAG %%
    state "Flujo RAG (Retrieval-Augmented Generation)" as Flujo_RAG {
        direction TB
        Buscar_BD_Vectorial: tool: search_knowledge_base
        Extraer_Contexto: Extraer fragmentos relevantes (ChromaDB)
        Generar_Respuesta_Teorica: Sintetizar respuesta técnica
        
        Buscar_BD_Vectorial --> Extraer_Contexto
        Extraer_Contexto --> Generar_Respuesta_Teorica
    }
    
    %% Flujo Optimización E2E %%
    state "Flujo de Optimización Autónoma (E2E)" as Flujo_Optimizacion {
        direction TB
        Validar_Contexto: ¿Hay archivo Excel adjunto?
        Subir_Escenario_Base: tool: upload_modified_scenario
        Simular_Original: tool: run_simulation
        Exportar_Resultados: tool: export_simulation_results
        Analizar_KPIs_Base: tool: analyze_kpis
        
        Validar_Contexto --> Subir_Escenario_Base
        Subir_Escenario_Base --> Simular_Original
        Simular_Original --> Exportar_Resultados
        Exportar_Resultados --> Analizar_KPIs_Base
        
        Analizar_KPIs_Base --> Toma_Decisiones: LLM Razona según Prompt y KPIs
        
        state Toma_Decisiones {
            direction LR
            Objetivo_Demanda --> Decisión_0: +20% Demanda
            Objetivo_Costes --> Decisión_1: -15% Costes Transporte
            Objetivo_Servicio --> Decisión_2: +10% Safety Stock
        }
        
        Toma_Decisiones --> Modificar_Excel: tool: modify_scenario_excel
        note right of Modificar_Excel: Inyecta el Prompt en la\nDescripción del Excel
        
        Modificar_Excel --> Subir_Nuevo_Escenario: tool: upload_modified_scenario
        Subir_Nuevo_Escenario --> Simular_Nuevo: tool: run_simulation
        Simular_Nuevo --> Exportar_Nuevos_Resultados: tool: export_simulation_results
        Exportar_Nuevos_Resultados --> Analizar_Nuevos_KPIs: tool: analyze_kpis
    }
    
    Flujo_RAG --> Redactar_Respuesta_Final
    Flujo_Optimizacion --> Redactar_Respuesta_Final
    
    Redactar_Respuesta_Final: Redacción Caveman Style + Reasoning
    Redactar_Respuesta_Final --> [*]
```

### Explicación para tu TFG
1. **El Enrutador (Análisis de Intención):** Al recibir un mensaje, el LLM decide autónomamente si debe usar sus herramientas de lectura de base de datos (RAG) o sus herramientas de interacción con la API de AnyLogistix. 
2. **Capacidad Híbrida:** El agente es capaz de mezclar ambos flujos en un solo turno. Si el usuario pide *"Explícame qué es el Safety Stock y luego optimiza este archivo para mejorarlo"*, el agente pasará primero por el bloque RAG para buscar la definición, y luego saltará al bloque de optimización para aplicar el Excel, demostrando un uso avanzado de herramientas combinadas.
