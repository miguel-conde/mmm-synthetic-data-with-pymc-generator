from __future__ import annotations

from .base import Estimator
from .bayes import OracleStructureKnownPlugin, PyMCMarketingMMM
from .linear import (
    EngineeredNoControls,
    EngineeredRegression,
    NaiveLast,
    NaiveMean,
    OLSRaw,
    PrivilegedTrueTransform,
    PrivilegedTrueTransformWithLatent,
    RidgeRaw,
)
from .trees import LightGBMPredictor, XGBoostPredictor

REGISTRY: dict[str, type[Estimator]] = {
    cls.model_id: cls
    for cls in (
        NaiveLast,
        NaiveMean,
        OLSRaw,
        RidgeRaw,
        EngineeredRegression,
        EngineeredNoControls,
        PrivilegedTrueTransform,
        PrivilegedTrueTransformWithLatent,
        PyMCMarketingMMM,
        OracleStructureKnownPlugin,
        XGBoostPredictor,
        LightGBMPredictor,
    )
}


def make_model(model_id: str, **kwargs) -> Estimator:
    return REGISTRY[model_id](**kwargs)
