# Plan de trabajo — Trabajo Final BI (Airbnb Bogotá)

**Entrega:** domingo 22 de noviembre, 11:59 PM (Teams) · **Peso:** 20% · **Equipo:** el mismo de antes
**Hoy:** sábado 14 de noviembre → quedan **8 días**.

---

## 1. Entregables (checklist maestro)

- [ ] **Informe PDF** (análisis > código; capturas propias; sin bloques largos de código)
- [x] **Notebook de ML ejecutado** (con salidas visibles)
- [ ] **Dashboard conectado al ETL** (capturas o enlace; nada de CSV sueltos)
- [ ] **Video de sustentación** (8–15 min, YouTube oculto / Drive / OneDrive)

## 2. Rúbrica → dónde se ganan los puntos

| Criterio | Peso | Qué hay que mostrar |
|---|---|---|
| Preguntas y enfoque | 10% | Mínimo 3 preguntas refinadas, claras y respondibles con datos |
| Visualizaciones y métricas | 25% | Gráficos útiles, KPIs, cada gráfico con "qué decisión permite" |
| Aplicación del modelo | 25% | Modelo bien justificado, evaluado e **interpretado críticamente** |
| Hallazgos y recomendaciones | 20% | Responder las preguntas + mín. 3 recomendaciones derivadas de resultados |
| Sustentación en video | 10% | Explicar, no leer el informe |
| Entrega y presentación | 10% | PDF ordenado y profesional |

> Los dos bloques de 25% (visualizaciones y modelo) son el 50% de la nota: ahí va el mayor esfuerzo.

---

## 3. Cronograma sugerido

| Día | Fecha | Foco | Responsable(s) | Resultado |
|---|---|---|---|---|
| 1 | Sáb 14 | Reparto de roles + definir problema y 3 preguntas | Todo el equipo | Preguntas refinadas acordadas |
| 2 | Dom 15 | Revisar ETL y dashboard del Trabajo 3 | Libardo + Robin | Lista de mejoras y estado de conexión |
| 3 | Lun 16 | Preparar evidencia del modelo y cerrar preguntas | Robin + Juan Carlos | Métricas interpretadas y preguntas acordadas |
| 4 | Mar 17 | Revisar hallazgos preliminares y estructura del informe | Juan Carlos + Robin | Esquema de informe y hallazgos con evidencia |
| 5 | Mié 18 | Mejoras finales al dashboard + capturas | Libardo | Dashboard revisado y capturas |
| 6 | Jue 19 | Redactar e integrar informe (secciones 1–5) | Juan Carlos; aportes de Libardo y Robin | Borrador v1 |
| 7 | Vie 20 | Recomendaciones, cierre, revisión y exportación PDF | Juan Carlos + todo el equipo | PDF v2 revisado |
| 8 | Sáb 21 | Grabar video + revisión cruzada | Todo el equipo | Video y entregables listos |
| — | Dom 22 | **Subir a Teams temprano** (no esperar a las 11:59 PM) | Todo el equipo | Entregado |



### Estado inicial del proyecto (14 de noviembre)

- [x] El ETL ya carga Listings, Reviews y Calendar en `output/airbnb.sqlite`.
- Ya existe un notebook de exploración, un informe del Taller 3 y un archivo
  `.pbix` del tablero anterior. La conexión y las visualizaciones del `.pbix`
  aún se deben validar en Power BI.
- [x] El entregable técnico prioritario, el notebook de Machine Learning, ya está
  creado y ejecutado desde SQLite. En la prueba inicial (3.724
  anuncios), el Random Forest obtuvo MAE de $60.590 COP y R² de 0,470; redujo el
  MAE un 30,7% frente a predecir la mediana. El informe y el video todavía
  requieren integrar estos hallazgos, capturas propias y revisión. Recalcular
  las métricas si se actualiza el ETL o la base.
- [ ] Validar la conexión y mejorar el dashboard en Power BI.
- [ ] Integrar los hallazgos al informe final y entregar PDF.
- [ ] Grabar y compartir el video de sustentación.
- El equipo reportado para este trabajo queda compuesto por Robin, Libardo y
  Juan Carlos; el reparto detallado y los compromisos de entrega están en la
  sección 6.

---

## 4. Plan por sección del informe

### 4.1 Contextualización (máx. 1 página)
- [ ] Enfoque general del análisis (1 párrafo)
- [ ] Qué aspectos del mercado Airbnb se estudian y por qué importan (precio, oferta por zona, disponibilidad, reseñas)
- [ ] Justificación del problema analítico elegido
- [ ] **Captura del modelo de datos / esquema del ETL** (imagen propia)

### 4.2 Preguntas de negocio refinadas (mínimo 3)
Partir de las preguntas del Trabajo 3 y reescribirlas de forma **medible**. Plantilla:

| # | Pregunta original | Pregunta refinada | Evidencia que la responde |
|---|---|---|---|
| 1 | ¿Qué zonas son más caras? | ¿Qué localidades de Bogotá tienen mayor precio mediano por noche y cómo varía según tipo de alojamiento? | Gráfico comparativo + KPI |
| 2 | ¿Qué influye en el precio? | ¿Qué variables (tipo de habitación, capacidad, localidad, reseñas) explican mejor el precio? | Correlaciones + modelo |
| 3 | ¿Hay patrones por zona/tipo? | ¿Existen segmentos diferenciados de alojamientos según precio, disponibilidad y calificación? | Segmentación / clustering |

*(Ajustar a las preguntas reales que ya trabajaron.)*

### 4.3 Visualizaciones y métricas
- [ ] Retomar las páginas del tablero del Trabajo 3 (Resumen, Oferta, Precios, Disponibilidad y reseñas, Detalle)
- [ ] Mejorar: claridad, legibilidad, títulos con mensaje, orden, filtros/segmentadores
- [ ] Cubrir los tipos esperados:
  - [ ] Gráficos comparativos
  - [ ] Distribuciones (p. ej., histograma de precio, con manejo de outliers)
  - [ ] Tendencias
  - [ ] KPIs (precio mediano, nº de anuncios, disponibilidad promedio, calificación promedio)
  - [ ] Relaciones entre variables (dispersión / correlación)
  - [ ] Segmentaciones o agrupaciones
- [ ] **Para cada visualización escribir 2–3 líneas:** qué decisión/patrón permite identificar y a qué pregunta responde
- [ ] Confirmar que el dashboard sigue **conectado al ETL / base de datos** (no a CSV sueltos)

### 4.4 Modelo de Machine Learning
**Paso 1 — Elegir el enfoque** (justificar por tipo de problema, variables y objetivo):

| Opción | Cuándo conviene | Métricas |
|---|---|---|
| Regresión (predecir precio) | Pregunta 2: qué variables explican el precio | MAE, RMSE, R² |
| Clasificación (p. ej., rango de precio alto/medio/bajo) | Predecir categoría | Accuracy, precision, recall, F1, matriz de confusión |
| Clustering (segmentos de alojamientos) | Pregunta 3: patrones/segmentos | Silhouette, método del codo, perfil de cada clúster |

- [x] Enfoque seleccionado: regresión del precio por noche, porque el objetivo es una variable continua.

**Paso 2 — Contenido obligatorio en el informe:**
- [ ] Objetivo del modelo (breve; pendiente integrarlo al informe)
- [ ] Variables utilizadas y justificación (pendiente integrarlo al informe)
- [ ] Proceso de preparación de datos (nulos, outliers, codificación, partición train/test; explicar en el informe que Random Forest no requiere escalado)
- [ ] Solo fragmentos de código estrictamente necesarios (capturas cortas)
- [ ] Métricas de evaluación correctas para el tipo de modelo (MAE, RMSE, R²; pendiente integrarlo al informe)
- [ ] Visualizaciones de apoyo (importancia de variables, real vs. predicho y residuos; pendiente agregarlas al informe)
- [ ] **Interpretación técnica y crítica** (pendiente integrarla al informe)

**Paso 3 — Buenas prácticas:**
- [x] Cargar los datos **desde la base del ETL** en el notebook
- [x] Comparar contra una línea base simple (predicción de la mediana)
- [x] Notebook ejecutado de arriba a abajo, con salidas visibles y comentarios en markdown

> **Importante (la guía lo dice explícitamente):** no se evalúa solo "tener buenos resultados". Si las métricas son flojas, explicar qué se intentaba, qué limitaciones hubo, interpretar con honestidad y proponer mejoras.

### 4.5 Hallazgos del análisis
- [ ] Responder **explícitamente** cada pregunta de negocio
- [ ] Explicar patrones y relaciones (no describir gráficos de forma aislada)
- [ ] **Conectar** lo visual con el modelo (p. ej., "la localidad que se ve cara en el tablero también aparece como variable importante en el modelo")
- [ ] Cada afirmación respaldada por un dato o gráfico, no por opinión

### 4.6 Recomendaciones accionables (mínimo 3)
Formato por recomendación: **Recomendación → Evidencia que la sustenta → Cómo aplicarla**

- [ ] Recomendación 1 (p. ej., segmentación de alojamientos)
- [ ] Recomendación 2 (p. ej., zonas de alto valor)
- [ ] Recomendación 3 (p. ej., variables clave para fijar precios)
- [ ] (Opcional) Recomendación 4: oportunidades de análisis futuro / datos adicionales

### 4.7 Cierre reflexivo (breve)
- [ ] Qué funcionó bien
- [ ] Qué dificultades hubo
- [ ] Qué se podría mejorar
- [ ] Por qué importa integrar ETL + visualización + ML en un flujo completo

---

## 5. Video de sustentación (8–15 min)

**Guion sugerido (con tiempos):**

| Min | Contenido | Quién |
|---|---|---|
| 0:00–1:30 | Contexto del problema y preguntas | Juan Carlos |
| 1:30–5:00 | Recorrido del dashboard (qué decisión permite cada página) | Libardo |
| 5:00–9:00 | ETL y modelo: objetivo, variables, métricas e interpretación | Robin |
| 9:00–11:30 | Hallazgos + relación visual ↔ modelo | Juan Carlos |
| 11:30–13:00 | Recomendaciones, limitaciones y conclusión | Juan Carlos; cierre conjunto |

- [ ] Ensayar una vez antes de grabar
- [ ] **No leer el informe ni el código**: explicar con palabras propias
- [ ] Verificar el enlace (permisos/visibilidad) antes de entregar

---

## 6. Reparto de tareas y entregas

| Responsable | Tareas asignadas | Entrega verificable | Fecha objetivo |
|---|---|---|---|
| **Libardo Alcides Bedoya Carmona** | Revisar el `.pbix`; comprobar que se actualiza desde el ETL/base de datos (sin CSV sueltos); mejorar títulos, filtros, KPIs y visualizaciones; describir qué decisión permite cada visual. | Dashboard actualizado, conexión validada y capturas propias; enviar a Juan Carlos los datos clave y notas de interpretación de cada página. | Diagnóstico: 15 nov. Capturas finales: 18 nov. |
| **Juan Carlos Escobar Gil** | Acordar las 3 preguntas refinadas; integrar la evidencia del tablero y del modelo; redactar e integrar el informe, hallazgos, mínimo 3 recomendaciones y cierre; exportar y revisar el PDF; coordinar el guion y el enlace del video. | Preguntas acordadas: 16 nov. Borrador: 19 nov. PDF y guion: 20 nov. Enlace accesible: 21 nov. |
| **Robin Alexander Montoya Velasquez** | Mantener el ETL/SQLite y el notebook de ML; entregar captura del esquema ETL y salidas del modelo; explicar al equipo MAE, R², línea base, variables importantes y limitaciones; revisar consistencia técnica y apoyar la sustentación. | Base y notebook reproducibles, evidencia técnica y revisión del informe/modelo. | Evidencia y explicación: 16 nov. Revisión final: 20–21 nov. |
| **Todo el equipo** | Validar preguntas y resultados, hacer revisión cruzada, ensayar, grabar y comprobar permisos del video antes de entregar. | Video de 8–15 minutos y entrega completa en Teams. | Ensayo: 20 nov. Video: 21 nov. Entrega: 22 nov. |

**Dependencias:** Libardo entrega primero el estado de conexión del dashboard y luego sus capturas/hallazgos; Juan Carlos usa esa evidencia y los resultados del notebook de Robin para redactar. Si el `.pbix` no puede conectarse a la base del ETL, el equipo debe resolverlo y documentarlo antes de presentar el dashboard como conectado. Robin no necesita rehacer el modelo salvo que cambien los datos o el ETL.

*(Todos deben dominar todo: la sustentación evalúa comprensión técnica individual.)*

---

## 7. Checklist final antes de subir

- [ ] El PDF tiene las 7 secciones + capturas propias de visualizaciones, dashboard, modelo y resultados
- [ ] Sin bloques largos de código en el PDF
- [ ] Mínimo 3 preguntas refinadas y mínimo 3 recomendaciones
- [ ] Contextualización ≤ 1 página, con captura del ETL
- [x] Notebook ejecutado y con salidas
- [ ] Dashboard conectado al ETL (capturas o enlace funcionando)
- [ ] Video entre 8 y 15 min con enlace accesible

