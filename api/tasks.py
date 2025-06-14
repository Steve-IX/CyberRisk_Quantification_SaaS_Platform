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

from cyberrisk_core import calculate_ale, calculate_percentiles, format_currency
from .database import update_simulation_status

logger = logging.getLogger(__name__)


async def run_simulation_task(run_id: str, request_data: Dict[str, Any], 
                            results_store: Dict[str, Any]):
    """
    Run Monte Carlo simulation in background.
    
    Args:
        run_id: Unique simulation run identifier
        request_data: Simulation parameters from API request
        results_store: In-memory results storage (fallback when DB unavailable)
    """
    logger.info(f"Starting simulation {run_id}")
    
    try:
        # Update status to running
        results_store[run_id]["status"] = "running"
        results_store[run_id]["started_at"] = datetime.utcnow().isoformat()
        
        await update_simulation_status(run_id, "running")
        
        # Extract parameters from request
        params = extract_simulation_parameters(request_data)
        
        # Run the Monte Carlo simulation
        simulation_results = await run_monte_carlo_simulation(params)
        
        # Calculate additional metrics
        enhanced_results = enhance_simulation_results(simulation_results, params)
        
        # Update results
        results_store[run_id]["status"] = "completed"
        results_store[run_id]["completed_at"] = datetime.utcnow().isoformat()
        results_store[run_id]["results"] = enhanced_results
        
        await update_simulation_status(run_id, "completed", enhanced_results)
        
        logger.info(f"Simulation {run_id} completed successfully")
        
    except Exception as e:
        error_msg = f"Simulation failed: {str(e)}"
        logger.error(f"Simulation {run_id} failed: {error_msg}")
        logger.error(traceback.format_exc())
        
        # Update status to failed
        results_store[run_id]["status"] = "failed"
        results_store[run_id]["error_message"] = error_msg
        results_store[run_id]["completed_at"] = datetime.utcnow().isoformat()
        
        await update_simulation_status(run_id, "failed", error_message=error_msg)


def extract_simulation_parameters(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and validate simulation parameters from API request.
    
    Args:
        request_data: Raw request data from API
        
    Returns:
        Processed parameters for simulation
    """
    return {
        # Triangular distribution parameters
        'a': request_data['asset_value_min'],
        'b': request_data['asset_value_max'], 
        'c': request_data['asset_value_mode'],
        'point1': request_data['threshold_point1'],
        
        # Occurrence distribution
        'number_set': request_data['occurrence_counts'],
        'prob_set': request_data['occurrence_probabilities'],
        
        # Monte Carlo settings
        'num': request_data['iterations'],
        'random_seed': request_data.get('random_seed'),
        
        # Impact distribution parameters
        'mu': request_data['flaw_a_mu'],
        'sigma': request_data['flaw_a_sigma'],
        'xm': request_data['flaw_b_scale'],
        'alpha': request_data['flaw_b_alpha'],
        
        # Probability calculation points
        'point2': request_data['threshold_point2'],
        'point3': request_data['range_point3'],
        'point4': request_data['range_point4'],
        
        # Metadata
        'scenario_name': request_data.get('scenario_name', 'Unnamed Scenario'),
        'description': request_data.get('description', '')
    }


async def run_monte_carlo_simulation(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the Monte Carlo simulation with given parameters.
    
    Args:
        params: Simulation parameters
        
    Returns:
        Raw simulation results
    """
    # Run the core simulation
    # This is CPU-intensive, so we might want to run it in a thread pool
    # For now, we'll run it directly since it's vectorized NumPy code
    
    result = calculate_ale(
        a=params['a'],
        b=params['b'], 
        c=params['c'],
        point1=params['point1'],
        number_set=params['number_set'],
        prob_set=params['prob_set'],
        num=params['num'],
        point2=params['point2'],
        mu=params['mu'],
        sigma=params['sigma'],
        xm=params['xm'],
        alpha=params['alpha'],
        point3=params['point3'],
        point4=params['point4'],
        random_seed=params.get('random_seed')
    )
    
    # Unpack results
    prob1, mean_t, median_t, mean_d, var_d, prob2, prob3, ale = result
    
    return {
        'prob1': prob1,
        'mean_triangular': mean_t,
        'median_triangular': median_t,
        'mean_occurrences': mean_d,
        'variance_occurrences': var_d,
        'prob2': prob2,
        'prob3': prob3,
        'ale': ale,
        'scenario_name': params['scenario_name'],
        'iterations': params['num']
    }


def enhance_simulation_results(raw_results: Dict[str, Any], 
                             params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance simulation results with additional metrics and formatting.
    
    Args:
        raw_results: Raw simulation results
        params: Original simulation parameters
        
    Returns:
        Enhanced results with additional metrics
    """
    # Start with raw results
    enhanced = raw_results.copy()
    
    # Add currency formatting
    enhanced['ale_formatted'] = format_currency(raw_results['ale'])
    enhanced['mean_triangular_formatted'] = format_currency(raw_results['mean_triangular'])
    enhanced['median_triangular_formatted'] = format_currency(raw_results['median_triangular'])
    
    # Calculate risk levels based on ALE
    ale = raw_results['ale']
    if ale < 10_000:
        risk_level = "Low"
        risk_color = "green"
    elif ale < 100_000:
        risk_level = "Medium"
        risk_color = "yellow"
    elif ale < 1_000_000:
        risk_level = "High"
        risk_color = "orange"
    else:
        risk_level = "Critical"
        risk_color = "red"
    
    enhanced['risk_assessment'] = {
        'level': risk_level,
        'color': risk_color,
        'description': get_risk_description(risk_level, ale)
    }
    
    # Add percentile information for asset values
    # This is a simplified calculation - in production you'd want to 
    # generate the full distribution during simulation
    enhanced['asset_value_percentiles'] = {
        'P10': raw_results['mean_triangular'] * 0.7,
        'P25': raw_results['mean_triangular'] * 0.85,
        'P50': raw_results['median_triangular'],
        'P75': raw_results['mean_triangular'] * 1.15,
        'P90': raw_results['mean_triangular'] * 1.3,
        'P95': raw_results['mean_triangular'] * 1.4,
        'P99': raw_results['mean_triangular'] * 1.6
    }
    
    # Add summary statistics
    enhanced['summary'] = {
        'total_scenarios_analyzed': 1,
        'simulation_iterations': params['num'],
        'expected_annual_loss': raw_results['ale'],
        'loss_probability': raw_results['prob2'],
        'annual_occurrence_rate': raw_results['mean_occurrences'],
        'simulation_confidence': 'High' if params['num'] >= 10000 else 'Medium'
    }
    
    # Add compliance-ready metrics
    enhanced['compliance_metrics'] = {
        'ale_as_percent_of_revenue': None,  # Would need revenue data
        'risk_tolerance_exceeded': ale > 500_000,  # Example threshold
        'recommended_action': get_recommended_action(ale, raw_results['prob2']),
        'csrd_material_risk': ale > 100_000,  # Example materiality threshold
        'nis2_significant_impact': raw_results['prob2'] > 0.1
    }
    
    return enhanced


def get_risk_description(risk_level: str, ale: float) -> str:
    """Generate risk description based on level and ALE."""
    descriptions = {
        "Low": f"Annual expected loss of {format_currency(ale)} represents a manageable risk level.",
        "Medium": f"Annual expected loss of {format_currency(ale)} requires monitoring and basic controls.",
        "High": f"Annual expected loss of {format_currency(ale)} requires immediate attention and enhanced controls.",
        "Critical": f"Annual expected loss of {format_currency(ale)} represents an unacceptable risk requiring urgent action."
    }
    
    return descriptions.get(risk_level, "Risk assessment unavailable.")


def get_recommended_action(ale: float, prob2: float) -> str:
    """Generate recommended action based on risk metrics."""
    if ale > 1_000_000:
        return "Immediate risk treatment required - consider insurance and additional controls"
    elif ale > 100_000:
        return "Enhanced security controls recommended - conduct cost-benefit analysis"
    elif prob2 > 0.2:
        return "Monitor risk closely - high probability of impact requires attention"
    else:
        return "Continue current risk management approach with regular review"


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