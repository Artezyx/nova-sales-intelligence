# Ficha de modelo — synthetic-logit-v1

## Uso previsto
Demostrar un flujo reproducible de ML supervisado y scoring explicable para priorización comercial, no estimar conversiones reales. No utilizar para decisiones comerciales de alto impacto ni para evaluación de individuos. Nunca se ejecuta contacto automáticamente.

## Datos y entrenamiento
Se generan 3,200 filas sintéticas con semilla 42. Las etiquetas se muestrean de una distribución Bernoulli definida por una función logística con pesos explícitos sobre seis variables comerciales: interacciones, días desde último contacto, demo solicitada, presupuesto confirmado, contacto decisor y ajuste al producto. No se emplean características demográficas. Se divide 75/25 de forma estratificada y se ajusta una regresión logística scikit-learn. El modelo se entrena al iniciar el proceso y se almacena en memoria; no carga artefactos pickle externos.

## Resultados de la ejecución local
- Entrenamiento: 2,400 filas.
- Evaluación: 800 filas.
- ROC AUC: 0.7956.
- Brier score: 0.1848.
- Exactitud con umbral 0.5: 0.7262.

Los resultados evalúan la capacidad de aproximar el generador sintético, no el mercado real. No han sido evaluados sesgo, deriva, calibración externa, fuga temporal o rendimiento en empresas reales. Los umbrales de 40 y 70 son convenciones ilustrativas. Los aportes se calculan respecto de un vector de referencia normalizado a 0.5; no son efectos causales.

## Recuperación de conocimiento
TF-IDF de unigramas y bigramas con similitud coseno, cinco guías locales escritas para la demo. Si la similitud es menor que 0.12, abstención. No es un LLM ni RAG generativo. El contexto del prospecto se presenta únicamente a su organización. No hay evaluación amplia de calidad de recuperación; las pruebas verifican ejemplos puntuales.

## Próxima validación necesaria
Datos autorizados y representativos, corte temporal, definición de objetivo comercial, evaluación comparativa contra reglas simples, calibración, métricas por segmentos de negocio, detección de deriva, registro de versión y revisión humana.
