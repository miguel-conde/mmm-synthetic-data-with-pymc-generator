# Respuesta breve al diseñador tras P0 (v1.2)

**Fecha:** 2026-11-06 · **Responde a:** [RESPUESTA_AL_AGENTE_MMM_V1_2.md](RESPUESTA_AL_AGENTE_MMM_V1_2.md) · **Índice:** [../reports/review_package_index.md](../reports/review_package_index.md)

Entregables P0:
- [quality_gate_v1_2.md](../reports/quality_gate_v1_2.md)
- [m3_coverage_audit.md](../reports/m3_coverage_audit.md)
- [e09_policy_audit.md](../reports/e09_policy_audit.md)
- [scientific_status_v1_2.md](../reports/scientific_status_v1_2.md)
- [review_package_index.md](../reports/review_package_index.md)

Integridad:
- v1 y v1.1 congeladas con SHA-256; 0 diferencias no explicadas. Un fichero de código, `bayes.py`, evolucionó; su versión v1.1 exacta está reconstruida y verificada en `reports/v1_1/code_snapshot/`.
- Las 87 pruebas pasan.
- **No se ha ejecutado MCMC.** El único re-cálculo son modelos rápidos en los 150 mundos F2, justificado por un error demostrado (abajo).

## 0. Error de protocolo encontrado en P0 (afecta a v1 y v1.1)

Todos los modelos se **ajustaron** desde la semana 0. Ahí su adstock arranca con historia cero, mientras el generador tiene 8 semanas previas de *burn-in* no guardadas. La **evaluación** ya excluía esas semanas; el ajuste no.

Demostración privilegiada (OLS con transformaciones verdaderas y base verdadera como *offset*): sesgo de −0,036 de media\|y\| ajustando desde la semana 0 frente a +0,004 desde la semana 8. Hay un test de regresión que lo comprueba.

Re-ajuste de los modelos rápidos en `[8, n_train)` (150 mundos):

| Modelo | Error con ajuste desde semana 0 | Error desde semana 8 | Comentario |
|---|---|---|---|
| M2p (forma verdadera, privilegiado) | 0,042 | 0,016 | sesgo de −0,039 a +0,001 |
| OLS / Ridge con canales crudos | sin cambio | sin cambio | — |
| M2 | 0,079 | 0,087 | ajustar en *burn-in* compensaba parte de su sobreajuste |

M3 no puede corregirse descartando filas, porque PyMC-Marketing reinicia el adstock en la primera fila. Necesita una verosimilitud enmascarada; el código ahora rechaza ese caso en lugar de dar un resultado erróneo.

## (i) ¿La cobertura del 33 % se concentra en nulos o afecta también a directos?

**A ambos, por razones distintas.**

- **Feeders y aislados:** cobertura 0 % por construcción. La posterior de una contribución con `HalfNormal × logística` es > 0 casi con seguridad y un intervalo de cola igual no contiene el 0 puntual (C1). No dice nada sobre la calibración de canales activos.
- **Directos, ajustes válidos (V3, 31 mundos):** cobertura 95 % de 0,40 [0,33; 0,47]; en los 23 ajustes válidos de los 35 mundos no usados para elegir V3, 0,41. Por escenario va de 0,27 (S0) a 0,47 (S1). S2 tiene solo 2 ajustes válidos y no es representativo.
- **V0 frente a V3** en los 7 mundos válidos en ambas: sin diferencia detectable (−0,05 [−0,17; 0,06]).

## (ii) ¿Qué sesgos concretos quedan en los directos?

Sesgo negativo, constante por canal, de −0,034 [−0,042; −0,026] de media\|y\|. Es **casi idéntico al de M2p ajustado desde la semana 0** (−0,036) y desaparece en M2p ajustado desde la semana 8 (+0,004).

- Su patrón también encaja con el artefacto: es máximo con arrastre Weibull (−0,053) y nulo sin arrastre (−0,002).
- **Retiro mi lectura de v1.1** («el sesgo es de forma funcional»): comparaba con un M2p contaminado por el mismo artefacto.
- **Estado: inconclusive** hasta reajustar M3 con verosimilitud enmascarada. La infra-cobertura de los directos puede deberse en gran parte a este sesgo.

## (iii) ¿Qué parte de E09 es realizable sin verdad?

**Familia principal (`all_channels_clamped_policy`): toda.**
- Las políticas usan solo el modelo, y el presupuesto se cumple por construcción (violación máxima 0).
- El óptimo guardado se confirma con multi-arranque en 45/45 mundos (11/11 arranques convergen al mismo valor, mejora máxima 1e-9).

**Familia secundaria (`selected_channels_do_policy`): nada que mejore el plan actual.**
- Tal como las proponen los modelos, las políticas son infactibles en 17–18 de 18 mundos (desviación media absoluta de 1,3–1,6 %).
- La regla aplicable sin verdad (proyección por regresión de los descendientes sobre los accionables, usando solo datos observados) es factible en el 78–89 % de los mundos, pero encoge la reasignación (\|m−1\| de 0,42 a 0,085). Su valor queda en torno al del plan actual (−0,2 % a +0,2 %).
- La normalización con el SCM verdadero queda etiquetada `oracle_ex_post_budget_equalization` y sin ranking.
- **La familia secundaria queda exploratoria.**

## (iv) ¿Cambia la conclusión predicción-atribución tras corregir azar y agrupación?

No de signo, sí de fuerza.

| Medida | v1.1 (600 mundos, ajuste desde semana 0) | v1.2 (150 mundos F2, ajuste desde semana 8) |
|---|---|---|
| Coincidencia del mejor predictor con el mejor atribuidor | 26,7 % [23 %; 30 %] | 30,7 % [23 %; 39 %] |
| Spearman entre rankings | 0,18 [0,13; 0,23] | 0,17 [0,07; 0,27] |

- Referencia de azar: 25 % (4 métodos, sin empates).
- Spearman por escenario (v1.2): de 0,02 (S1) a 0,37 (S2).
- **Redacción:** hay una asociación positiva débil entre rankings; **no hay evidencia clara de que el mejor predictor sea el mejor atribuidor más allá del azar**.
- Predicción frente a decisión: correlación dentro de mundo de 0,095 [−0,05; 0,23], compatible con relación nula o positiva débil-moderada.
- En S0 (una sola célula DAG) la generalización es solo a esa receta.

## (v) Tres decisiones para arrancar P1

Protocolo en borrador: [protocolo_v1_2_P1.md](protocolo_v1_2_P1.md).

1. **Ventana de ajuste.** ¿Aprueba fijar `[8, n_train)` como estándar de todos los ajustes y, por tanto: (a) implementar y validar la verosimilitud enmascarada de M3 como prerrequisito de P1a (validación en el control lineal E02); (b) re-ejecutar con la ventana corregida los modelos rápidos de F3, E10A y las políticas de E08/E09 (sin MCMC, ≈ 3–4 h de CPU)?
2. **Nulos en P1a.** ¿*Spike-and-slab* con indicador marginalizado (permite P(β = 0); modelo propio, ya no es el MMM estándar de PyMC-Marketing) o contracción continua + ROPE con δ = 0,005 × media\|y\| por semana, fijado antes de mirar resultados?
3. **Alcance de P1b/P1c.** ¿Acepta 40 pares por nivel a T=104 para E10A? La potencia del piloto detecta diferencias de 0,005 en OLS/M2p; M2 es demasiado ruidoso y se informaría sin pretensión de potencia. ¿Y el diseño E14 con `Z` observado sin `Z→Y`, 30 pares × 3 niveles de `zc_coeff_range`, en ese orden y antes de E10B?
