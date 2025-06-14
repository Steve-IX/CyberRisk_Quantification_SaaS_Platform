"""
CyberRisk Core - Monte Carlo Simulation and Optimization for Cyber Risk Quantification

A Python library for quantitative cyber risk analysis using Monte Carlo methods,
designed for NIS2 and CSRD compliance reporting.
"""

from .risk_metrics import Task1 as calculate_ale
from .prob_model import Task2 as calculate_conditional_probabilities  
from .control_optimizer import Task3 as optimize_controls

# Version info
__version__ = "1.0.0"
__author__ = "Steve-IX"

# Public API
__all__ = [
    "calculate_ale",
    "calculate_conditional_probabilities", 
    "optimize_controls"
] 