# Respuesta al agente — revisión de P1, Entrega A y autorización condicionada de la siguiente fase

**Fecha:** 2026-11-06  
**Proyecto:** banco de pruebas de MMM con `pymc-generator`, sin acceso a River  
**Documento revisado:** `respuesta_P1_al_disenador.md`  
**Destinatario:** agente GitHub Copilot (VS Code / WSL2)

## 0. Dictamen y reglas generales

**Apruebo la Entrega A como hito de implementación y como análisis exploratorio. No doy por resueltos el ajuste bayesiano M3 ni su cobertura.** El motor de verosimilitud enmascarada parece bien contrastado según tu informe, pero no dispongo en esta conversación del código ni de los informes enlazados para auditarlo de modo independiente.

Conserva sin cambios todos los artefactos y manifiestos congelados de v1, v1.1 y P0. Mantén los resultados nuevos y antiguos con etiquetas claras: `legacy_w0`, `corrected_w8`, `privileged`, `blind`, `converged_strict`, `exploratory`. No reescribas los resultados previos. No emprendas campañas masivas, ni ejecutes M4 ni redes neuronales por ahora. Registra diseño, semillas, versiones y decisiones **antes** de ejecutar cada bloque.

**Resultado relevante ya observado:** el sesgo de M3 en canales directos pasa descriptivamente de −0,022 a +0,001 al corregir el periodo inicial; M2p también mejora mucho. **Pero no está probado todavía que el cambio del enmascaramiento, por sí solo, explique toda la mejora**, ni que la cobertura de M3 alcance una calibración aceptable.

## 1. Decisiones solicitadas

| Nº | Consulta | Decisión |
|---|---|---|
| D1 | M3: ampliar, mejorar muestreo o relajar R-hat | **Opción (b)**. Primero un diagnóstico y ajuste *limitado* del muestreador, sin usar la verdad generadora. Mantén como principal R-hat ≤ 1,01, ESS bulk ≥ 400 y 0 divergencias. No relajes el criterio para proclamar validez. |
| D2 | ROPE y nulos | **Mantener el ROPE como análisis de relevancia práctica**: δ = 0,005 × media de \|Y\| semanal, en **unidades de contribución directa semanal**, con umbral de decisión posterior prefijado. No equipararlo a identificar un coeficiente exactamente cero ni sacar conclusiones sobre nulos con solo cuatro casos. |
| D3 | Niveles E14 | **Acepto {0; 1,5; 3,0} como niveles de un piloto de diseño**, no todavía como prueba aislada de multicolinealidad pura. Debes verificar y, si hace falta, igualar distribuciones marginales de inversión, señal, ruido y magnitud del efecto. |
| D4 | M2 sobreestima tras la corrección | **Conservar M2 actual como referencia**, sin corregirlo a posteriori. Realiza una auditoría de su selección de formas y, si propones una rejilla distinta, crea `M2v2`, con selección en desarrollo y evaluación separada. |

Los resultados E10A y la corrección de las líneas base se aceptan **con las salvedades y pruebas adicionales del apartado 4**.

## 2. P1a — M3: separar el efecto del enmascaramiento del escalado

### P1a.0 — Control imprescindible de dos cambios simultáneos

El informe indica que en M3 enmascarado se modificaron **dos elementos**: (i) qué observaciones entran en la verosimilitud y (ii) la escala de `Y`, que ahora se estima en `[8, n_train)`. Si la referencia histórica usa otra escala, la comparación w0/w8 no aísla el efecto del enmascaramiento.

En una muestra pequeña y pareada, compara estos tres brazos:

- **A, histórico:** verosimilitud desde 0 y escalado original.
- **B, control de escala:** verosimilitud desde 0, pero **exactamente el mismo escalado** que en C, calculado a partir de `[8, n_train)`.
- **C, corrección principal:** verosimilitud desde 8 y el mismo escalado que B; conservar todos los datos anteriores de los canales para calcular el adstock.

Contrastes: **B − A** identifica el efecto del cambio de escala en esa comparación; **C − B** aísla el efecto del enmascaramiento. Confirma también que el cambio de escala no modifica inadvertidamente la prior en unidades originales; si lo hace, cuantifica esa diferencia y evita atribuir todo el contraste al enmascaramiento.

No hace falta repetir este control en 600 mundos: úsalo como prueba de identificación del cambio de implementación, con diagnósticos de muestreo y estimandos idénticos.

### P1a.1 — Mejora de muestreo sin seleccionar por la verdad

1. Trabaja primero con **6–10 mundos de desarrollo** identificados de forma explícita. Indica cuáles coinciden con los usados anteriormente para elegir V3; **no son una muestra independiente**.
2. Documenta qué falla: por parámetro y mundo, R-hat, ESS bulk/tail, divergencias, BFMI, saturación de profundidad del árbol, correlaciones posteriores y tiempos.
3. Registra antes de ejecutar **como máximo dos variantes** de muestreo que mantengan la **misma posterior objetivo**; por ejemplo, más etapas de adaptación o más extracciones, y solo una reparametrización si conserva la distribución. Distingue una mejora del muestreador de un cambio en priors/modelo.
4. Escoge la variante **solo** por convergencia y coste, sin examinar cobertura ni errores frente al SCM. Mantén la configuración original como referencia.
5. Regla para pasar a evaluación: al menos **8/10 ajustes estrictamente válidos** en el piloto de 10, sin un fallo sistemático no explicado por escenario. En caso contrario, documenta el límite y no hagas la ampliación completa por inercia.
6. Si se supera la regla, congela la configuración y evalúala sobre el subconjunto **no utilizado** para tomar estas decisiones. El informe menciona 35 mundos: verifica solapamientos; si existen, sepáralos o fija un nuevo conjunto confirmatorio antes de generar/ajustar nada.
7. Para comparar cobertura w0/w8, usa la **intersección de mundos donde ambos son válidos** bajo la regla estricta. Informa asimismo los resultados descriptivos en todos los mundos, sin confundirlos con una evaluación de ajustes válidos. Como orientación, pretende ≥ 20 pares válidos para una conclusión confirmatoria; si no se alcanza, informa «no concluyente».

**No aprobar la opción (c)** como criterio principal. Se puede publicar una sensibilidad secundaria con R-hat ≤ 1,015, claramente etiquetada como tal, sin cambiar la regla principal después de conocer las respuestas.

### P1a.2 — Cobertura, nulos y ROPE

- Cobertura de intervalos nominales al 50/80/95 %, anchura y sesgo de contribuciones **directas**, separados por `direct`, `feeder` y `isolated`; escenario y T; distinguir ajustes válidos y no válidos.
- Para cada resultado, indica la unidad básica de inferencia: **mundo** (con agrupación por célula DAG cuando proceda). No construyas IC de diferencias tratando canal-semana como réplica independiente. El contraste publicado de cobertura 0,46→0,61 procede de solo cuatro pares: verifica el algoritmo de bootstrap y advierte de su alta incertidumbre.
- Distingue el estimando `historical_observed_path` del efecto causal total de `do`, y usa idéntica ventana, escala y normalización en verdad y posterior.
- **ROPE:** sobre la contribución directa semanal en unidades de `Y`, δ = 0,005 × media\|Y\| semanal, fijando de antemano qué media se usa y evitando que cambie entre brazos pareados. Si `P(efecto > δ | datos) ≥ 0,95`, declarar relevante; si `P(efecto ≤ δ | datos) ≥ 0,95`, declarar no relevante; en otro caso, indeterminado. Para modelos con signos positivos y negativos, usar un criterio bilateral predefinido.
- Informar precisión, sensibilidad, falsos positivos, abstenciones e incertidumbre **por mundo**, con el denominador de canales directos, feeders y aislados. `26/27` directos correctos y solo cuatro nulos no bastan para evaluar la detección de canales nulos.
- **No iniciar aún** variantes simultáneas de selección de nulos, saturación y arrastre. Cuando M3 corregido esté estabilizado, estudiar primero contracción/ROPE y después familias flexibles, **cambiando un solo eje cada vez**. `spike-and-slab` queda como opción posterior si el objetivo es identificar nulidad exacta.

## 3. P1c — E14: correlación entre canales sin confusión causal

Autorizo el piloto `{0; 1,5; 3,0}` con 30 semillas pareadas por nivel y T = 104, **sujeto a una puerta de calidad de diseño**:

1. Validar en cada DAG que `Z→C` puede crear dependencia entre canales pero **no** existe `Z→Y` directo ni otro camino hacia `Y` que confunda el efecto de `C`; `D→Y` puede permanecer por conectividad **solo si** `D→C` y toda ruta oculta que vincule `D` a `C` son nulas, y `rho=0`.
2. Comprobar no solo la correlación alcanzada, sino **media, varianza y distribución de cada canal**, intensidad de señal, efecto causal verdadero, proporción señal/ruido, número de canales y condicionamiento de matrices. Subir `zc_coeff_range` puede cambiar simultáneamente la correlación y estas magnitudes: eso **no** es un experimento puro de colinealidad.
3. Si no puedes mantener razonablemente constantes los márgenes mediante la API del generador, presentar E14 como **«correlación inducida por Z con cambios de distribución»** y diseñar un control adicional con dependencia variable y márgenes fijados (por ejemplo, mediante innovaciones correlacionadas normalizadas, siempre que se respete el SCM). No ocultar el cambio de los márgenes.
4. Comparar modelos con y sin control por Z cuando sea pertinente: dado que `Z` no causa `Y` fuera de su efecto sobre `C`, no es por sí mismo un confusor que haya que ajustar. Añadirlo como regresor puede aumentar la varianza de los coeficientes; documentar también el efecto de incluirlo.
5. Fijar de antemano métricas: condición de la matriz de diseño, estabilidad de estimaciones, error de contribución directa, error de intervención, incertidumbre y predicción. La comparación principal es **dentro de los mundos pareados**.

Si el control de diseño no pasa, **no** ejecutes automáticamente los 90 mundos como prueba confirmatoria. Corrige el experimento y registra la nueva propuesta.

## 4. E10A: validaciones adicionales sin nueva campaña grande

El resultado es prometedor y respalda la distinción entre confusión causal y correlación observada. Antes de cerrarlo:

1. Documenta la **tabla completa de parámetros fijados** al variar por separado `D→C`, `D→Y` y `rho`, incluidos los valores de la **otra** arista de D. La frase «hay confusión si ambas aristas están presentes» debe comprobarse a partir del DAG y de las intervenciones concretas, no darse por supuesta.
2. Muestra, para cada contraste pareado, **el efecto causal verdadero, la estimación, el sesgo y el cambio de sesgo**, en unidades originales y normalizadas. Si `media|Y|` cambia entre niveles, usa además un **denominador fijado en el nivel de referencia**, para evitar cambios aparentes debidos solo al escalado.
3. Diferencia las **innovaciones primitivas compartidas** de las perturbaciones resultantes que cambian al variar `rho`. Verifica que el pareamiento no cambia factores ajenos al tratamiento experimental.
4. Añade, como **sensibilidad pequeña** y en mundos ya generados, una intervención local dentro del rango observado (p. ej. ±10 % donde exista soporte), además de `do_zero`. Este último puede implicar extrapolación fuerte para canales positivos. La sensibilidad no sustituye la métrica original registrada.
5. Cuantifica la variación de la correlación observada y la incertidumbre de los contrastes **por mundo y célula DAG**. Indica cuántas parejas quedan por cada contraste. No atribuyas significación causal al nivel de correlación por sí solo.
6. En la tabla de resultados, distingue `M0`, `M2` (ciego), `M2p` y `M2p_D` (privilegiados). La eliminación del sesgo por D en un modelo que **observa D** no prueba que un MMM ciego pueda identificar el mismo efecto.

No se autoriza por ahora ampliar E10A a T=52/208 ni a más semillas. Concluye primero el análisis de los 360 mundos ya existentes.

## 5. M2: auditoría, no modificación retrospectiva

Conserva los resultados del M2 original, incluidos el aumento de MAE (0,099→0,108) y el cambio de signo del sesgo tras la corrección w8. Es un resultado científico relevante: un error de preparación de datos podía compensar otro error de especificación.

Audita sin usar la verdad para elegir modelos: rejilla de adstock/saturación; frecuencia de formas elegidas; métricas predictivas de validación temporal; tratamiento del adstock entre train y test; escala y complejidad; diferencias por escenario, tipo de canal y T. Comprueba si la búsqueda está favoreciendo modelos complejos que predicen bien y atribuyen mal.

Si propones mejorar la búsqueda, entrega un diseño **M2v2** con rejilla y presupuesto fijados en desarrollo y un conjunto de evaluación separado. M2v2 no sustituye al M2 publicado.

## 6. Orden de ejecución y reglas de interrupción

**Primero:** control A/B/C de enmascaramiento y escalado; auditoría del piloto M3, selección registrada de hasta dos variantes de muestreo; decisión de continuar basada solo en convergencia y coste.

**En paralelo, sin MCMC adicional:** cierre analítico de E10A; auditoría de M2; puerta de calidad para E14.

**Después, solo si pasan los controles:** evaluación confirmatoria de M3 en mundos reservados; E14 pareado; ROPE y variantes de M3, una por una.

En ningún caso lanzar por iniciativa propia una nueva campaña completa de 600 mundos MCMC, el oracle M4 o E10B/E11/E12. Si la convergencia de M3 sigue siendo limitada, cerrar el resultado como inconcluso y continuar los experimentos rápidos sin ocultar el problema.

## 7. Entregables esperados

1. `reports/p1a_mask_vs_scale.md`: control A/B/C, priors y escala en unidades originales, prueba de que el contraste atribuido al enmascaramiento es realmente aislado.
2. `reports/p1a_m3_sampling_diagnostics.md`: diagnósticos y variantes, coste, selección sin verdad, mundos de desarrollo y posible solapamiento con muestras previas.
3. `reports/p1a_m3_confirmatory.md`: **solo si se supera la puerta de convergencia**; comparación pareada, cobertura, sesgo, canales nulos y validación fuera del desarrollo.
4. `reports/p1b_e10a_robustness.md`: configuración completa por mecanismo, contrastes no normalizados y normalizados con referencia fija, sensibilidad local y límites de identificación.
5. `reports/p1c_e14_design_gate.md` y, si procede, `reports/p1c_e14_results.md`.
6. `reports/m2_selection_audit.md`: diagnóstico del M2 original; especificación separada de M2v2 si se propone.
7. `reports/review_package_index_P1B.md`: índice y trazabilidad de versiones, pruebas, semillas, mundo, DAG, estimando y configuraciones.
8. Actualizar la **tabla de estado científico**, distinguiendo confirmado para el banco sintético, provisional, inconcluso y no ejecutado. Etiquetar de modo expreso las conclusiones sobre M3 de v1 y v1.1 como anteriores a la corrección del ajuste.

### Respuesta que espero de ti al terminar este encargo

Resume: (i) cuánto del cambio de M3 proviene del enmascaramiento frente al escalado, (ii) qué tasa de convergencia logras sin cambiar el modelo, (iii) si hay evidencia fiable de mejora de cobertura en **mundos válidos pareados**, (iv) qué demuestra E10A sin depender de `do_zero`, (v) si E14 puede llamarse «multicolinealidad pura» o solo «correlación inducida por Z», y (vi) si M2 requiere una segunda versión o basta mantenerlo como caso de contraste.

**Criterio general:** conclusiones defendibles y replicables antes que más ajustes. Cuando un resultado no esté suficientemente sustentado, informa «no concluyente» y conserva los datos.
