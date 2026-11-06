# Diagnóstico MCMC (D4) — v1.1

Criterio vinculante (D4): todas las variables libres con R-hat (rank) ≤ 1,01, ESS bulk ≥ 400 y 0 divergencias. Fuera de él, `nonconverged`. El criterio piloto (ESS ≥ 100) solo es exploratorio.

## 1. Submuestra y variantes (registradas en [docs/revision_v1_1.md](../docs/revision_v1_1.md) §3.1)

10 mundos M3 de F2 que no cumplían el criterio estricto en v1 (los dos primeros por `world_id` de cada escenario; selección sin usar la verdad). Las variantes V0–V2 cambian solo `target_accept`, con 4 cadenas × (1000 + 1000), nutpie y la misma semilla por mundo.

## 2. Resultados V0–V2 (solo diagnósticos del muestreador)

| Variante | `target_accept` | Ajustes estrictamente convergidos | Con alguna divergencia | Divergencias totales | R-hat máx. | ESS mín. | s/ajuste (mediana) |
|---|---|---|---|---|---|---|---|
| V0 (= v1) | 0,90 | 0/10 | 8/10 | 46 | 1,017 | 330 | 17 |
| V1 | 0,95 | 2/10 | 7/10 | 25 | 1,024 | 226 | 18 |
| V2 | 0,99 | 7/10 | 1/10 | 2 | 1,015 | 250 | 29 |

Al re-ejecutar V0 con la misma semilla, ningún mundo converge, igual que en v1, aunque las cifras exactas difieren ligeramente (`v1_1_m3_diag` frente a `core`).

## 3. Geometría posterior (V0)

- **Arista de identificabilidad saturación–escala.** En los 10 mundos, la correlación posterior entre `log(saturation_lam)` y `log(saturation_beta)` del canal más afectado va de 0,75 a 0,99 (mediana ≈ 0,94). Con `LogisticSaturation` y tratamientos en el tramo casi lineal, `logistic(lam·x) ≈ lam·x/2`, así que solo el producto `beta·lam` está bien identificado.
- **Variables peor muestreadas:** `saturation_lam` / `saturation_beta` (peor R-hat en 22 de 30 ajustes) y, en S2/S3, `intercept_contribution`, correlacionado con la escala de medios.
- **Arrastre.** `adstock_alpha` acumula un 8–36 % de masa por debajo de 0,05: la prior `Beta(1, 3)` permite colapsar el arrastre, sin problema de muestreo asociado.
- **Divergencias.** Se concentran donde `lam` es extremo (colas de la arista). `target_accept = 0,99` reduce el paso y casi las elimina, a cambio de ~1,7× más tiempo.

## 4. Registro de V3 (antes de ejecutarla)

Fijada el 2026-11-05 a partir de §3, **sin consultar ninguna métrica frente a la verdad**:

- **V3 = V2 (`target_accept = 0,99`) + prior `saturation_lam ~ Gamma(α = 6, β = 2)`**, en lugar del valor por defecto `Gamma(3, 1)`. Mantiene la media a priori (3) y reduce la desviación típica de 1,73 a 1,22, quitando masa de las colas de la arista `lam–beta` donde aparecen las divergencias. `saturation_beta ~ HalfNormal(2)` sin cambios.
- **Riesgo declarado:** una prior más concentrada puede sesgar `lam` cuando la saturación verdadera está lejos de la media a priori. Se evaluará en la comparación con la verdad, pero **no** se usará para elegir variante.
- **Regla de selección (pre-registrada):** mayor fracción de ajustes estrictamente convergidos en los 10 mundos; en caso de empate, menor tiempo mediano.

<!-- V3-RESULTS -->

## 5. Resultado de V3 y selección

| Variante | Estrictamente convergidos | Con divergencias | R-hat máx. | ESS mín. | Corr. mediana `log lam`–`log beta` |
|---|---|---|---|---|---|
| V0 | 0/10 | 8/10 | 1,017 | 330 | 0,94 |
| V1 | 2/10 | 7/10 | 1,024 | 226 | 0,94 |
| V2 | 7/10 | 1/10 | 1,015 | 250 | 0,94 |
| **V3** | **9/10** | **0/10** | 1,011 | 505 | 0,83 |

Por la regla pre-registrada (mayor fracción de ajustes estrictamente convergidos), **se elige V3**. El único fallo restante (`S2_promo_drives_treatment_T104_r02`) tiene R-hat 1,011, justo por encima del umbral. La prior más concentrada reduce la correlación de la arista, como se esperaba.

**Coste:** V3 se ejecutó con dos cadenas de experimentos más compitiendo por la CPU (mediana 116 s/ajuste frente a 29 s de V2, que se ejecutó sin competencia), así que esos tiempos no son comparables. El coste en los 45 mundos se informa en el informe v1.1.

V3 se aplica a los 45 mundos M3 de F2 (`configs/v1_1_m3.yaml`) y a las réplicas 0–2 del control lineal E02. La comparación con la verdad (error y cobertura) aparece en el informe v1.1 y **no** se ha usado para elegir.

## 6. V3 en los 45 mundos M3 de F2

| | v1 (V0) | v1.1 (V3) |
|---|---|---|
| Estrictamente convergidos | 11/45 (24 %) | **31/45 (69 %)** |
| Con alguna divergencia | 62 % | 2 % |
| Por escenario (V3) | — | S0 56 %, S1 100 %, S2 22 %, S3 78 %, S4 89 % |
| s/ajuste (mediana; con otras ejecuciones compitiendo) | 20 | 70 |
| Error de contribución histórica (mediana) | 0,040 | 0,039 (diferencia emparejada −0,0001 [−0,0011; 0,0010]) |

S2 (`promo_drives_treatment`) sigue siendo el escenario con peor geometría.

## 7. Cobertura: no es (solo) un problema de convergencia

Cobertura empírica de las contribuciones *observed-path*, ventana `historical_in_sample_fit`, V3, 45 mundos (`reports/tables_v1_1/m3_v3_coverage_by_channel.csv`):

| Ajuste | Rol del canal | Canal-mundos | Cobertura 95 % | Anchura media | MAE | \|sesgo medio\| |
|---|---|---|---|---|---|---|
| válido | directo | 117 | 0,40 | 0,55 | 0,46 | 0,46 |
| válido | feeder | 18 | **0,00** | 0,22 | 0,07 | 0,07 |
| válido | aislado | 12 | **0,00** | 0,25 | 0,10 | 0,10 |
| no válido (descriptivo) | directo | 54 | 0,55 | 0,64 | 0,39 | 0,39 |

1. **Canales sin `C→Y`:** la cobertura es 0 por construcción. `saturation_beta ~ HalfNormal` y la saturación logística son estrictamente positivas, así que el intervalo de la contribución nunca contiene el 0 verdadero. Es una incompatibilidad entre el soporte de la prior y el estimando, no un fallo de muestreo.
2. **Canales directos:** el error es casi todo sesgo constante por canal (\|sesgo medio\| / MAE = 0,99), no ruido semanal. Los intervalos son ~1,3 × el MAE de ancho pero están centrados fuera de la verdad.
3. **Por familia verdadera** (canales directos): cobertura 0,65 sin arrastre, 0,47 geométrico y 0,35 Weibull; por saturación, de 0,61 (hill) a 0,31 (root). Encaja con un desajuste de forma funcional (adstock geométrico + logística frente a las familias del generador), que el intervalo posterior no recoge porque solo refleja incertidumbre paramétrica *dentro* de esa forma.
4. **Sesgo de selección:** los ajustes no válidos cubren más (0,55) que los válidos (0,40); evaluar solo convergidos no es neutro.

**Conclusión provisional:** la infra-cobertura de M3 es sobre todo de especificación (forma funcional y soporte de la prior), no de convergencia. Mejorar la convergencia (V3) no la corrige. Lo que convendría probar no es «más muestras», sino priors que admitan efecto nulo (*spike-and-slab* o *horseshoe* sobre `beta`) y familias de arrastre/saturación más flexibles. Esto queda propuesto para v2.
