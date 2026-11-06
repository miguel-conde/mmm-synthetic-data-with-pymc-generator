# Protocolo P1 (v1.2) — borrador para decisión del diseñador

**Estado:** no ejecutado. Se fija cuando el diseñador resuelva las decisiones de [respuesta_v1_2_al_disenador.md](respuesta_v1_2_al_disenador.md) §5. Todo en `configs/v1_2_*`, `runs/v1_2_*`, `reports/v1_2/`. Ningún informe previo se reescribe.

## 0. Prerrequisito común: ajuste sin filas de *burn-in*

P0 demostró que ajustar desde la semana 0 sesga los coeficientes de medios (ver [../reports/scientific_status_v1_2.md](../reports/scientific_status_v1_2.md) §2). Todos los ajustes de P1 usarán la ventana `[8, n_train)` y conservarán las semanas 0–7 como historia de tratamiento.

- Modelos rápidos: ya implementado (`fit_scope: train_after_warmup`).
- **M3 (PyMC-Marketing):** requiere verosimilitud enmascarada. El modelo recibe todas las semanas de `X` (adstock con historia) y la verosimilitud solo las semanas ≥ 8.
  - **Implementación a validar:** construir el modelo con todas las filas de `X` e `y` y sustituir la observación por una verosimilitud sobre `y[8:]` vía `model.observe`/`pm.Data` con máscara. También se puede usar `include_last_observations` en una segunda llamada si la API lo permite.
  - **Criterio de aceptación:** en un mundo lineal (E02, OLS correcto) la contribución de M3 con verosimilitud enmascarada no tiene sesgo detectable frente a OLS con la misma ventana. Si la API no lo permite sin modificar PyMC-Marketing, se documenta como arquitectura propia (deja de ser el MMM estándar).

## P1a — Especificación de M3 en dos ejes

| Elemento | Definición |
|---|---|
| Hipótesis | (i) El sesgo constante de los canales directos se debe sobre todo a la forma funcional. (ii) La infra-cobertura en canales sin `C→Y` se debe a una posterior estrictamente positiva. |
| Estimandos | `historical_observed_path_response` (por canal-semana, resumido por canal y mundo); detección de efecto nulo por canal (clasificación). |
| Verdad | `contributions_observed`; rol de canal (`direct` / `feeder` / `isolated`). |
| Variantes | **R** = V3 con verosimilitud enmascarada (referencia congelada). **N** = R + mecanismo de nulos. **F** = R + familias `WeibullPDFAdstock` + `HillSaturation` (las de PyMC-Marketing más cercanas al generador). **NF** = N + F, solo si el coste lo permite. |
| Mecanismo de nulos (decisión 2) | (a) *spike-and-slab* con indicador marginalizado por canal (mezcla de dos componentes sobre `beta`, sin variables discretas para NUTS): permite P(β = 0). Implica modelo propio. (b) Contracción continua (horseshoe regularizado sobre `beta`) + regla ROPE: canal «sin efecto relevante» si P(contribución media < δ) ≥ 0,9, con δ fijado **antes**: δ = 0,005 × media\|y\| por semana (umbral de negocio sugerido). No prueba nulidad exacta. |
| Mundos | Desarrollo: 10 mundos nuevos estratificados (2 por escenario, réplicas 10–11 de F2, T=104), **disjuntos** de los 45 de evaluación. Evaluación: los 45 mundos M3 de F2. Las 35 de evaluación no usadas en v1.1 se informan además por separado. |
| Criterios congelados (desarrollo, sin verdad) | Convergencia estricta (R-hat ≤ 1,01, ESS ≥ 400, 0 divergencias) en ≥ 8/10 mundos de desarrollo y coste ≤ 5 min/ajuste. Si no se cumple: ajustar `target_accept`/priors solo con diagnósticos y repetir. |
| Métricas primarias | Error y sesgo de contribución en canales directos; cobertura 50/80/95 % solo en ajustes válidos; para nulos, tasa de falsos positivos y sensibilidad/precisión de detección; todo por rol, escenario y T. |
| Modelos e información | Solo ciegos; M2p como referencia privilegiada fuera de ranking. |
| Coste | ≈ 1–2 min/ajuste (V3) × 4 variantes × (10 + 45) mundos ≈ 4–7 h de CPU. Piloto: 10 de desarrollo, ≈ 1 h. |
| Interrupción | Se detiene antes de la evaluación si ninguna variante cumple el criterio de desarrollo. |

## P1b — E10A ampliado: confusión con dos mecanismos

| Elemento | Definición |
|---|---|
| Hipótesis | La confusión estructural (`D→C` con `D→Y`) y la correlación de innovaciones (`rho`) cambian el error de contribución observada y del efecto `do` implicado de modelos ciegos. |
| Factores | `E10A_D`: `dc_coeff_range` ∈ {0; 0,25; 0,5}, con `dy_coeff_range` fijo; variante adicional `dy_coeff_range` ∈ {0,15; 0,45} con `dc` fijo. `E10A_rho`: `confounding_strength_range` ∈ {1e-6; 0,3; 0,6}. Mundos pareados: misma semilla ⇒ mismo DAG, parámetros e innovaciones salvo el factor (verificado por test). «Mismo DAG» no implica el mismo efecto causal: se informa el efecto `do_zero` verdadero por nivel. |
| Potencia | Del piloto (DE de la diferencia pareada): OLS 0,003–0,009 y M2p 0,006–0,014, así que 25–60 pares detectan diferencias de 0,005 con 80 % de potencia. M2: DE 0,03–0,06, inalcanzable con tamaños moderados (se informa con su IC, sin pretender potencia). Propuesta: **40 pares por nivel**, T=104; T=52 y 208 solo después. |
| Modelos | M0, M1, M2, M2_noZ (ciegos), con ajuste desde la semana 8. M2p, M2p_D como control privilegiado (nunca en ranking ciego). |
| Estimandos | Atribución *observed-path* (sesgo, error) y efecto `do_zero` implicado frente al verdadero. Se distinguen sesgo directo observado y sesgo de intervención. Se declara si el efecto `do` no es identificable sin `D` aunque mejore la predicción. |
| Coste | Modelos rápidos + motor `do`: ≈ 30 s/mundo × 240 mundos ≈ 2 h. |

## P1c — E14: multicolinealidad sin confusión causal

| Elemento | Definición |
|---|---|
| Hipótesis | La correlación entre canales inducida por una causa observada `Z` sin `Z→Y` reduce la estabilidad de la atribución sin sesgarla, al contrario que la confusión estructural. |
| Diseño | Escenario propio: 4 canales, 1 `Z` con aristas `Z→C` a todos los canales, `zy = 0`, `dc = cc = 0` (sin `D→C`, sin `C→C`), `D→Y` permitido solo como base. Niveles de correlación vía `zc_coeff_range` ∈ {(0,0); (0,15; 0,15); (0,3; 0,3)} con mundos pareados. Se verifica en cada mundo el DAG (sin sendas alternativas `C←…→Y` salvo a través de `Z` observado y sin efecto), la correlación lograda, el número de condición y el VIF. |
| Señal | Se mantienen `beta_additive_range` y el número de canales; se informa la fracción de medios en `y` por nivel. |
| Métricas | Error y varianza entre mundos de la atribución, signo de los coeficientes, cobertura de M3 en válidos (si P1a está validado) y comparación con E10A_D a la misma correlación lograda. |
| Coste | 30 pares × 3 niveles, modelos rápidos ≈ 1 h. M3 solo en 10 pares si P1a lo valida. |

## Común

Registro previo de cada experimento antes de ejecutarlo. Rankings sobre la misma intersección de mundos. Intervalos por mundo. Hashes de código y entorno en cada `manifest.json`. Sin cambio de versión del generador.
