# Métodos, hipótesis y umbrales pre-registrados

Fijado el 2026-11-05 **antes de ejecutar ningún modelo**. No se modifica a posteriori; los resultados se escriben aparte en `reports/benchmark_report.md`.

## Hipótesis (copiadas del programa, §2)

| Código | Hipótesis | Prueba en este banco |
|---|---|---|
| H1 | Buen ajuste/pronóstico de `Y` no garantiza recuperar contribuciones | Correlación de Spearman entre ranking de RMSE de test y de error de contribución, por mundo |
| H2 | Más semanas mejoran la recuperación media sin garantizar identificación | Error de contribución por `T` y escenario |
| H3 | La confusión latente deteriora a modelos que no la representan | S1 vs S0; M2p vs M2p_D (privilegiado con `D`) |
| H4 | Controles ayudan pero mal ajustados sesgan | S2: M2 con controles vs M2 sin controles (`M2_noZ`) |
| H5 | Correlación entre canales reduce estabilidad | Error vs correlación media entre canales observada (E14 parcial) |
| H6 | Corregir forma funcional ayuda pero no arregla confusión | M0/M1 vs M2 vs M2p en S0 y S1 |
| H7 | `C→C` hace divergir atribución observada y efecto `do` del canal origen | S3: atribución observada del canal origen (0 si `g_cy=0`) vs `do` total |
| H8 | Árboles predicen igual o mejor sin validez causal | RMSE test M5/M6 vs regresiones; árboles sin contribución causal |
| H9 | Intervalos de modelos mal especificados infra-cubren; oracle también puede fallar | Cobertura 50/80/95 de M3 y M4 |
| H10 | Mejor predictor ≠ mejor decisión | Regret de políticas por modelo (E09) |
| H11 | Cambios de prior degradan distinto según método | E10 — no ejecutado en v1 |

## Umbrales y reglas fijadas antes de ver resultados

- **Falsa atribución a canal nulo** (canal con `g_cy = 0`, respuesta observada verdadera idénticamente 0): `|Σ_t ĉ_{k,t}| / Σ_t |y_t| > 0.02` en la ventana de evaluación.
- Métricas de atribución normalizadas por `mean_t |y_t|` de la misma ventana; se reportan también absolutas.
- Unidad de repetición: el **mundo**. Intervalos del 95 % por bootstrap de mundos (2000 remuestreos, semilla fija); comparaciones emparejadas solo sobre la intersección de mundos con ambos modelos `ok`.
- Diagnósticos MCMC «válidos»: `max R-hat ≤ 1.01`, `min ESS bulk ≥ 400` (≥ 100 en el piloto de 2 cadenas, marcado), 0 divergencias. Ajustes no válidos se reportan con su estado y se excluyen de cobertura «fiable», mostrándose aparte.
- Contrafactual validado solo si: intervención nula reproduce `Y` con `max|Δ| ≤ 1e-9`; canal sin ruta a `Y` tiene efecto `≤ 1e-9`; intervención en semana `s` no cambia `Y_{t<s}`; en mundos con `C→C` el canal descendiente cambia al intervenir el ascendente.

## Métodos implementados (detalle en código)

| ID | Clase | Información | Notas |
|---|---|---|---|
| N0/N1 | `NaiveLast`, `NaiveMean` | ciega | referencias de predicción, sin contribuciones |
| M0 | `OLSRaw` | ciega | canales crudos + `Z` + tendencia + Fourier anual (2 términos) |
| M1 | `RidgeRaw` | ciega | igual que M0, estandarizado con estadísticas de train, `α` por validación temporal |
| M2 | `EngineeredRegression` | ciega | adstock geométrico normalizado (`l_max=8`) + saturación `x/(x+κ)` por canal, búsqueda por coordenadas en validación temporal; OLS |
| M2_noZ | idem sin controles | ciega | variante de especificación (H4) |
| M2p | `PrivilegedTrueTransform` | **privilegiada** | transformaciones verdaderas del generador + OLS; fuera de ranking |
| M2p_D | idem + `D` latente | **privilegiada** | control metodológico de confusión (E03) |
| M3 | `PyMCMarketingMMM` | ciega | `GeometricAdstock(l_max=8)` + `LogisticSaturation`, controles + tendencia, Fourier anual 2, NUTS (nutpie) |
| M4 | `OracleStructureKnownPlugin` | **privilegiada** | `pg.sample_oracle`, latentes marginalizadas |
| M5 | `XGBoostPredictor` | ciega | `xgboost-cpu`, lags/medias móviles causales, validación temporal |
| M6 | `LightGBMPredictor` | ciega | ídem |
| M7–M10 | DML, Causal Forest, MMM neuronal, MLP | — | **no ejecutados en v1** (ver estado) |
