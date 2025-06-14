"""
Background Tasks Module - Async simulation processing

This module handles background processing of Monte Carlo simulations
and other long-running tasks for the CyberRisk SaaS platform.
"""

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime
import traceback
import numpy as np

from cyberrisk_core import calculate_ale, calculate_percentiles, format_currency
from .database import update_simulation_status, update_simulation_run, update_optimization_run

logger = logging.getLogger(__name__)


async def run_simulation_task(run_id: str, parameters: Dict[str, Any], org_id: str):
    """
    Background task to run Monte Carlo simulation with enhanced database integration.
    
    Args:
        run_id: Unique simulation run identifier
        parameters: Simulation parameters
        org_id: Organization ID
    """
    logger.info(f"Starting simulation task {run_id}")
    
    try:
        # Extract simulation parameters
        asset_value_min = parameters.get('asset_value_min', 50000)
        asset_value_mode = parameters.get('asset_value_mode', 150000)
        asset_value_max = parameters.get('asset_value_max', 500000)
        occurrence_counts = parameters.get('occurrence_counts', [0, 1, 2, 3, 4, 5])
        occurrence_probabilities = parameters.get('occurrence_probabilities', [0.3, 0.4, 0.2, 0.06, 0.03, 0.01])
        iterations = parameters.get('iterations', 10000)
        
        # FAIR analysis parameters  
        flaw_a_mu = parameters.get('flaw_a_mu', 9.2)
        flaw_a_sigma = parameters.get('flaw_a_sigma', 1.0)
        flaw_b_scale = parameters.get('flaw_b_scale', 5000)
        flaw_b_alpha = parameters.get('flaw_b_alpha', 2.5)
        
        # Threshold parameters
        threshold_point1 = parameters.get('threshold_point1', 100000)
        threshold_point2 = parameters.get('threshold_point2', 50000)
        range_point3 = parameters.get('range_point3', 20000)
        range_point4 = parameters.get('range_point4', 100000)
        
        # Scenario information
        scenario_name = parameters.get('scenario_name', 'Cyber Risk Assessment')
        
        # Import risk analysis modules
        from cyberrisk_core.risk_metrics import RiskAnalyzer
        from cyberrisk_core.prob_model import ProbabilityModel
        
        # Initialize components
        risk_analyzer = RiskAnalyzer()
        prob_model = ProbabilityModel()
        
        # Run triangular distribution analysis for asset values
        triangular_samples = risk_analyzer.sample_triangular_distribution(
            asset_value_min, asset_value_mode, asset_value_max, iterations
        )
        
        # Calculate ALE using FAIR methodology
        ale = risk_analyzer.calculate_ale(
            triangular_samples,
            occurrence_counts,
            occurrence_probabilities,
            iterations
        )
        
        # Run probability analysis
        flaw_a_samples = prob_model.sample_lognormal(flaw_a_mu, flaw_a_sigma, iterations)
        flaw_b_samples = prob_model.sample_gamma(flaw_b_scale, flaw_b_alpha, iterations)
        
        # Calculate conditional probabilities
        prob1 = prob_model.conditional_probability(
            flaw_a_samples, flaw_b_samples, threshold_point1
        )
        prob2 = prob_model.conditional_probability(
            flaw_a_samples, flaw_b_samples, threshold_point2
        )
        prob3 = prob_model.conditional_probability_range(
            flaw_a_samples, flaw_b_samples, range_point3, range_point4
        )
        
        # Calculate risk metrics
        mean_triangular = float(np.mean(triangular_samples))
        median_triangular = float(np.median(triangular_samples))
        
        # Calculate occurrence statistics
        occurrence_samples = np.random.choice(
            occurrence_counts, iterations, p=occurrence_probabilities
        )
        mean_occurrences = float(np.mean(occurrence_samples))
        variance_occurrences = float(np.var(occurrence_samples))
        
        # Calculate percentiles for asset values
        percentiles = [5, 10, 25, 50, 75, 90, 95, 99, 99.9]
        asset_value_percentiles = {
            str(p): float(np.percentile(triangular_samples, p)) for p in percentiles
        }
        
        # Risk assessment based on ALE
        if ale < 100000:
            risk_level = "Low"
            risk_description = "Risk exposure is within acceptable limits"
        elif ale < 500000:
            risk_level = "Medium"
            risk_description = "Risk exposure requires monitoring and mitigation"
        else:
            risk_level = "High"
            risk_description = "Risk exposure requires immediate attention and mitigation"
        
        # Compliance metrics
        compliance_metrics = {
            "ale_currency": ale,
            "risk_tolerance_exceeded": ale > 1000000,
            "requires_board_attention": ale > 500000,
            "recommended_action": "Implement additional controls" if ale > 500000 else "Monitor and review",
            "compliance_score": "High" if ale < 100000 else "Medium" if ale < 500000 else "Low"
        }
        
        # Prepare simulation results
        simulation_results = {
            'run_id': run_id,
            'status': 'completed',
            'ale': ale,
            'mean_triangular': mean_triangular,
            'median_triangular': median_triangular,
            'mean_occurrences': mean_occurrences,
            'variance_occurrences': variance_occurrences,
            'prob1': prob1,
            'prob2': prob2,
            'prob3': prob3,
            'asset_value_percentiles': asset_value_percentiles,
            'risk_assessment': {
                'level': risk_level,
                'description': risk_description
            },
            'compliance_metrics': compliance_metrics,
            'scenario_name': scenario_name,
            'iterations': iterations,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        # Update simulation run in database
        await update_simulation_run(run_id, simulation_results, 'completed')
        
        logger.info(f"Completed simulation task {run_id} with ALE: £{ale:,.2f}")
        
    except Exception as e:
        logger.error(f"Simulation task {run_id} failed: {e}")
        
        # Update with error status
        error_results = {
            'run_id': run_id,
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.utcnow().isoformat()
        }
        
        await update_simulation_run(run_id, error_results, 'failed')


async def run_optimization_task(optimization_id: str, parameters: Dict[str, Any], org_id: str):
    """
    Background task to run control optimization.
    
    Args:
        optimization_id: Unique optimization identifier
        parameters: Optimization parameters
        org_id: Organization ID
    """
    logger.info(f"Starting optimization task {optimization_id}")
    
    try:
        # Extract parameters
        historical_data = parameters.get('historical_data', [])
        safeguard_effects = parameters.get('safeguard_effects', [])
        maintenance_loads = parameters.get('maintenance_loads', [])
        current_controls = parameters.get('current_controls', [])
        control_costs = parameters.get('control_costs', [])
        control_limits = parameters.get('control_limits', [])
        safeguard_target = parameters.get('safeguard_target', 90.0)
        maintenance_limit = parameters.get('maintenance_limit', 50.0)
        control_names = parameters.get('control_names', [])
        
        # Run control optimization
        from cyberrisk_core.control_optimizer import ControlOptimizer
        
        optimizer = ControlOptimizer()
        
        # Run the optimization
        result = optimizer.optimize_controls(
            historical_data=historical_data,
            safeguard_effects=safeguard_effects,
            maintenance_loads=maintenance_loads,
            current_controls=current_controls,
            control_costs=control_costs,
            control_limits=control_limits,
            safeguard_target=safeguard_target,
            maintenance_limit=maintenance_limit
        )
        
        # Calculate total additional cost
        total_additional_cost = sum(
            add_control * cost 
            for add_control, cost in zip(result['additional_controls'], control_costs)
        )
        
        # Generate recommendations
        recommendations = []
        for i, (add_control, cost) in enumerate(zip(result['additional_controls'], control_costs)):
            if add_control > 0:
                control_name = control_names[i] if i < len(control_names) else f"Control {i+1}"
                recommendations.append({
                    'control_type': control_name,
                    'current_count': current_controls[i] if i < len(current_controls) else 0,
                    'recommended_additional': int(add_control),
                    'unit_cost': cost,
                    'total_cost': int(add_control * cost)
                })
        
        # Prepare optimization results
        optimization_results = {
            'optimization_id': optimization_id,
            'status': 'completed',
            'results': {
                'total_additional_cost': total_additional_cost,
                'additional_controls': result['additional_controls'].tolist(),
                'safeguard_achieved': result.get('safeguard_achieved', safeguard_target),
                'maintenance_used': result.get('maintenance_used', 0),
                'optimization_successful': result.get('optimization_successful', True),
                'recommendations': recommendations,
                'weights_b': result['weights_b'].tolist() if 'weights_b' in result else [],
                'weights_d': result['weights_d'].tolist() if 'weights_d' in result else []
            },
            'parameters': parameters,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        # Update optimization run in database
        await update_optimization_run(optimization_id, optimization_results, 'completed')
        
        logger.info(f"Completed optimization task {optimization_id}")
        
    except Exception as e:
        logger.error(f"Optimization task {optimization_id} failed: {e}")
        
        # Update with error status
        error_results = {
            'optimization_id': optimization_id,
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.utcnow().isoformat()
        }
        
        await update_optimization_run(optimization_id, error_results, 'failed')


async def cleanup_expired_simulations(results_store: Dict[str, Any], 
                                    max_age_hours: int = 24):
    """
    Clean up expired simulation results from memory.
    
    Args:
        results_store: In-memory results storage
        max_age_hours: Maximum age in hours before cleanup
    """
    try:
        current_time = datetime.utcnow()
        expired_runs = []
        
        for run_id, run_data in results_store.items():
            created_at = datetime.fromisoformat(run_data['created_at'])
            age_hours = (current_time - created_at).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                expired_runs.append(run_id)
        
        for run_id in expired_runs:
            del results_store[run_id]
            logger.info(f"Cleaned up expired simulation {run_id}")
            
    except Exception as e:
        logger.error(f"Error during simulation cleanup: {e}")


# Periodic background tasks
async def background_maintenance():
    """Run periodic maintenance tasks."""
    while True:
        try:
            # This would be replaced with actual maintenance tasks
            logger.info("Running background maintenance...")
            
            # Sleep for 1 hour
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Background maintenance error: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes before retry 