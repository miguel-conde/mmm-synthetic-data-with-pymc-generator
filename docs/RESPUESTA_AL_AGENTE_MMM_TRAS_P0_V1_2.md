# Respuesta del diseñador tras P0 de v1.2 — autorización condicionada de P1

**Proyecto:** Benchmark de MMM con `pymc-generator`, sin River  
**Fecha:** 2026-11-06  
**Documento recibido:** `respuesta_v1_2_al_disenador.md`  
**Destinatario:** agente GitHub Copilot, en el workspace actual de VS Code / WSL2.  
**Decisión:** acepto **provisionalmente** el cierre de P0 según el informe remitido. Autorizo los trabajos de P1 en etapas, no una campaña masiva.

## 0. Valoración y alcance de la aprobación

Reconozco la corrección del error de historia inicial del adstock, las 87 pruebas declaradas, el análisis de cobertura y el examen de factibilidad de E09. El fallo del periodo inicial cambia la interpretación de resultados anteriores: **no basta con excluir las semanas iniciales al puntuar si sus observaciones han influido en los parámetros estimados**.

Esta aprobación se basa en el **resumen del agente**. Todavía no dispongo para revisión independiente del código, las tablas por mundo y los informes a los que remite. Conserva el índice `reports/review_package_index.md` y los informes P0 sin alteraciones, y deja enlaces claros a los artefactos verificables. No afirmes que el diseñador ha auditado personalmente esos artefactos.

No reescribas v1 ni v1.1. No vuelvas a presentar los resultados antiguos de M3 como conclusiones definitivas sobre sesgo, cobertura o capacidad de decisión.

## 1. Decisión D1 — Ventana de ajuste: APROBADA, con una precisión técnica

Establece **`warmup = 8` semanas** como regla general, fija y conocida por la configuración del generador, para los experimentos actuales. Si el criterio específico por mundo indicaba 7 semanas, usar 8 es conservador y evita que la selección dependa de información privilegiada del SCM. Puedes mostrar la sensibilidad 7/8 por separado; no mezcles ambas reglas en el ranking principal.

Para todos los modelos comparables:

- **Datos de entrada:** conservar la secuencia de tratamientos y controles desde la semana 0 para calcular adstock y sus estados internos. No cortar las primeras 8 filas *antes* de efectuar el arrastre.
- **Contribución a la verosimilitud de entrenamiento:** únicamente observaciones de `Y` en `[8, n_train)`. Las semanas 0–7 no deben contribuir ni de forma directa ni mediante otros términos inadvertidos que dependan de su `Y` observado.
- **Validación temporal y predicción:** continuar con las ventanas ya establecidas, sin usar observaciones futuras de `Y` para ajustar parámetros; el historial de canales al inicio de test sí puede incluir las semanas anteriores observadas.
- **Comparaciones:** usar la misma ventana útil y los mismos mundos en los rankings. Si un método no tiene adstock, ajustar también sobre la ventana común cuando se haga una comparación estrictamente pareada; conservar, aparte, su antiguo resultado como referencia.
- **Escalado, priors dependientes de los datos y elección de hiperparámetros:** estimarlos con el conjunto de entrenamiento permitido; documentar de forma separada cualquier uso permitido de los canales durante la fase inicial para formar las variables transformadas. No utilizar `Y` futuro ni la verdad generadora.

### Implementación de M3: condición previa de P1a

Autorizo implementar una **verosimilitud enmascarada**, o un mecanismo matemáticamente equivalente, para PyMC-Marketing 1.3.0 con la API realmente instalada. No presupongas que la documentación de versiones posteriores se aplica sin cambios.

Antes de realizar MCMC costoso, exige pruebas de estas propiedades:

1. El modelo calcula adstock y saturación sobre la secuencia completa de entrada y conserva el estado que afecta a las semanas 8 en adelante.
2. Su función de log-verosimilitud coincide, en un ejemplo pequeño con parámetros fijos, con la suma manual de los términos semanales **solo** de `[8, n_train)`; no hay una segunda verosimilitud que cuente observaciones por duplicado.
3. Cambiar el `Y` observado en semanas 0–7, manteniendo el resto fijo, no cambia la log-verosimilitud ni el ajuste de los parámetros (salvo error numérico/aleatoriedad del muestreo). **No** se exige que cambiar los canales de esas semanas deje el resultado igual: deben afectar a los estados de arrastre posteriores.
4. Los resultados de E02 lineal coinciden, dentro de lo esperable para sus priors y el error de muestreo, con una formulación de referencia independiente; verifica también al menos un escenario con arrastre Weibull/geometría y saturación no lineal. Comprueba la igualdad determinista de transformaciones antes de exigir coincidencia entre posteriores.
5. No se rompen las contribuciones por canal, las escalas, las predicciones, la extracción de resultados ni los diagnósticos MCMC.
6. El informe identifica si M3 sigue siendo la clase estándar de PyMC-Marketing con una modificación controlada de la verosimilitud o si pasa a ser un modelo PyMC propio que reutiliza sus componentes. No confundir ambas arquitecturas.

**Secuencia autorizada:** pruebas deterministas → ensayo mínimo de 3–5 mundos (incluido E02) → piloto de 5–10 mundos estratificados con V3 y la nueva verosimilitud → evaluación ampliada solo si pasan los diagnósticos. Guarda el coste y la tasa de convergencia. Mantén los criterios `R-hat ≤ 1,01`, ESS bulk ≥ 400 y cero divergencias para considerar válido el ajuste.

**Punto crítico:** al estudiar nuevas priors o funciones de respuesta, la referencia de comparación será **V3 con la ventana corregida**, no la V3 antigua contaminada por las semanas 0–7. Deja esta última en una columna histórica separada. No atribuyas a una prior nueva la mejora que pueda deberse solo al enmascaramiento.

Una vez validadas las pruebas de la ventana, **autorizo** la repetición de los modelos rápidos en los subconjuntos F3 y E10A y la actualización de E08/E09 con los ajustes disponibles, usando las mismas configuraciones y semillas, sin nueva generación masiva. Separa el coste y los resultados de estas correcciones de los experimentos científicos nuevos. Si las políticas incorporan M3, sus resultados corregidos deberán esperar al nuevo ajuste M3.

## 2. Decisión D2 — Efectos nulos en P1a: empezar con ROPE, reservar spike-and-slab

**Elección para el primer piloto: contracción continua y ROPE**, no `spike-and-slab` de entrada. Motivos: menor complejidad, comparación más limpia con el M3 actual y menor riesgo de emplear el tiempo en problemas de muestreo de un modelo nuevo. Esto **no** convierte una prior continua en una prueba de nulidad exacta. Conserva `spike-and-slab` como línea posterior, si la selección exacta de canales sigue siendo una cuestión central.

Antes de probar priors nuevas, calcula con la posterior **V3 corregida** una decisión ROPE de referencia. Fija de antemano:

- **Estimando:** contribución **directa** media semanal del canal, en unidades originales de `Y`, calculada sobre una ventana establecida de semanas ≥ 8 y con las exposiciones observadas de esa ventana. No apliques ROPE al coeficiente bruto `beta`, que cambia de escala según la transformación.
- **Umbral:** `delta = 0,005 × media(|Y_train|)` en esa misma escala; la media se calcula solo sobre las semanas de entrenamiento permitidas. Esta regla queda fijada para el piloto, sin ajustar `delta` a los resultados causales verdaderos.
- **Regla de decisión exploratoria:** «prácticamente nulo» si `P(0 ≤ contribución < delta | datos) ≥ 0,95`; «efecto relevante» si `P(contribución ≥ delta | datos) ≥ 0,95`; si no, «indeterminado». Es un umbral de decisión, **no** un intervalo de cobertura del 95 % ni una prueba de `beta = 0`.
- **Evaluación:** sensibilidad, falsos positivos, precisión, proporción de indeterminados y errores de contribución, por `direct`, `feeder` e `isolated`; además cobertura de intervalos sobre directos y tasa de validez MCMC. En feeders la verdad directa es cero, pero el efecto total `do` puede ser positivo.

Después compara, en los **mismos mundos y con la misma ventana corregida**, tres variantes mínimas: **V3 corregida**, **V3 con contracción continua modificada sin alterar familias de respuesta**, y **V3 con familias de respuesta más flexibles sin cambiar la prior de efecto**. Solo estudia la combinación de cambios si los pilotos anteriores muestran utilidad y el coste es razonable.

No elijas la prior que minimiza el error frente a la verdad sintética en el conjunto de evaluación. Selecciona hiperparámetros con criterios disponibles para un analista real en el conjunto de desarrollo, registra la decisión y evalúa después sobre mundos reservados. Los 35 mundos que no se usaron para elegir V3 ya se han consultado en sucesivas auditorías; **no los describas como una prueba final completamente independiente de todas las decisiones posteriores**. Si queremos una confirmación fuerte, prepara una pequeña muestra nueva, con semillas registradas tras congelar las especificaciones, y úsala una sola vez.

## 3. Decisión D3 — E10A y E14: diseños APROBADOS como pilotos

### P1b / E10A: confusión

Autorizo **40 pares por nivel con T = 104**, comenzando por un diseño donde cambie un solo mecanismo a la vez. Registra antes los niveles elegidos y el número de mundos efectivo:

- Intervención sobre las aristas `D→C` y `D→Y` (separa, cuando la API lo permita, intensidad de ambas aristas).
- Correlación de perturbaciones `rho`, sin cambiar a la vez los coeficientes de `D`.
- Condición con `D` observable **solo como control privilegiado**, claramente separada de los modelos ciegos.

El pareamiento debe conservar DAG, semillas básicas, parámetros ajenos al mecanismo y fuentes de azar cuando sea matemáticamente posible. Verifica qué cantidad exacta cambia al variar `rho`; usar la misma semilla no garantiza por sí solo que las innovaciones **resultantes** sean iguales. Al comparar errores, utiliza para cada mundo su **propia verdad contrafactual**.

Fija una métrica primaria de sesgo del efecto de intervención y métricas secundarias para contribución directa, predicción y atribución. No confundas correlación observada, confusión causal y falta de identificación. La potencia declarada en el piloto solo cubre los métodos y contrastes donde se justificó: no prometas detectar un efecto de 0,005 en M2 si sus resultados son más variables. No amplíes aún T a 52/208.

### P1c / E14: multicolinealidad sin confusión

Autorizo **30 pares × 3 niveles de `zc_coeff_range`, con T = 104**, ejecutados tras E10A. Mantén `Z→C`, sin efecto directo `Z→Y`, sin `D` común no observado y sin interacciones `C→C` en el control principal. Verifica esto en el DAG de cada mundo y no solo en la configuración global.

Mide la correlación **realmente lograda** entre los canales, el número de condición y la estabilidad/rango de la matriz de diseño, tanto sobre entradas crudas como sobre las transformaciones que se usen para ajustar. Conserva comparabilidad en ruido, señal y número de canales. Un `Z` que afecta a varios canales sin ruta adicional propia hacia `Y` puede causar multicolinealidad sin ser confusor de `C→Y`. Comprueba por separado si incluir `Z` en los ajustes mejora o empeora la estimación.

Antes de ejecutar las 90 parejas, confirma que los tres niveles generan una separación real de correlaciones; si no, detén el piloto y propón una modificación registrada, sin retocar los niveles después de mirar la métrica causal.

## 4. Revisión E09 y comunicación científica

- Mantén `all_channels_clamped_policy` como **intervención sintética definida por el protocolo**. No presupongas que controlar simultáneamente todos los canales es viable en cualquier plan de medios real, sobre todo si el SCM contiene `C→C`.
- La igualdad de resultados en 11 arranques muestra **estabilidad del mejor valor encontrado**, no certifica un óptimo global. Usa esa expresión, salvo prueba adicional de globalidad.
- No incorpores al ranking de políticas aplicables la corrección presupuestaria que usa la verdad del SCM.
- La política de canales seleccionados sigue siendo exploratoria: informa factibilidad, gasto realizado y valor obtenido, sin esconder los incumplimientos de presupuesto.
- No llames ROAS monetario a ratios basados en unidades sintéticas de tratamiento.
- Separa «atribución histórica», «efecto total de una intervención» y «valor de una decisión». Una misma magnitud no sustituye a las otras.

## 5. Entregables y criterios de avance

**Entrega A — corrección metodológica y piloto de M3 (antes de nuevos ajustes bayesianos extensos):**

1. `reports/p1a_warmup_validation.md`: descripción exacta del enmascaramiento, prueba de log-verosimilitud, conservación de historia de adstock, E02 lineal y casos no lineales, resultado de los tests, cambios de API, tiempo y memoria.
2. `reports/p1a_m3_rebaseline.md`: V3 original frente a **V3 enmascarada**, en los mismos mundos piloto, con sesgo, cobertura de directos, indicadores sobre nulos y convergencia.
3. Informe breve al diseñador con una respuesta explícita: «¿La corrección de la ventana explica una parte importante del sesgo negativo y la baja cobertura en directos?». Si no hay suficientes ajustes válidos, responder **no concluyente**.

**Entrega B — especificaciones, después de superar A:**

4. `reports/p1a_null_effects_and_response_shapes.md`: resultados ROPE y comparación de variantes en las mismas muestras; decisión sobre si merece probar después `spike-and-slab`.
5. `reports/p1b_e10a_confounding.md` y `reports/p1c_e14_collinearity.md`: resultados con parejas, estimandos, tamaños, intervalos, diagnósticos y límites.
6. `reports/p1_corrected_baselines.md`: corrección de modelos rápidos y, en su caso, E08/E09; distinguir estimaciones antiguas de corregidas.

**Control de calidad:** tests automáticos; configuración y código congelados por fase; hashes de entradas y versiones; n.º de mundos, células DAG y ajustes válidos; tablas pareadas; separación desarrollo/evaluación; costes medidos. Conserva intactos v1, v1.1 y P0.

**Regla de interrupción:** si el enmascaramiento falla una prueba esencial, no ejecutes M3. Si las variantes MCMC no cumplen los diagnósticos en el piloto, no amplíes muestra. E10A/E14 con modelos rápidos pueden avanzar por separado, siempre que usen las ventanas corregidas y el protocolo registrado.

## 6. Orden de trabajo que autorizo

1. Congelar el protocolo P1 y el estado P0; anotar el defecto de inicialización de v1/v1.1 en sus índices, **sin modificar sus resultados congelados**.
2. Implementar y **probar** el enmascaramiento de M3. Hacer primero pruebas deterministas y después 3–5 mundos.
3. Ejecutar el pequeño piloto pareado V3 antigua / V3 corregida; si los resultados son válidos, aplicar ROPE a la nueva posterior y empezar la comparación de especificaciones.
4. Corregir los modelos rápidos y los informes derivados sobre las muestras existentes, incluidos E08/E09 cuando corresponda.
5. Ejecutar E10A y, si supera sus controles, E14, con los tamaños y límites aprobados.
6. Informar de resultados; **no** iniciar 600 nuevos mundos, 45 ajustes oracle ni redes neuronales sin un nuevo diseño acordado.

**Formato de la próxima respuesta:** resumen de resultados verdaderamente ejecutados, hallazgos y anomalías, coste y pruebas, decisiones que siguen pendientes. Si el informe breve no permite una auditoría externa, adjunta o empaqueta al menos las tablas, la configuración y los informes citados en `review_package_index.md`.
