"""
apps/claims/pipeline.py

Thin shim — delegates to apps.fraud.service.run_fraud_pipeline.
Replaced the duplicated and simpler version to prevent circular imports and 
ensure the 6-layer fraud model is the single source of truth.
"""
from apps.fraud.service import run_fraud_pipeline

__all__ = ['run_fraud_pipeline']
