This workspace is used along with the repository [pymc-generator](https://github.com/pymc-labs/pymc-generator) to learn about this synthetic data generator library for MMM.

Always use uv to install packages and run code. You have a skill about how to use uv, use it.

Also use it to set up the workspace virtual environment and project configuration.

## `pymc-generator` reference documentation

Docs root: https://github.com/pymc-labs/pymc-generator/tree/main/docs (rendered site: https://pymc-labs.github.io/pymc-generator/).

- **Version caveat.** The project pins `pymc-generator` at commit `fb9549d78f0515d89c739c6d4c9f3a29d4a47c26` (`pyproject.toml`), while the docs track `main`. If a doc and the installed code disagree, trust the installed source in `.venv/lib/python3.13/site-packages/pymc_generator/`, or the docs at the pinned commit: replace `main` with the commit hash in the URL.
- **Fetching pages.** Use the raw URL, `https://raw.githubusercontent.com/pymc-labs/pymc-generator/main/docs/<path>`. GitHub tree pages truncate directory listings.
- **Consult the docs before:** using a generator API you have not verified; changing world generation (scenarios, overrides, edge budgets); interpreting a ground-truth quantity (contributions, baseline, burn-in); or using the oracle.

| Need | Consult |
|---|---|
| Overview, install, first world | `index.md`, `getting-started.md` |
| The SCM: nodes (treatments C, covariates Z, latents D), edges, mechanisms, carryover/saturation families | `guide/foundation.md` |
| Sampling one world, burn-in, seeds, `SCM` object, replay | `guide/worlds.md`, `reference/sampling.md`, `reference/world-model.md` |
| Exact additive decomposition: `contributions_observed`, baseline, indirect effects (ground truth for attribution) | `guide/decomposition.md` |
| Named scenarios / presets (`direct_only`, `confounded_treatment`, …) | `guide/scenarios.md`, `reference/scenarios.md` |
| Prior / config knobs (`make_scm_prior`, `SCMPrior`: edge budgets, coefficient ranges, `confounding_strength_range`, `carryover_burn_in`) | `reference/config.md` |
| Input trajectories for treatments/covariates (hf, pulses, shocks, flighting) | `guide/trajectories.md` |
| Corpora: many worlds, `sample_prior_predictive`, `DataGenerator`, save/load, active-count coverage | `guide/corpus.md`, `reference/corpus.md` |
| Corpus quality checks | `guide/corpus-quality.md` |
| Posterior oracle (`sample_oracle`, `OracleSamplingConfig`, `build_oracle_model`, receipts, health) | `guide/oracle.md`, `reference/world-model.md` |
| Data diagnostics: dependence, VIF/collinearity, dynamics, contribution hierarchy | `guide/data-diagnostics.md`, `reference/diagnostics.md` |
| Signal diagnostics (response warm-up, kernel support) | `reference/signal.md` |
| Outcome and contribution magnitudes across worlds | `reference/outcomes.md` |
| World descriptors, comparing or stratifying worlds, nearest worlds | `guide/world-descriptors.md`, `reference/descriptors.md` |
| Audit bundles and text descriptions (`write_scm_bundle`, `describe_scm`) | `guide/bundles.md`, `reference/bundles.md`, `reference/describe.md` |
| Plots | `reference/viz.md` |
| Full public API and import surface | `reference/index.md` |
| Worked examples: end-to-end tour, MMM recovery case study, linear recovery | `examples/index.ipynb`, `examples/simple-model.ipynb`, `examples/linear-recovery.ipynb`, `examples/map-recovery-pilot.md` |

The generator has no public `do()` intervention API. This project's engine in `mmm_benchmark/interventions.py` uses private graph internals and is labelled `research_validated_private_api`. Do not assume the docs cover it.