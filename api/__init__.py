"""
CyberRisk API Package

FastAPI-based REST API for cyber risk quantification platform.
Provides endpoints for Monte Carlo simulations, risk optimization,
and compliance reporting.
"""

from .main import app

__version__ = "1.0.0"
__all__ = ["app"] 