"""
apps/claims/pipeline.py

Thin shim — delegates to apps.fraud.service.run_fraud_pipeline.
Kept for backward compatibility with existing imports in claims/tasks.py.
"""
from apps.fraud.service import run_fraud_pipeline  # noqa: F401 — re-export

__all__ = ['run_fraud_pipeline']
