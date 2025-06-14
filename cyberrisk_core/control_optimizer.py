"""
Control Optimizer Module - Security Control Portfolio Optimization

This module provides functions for optimizing security control deployments using:
- Linear regression to model control effectiveness
- Linear programming to minimize costs while meeting security targets
- Portfolio optimization for risk reduction
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
try:
    from scipy.optimize import linprog
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


def Task3(x: List[List[float]], y: List[float], z: List[float], 
         x_initial: List[int], c: List[float], x_bound: List[int], 
         se_bound: float, ml_bound: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Optimize security control deployment using linear programming.
    
    Args:
        x: Historical control count matrix (4 lists of 9 values each)
        y: Safeguard effect values (9 values) 
        z: Maintenance load values (9 values)
        x_initial: Current control deployment [c1, c2, c3, c4]
        c: Unit costs for each control type [cost1, cost2, cost3, cost4]
        x_bound: Upper bounds for each control type [max1, max2, max3, max4]
        se_bound: Minimum safeguard effect requirement
        ml_bound: Maximum maintenance load allowed
        
    Returns:
        Tuple containing (weights_b, weights_d, x_add) where:
        - weights_b: Regression weights for safeguard effect model
        - weights_d: Regression weights for maintenance load model  
        - x_add: Additional controls to deploy per type
    """
    if not SCIPY_AVAILABLE:
        raise ImportError(
            "SciPy is required for optimization. Install with: pip install scipy"
        )
    
    # Convert inputs to numpy arrays
    X_features = np.array(x).T  # Transpose to get (9 x 4) design matrix
    n = X_features.shape[0]     # number of samples = 9
    ones = np.ones((n, 1))
    X_design = np.hstack((ones, X_features))  # Design matrix with intercept (9 x 5)
    
    y = np.array(y)
    z = np.array(z)
    
    # Compute least squares estimates using normal equations
    # weights = (X^T X)^(-1) X^T y
    try:
        weights_b, _, _, _ = np.linalg.lstsq(X_design, y, rcond=None)
        weights_d, _, _, _ = np.linalg.lstsq(X_design, z, rcond=None)
    except np.linalg.LinAlgError as e:
        raise ValueError(f"Failed to solve linear regression: {e}")
    
    # Calculate current performance metrics
    current_safeguard = weights_b[0] + np.dot(weights_b[1:], x_initial)
    current_maintenance = weights_d[0] + np.dot(weights_d[1:], x_initial)
    
    # Calculate gaps that additional controls must address
    safeguard_gap = se_bound - current_safeguard
    maintenance_gap = ml_bound - current_maintenance
    
    # Setup linear programming constraints
    # Constraint 1: weights_b[1:] * x_add >= safeguard_gap
    # Constraint 2: weights_d[1:] * x_add <= maintenance_gap
    A_ub = np.array([
        -weights_b[1:],   # Safeguard constraint (multiply by -1 for >=)
         weights_d[1:]    # Maintenance constraint 
    ])
    b_ub = np.array([
        -safeguard_gap,   # Negative because we multiplied constraint by -1
         maintenance_gap
    ])
    
    # Variable bounds: 0 <= x_add[i] <= (x_bound[i] - x_initial[i])
    bounds = []
    for i in range(4):
        upper_bound = max(0, x_bound[i] - x_initial[i])
        bounds.append((0, upper_bound))
    
    # Solve the linear programming problem
    # Objective: minimize total cost c^T * x_add
    try:
        result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, 
                        method='highs', options={'disp': False})
        
        if not result.success:
            raise ValueError(f"Optimization failed: {result.message}")
        
        x_add = result.x
        
    except Exception as e:
        raise ValueError(f"Linear programming solver failed: {e}")
    
    return (weights_b, weights_d, x_add)


def evaluate_control_portfolio(x_current: List[int], weights_b: np.ndarray, 
                             weights_d: np.ndarray) -> Dict[str, float]:
    """
    Evaluate the performance of a control portfolio.
    
    Args:
        x_current: Current control deployment
        weights_b: Regression weights for safeguard effect
        weights_d: Regression weights for maintenance load
        
    Returns:
        Dictionary with safeguard effect and maintenance load
    """
    x_current = np.array(x_current)
    
    safeguard_effect = weights_b[0] + np.dot(weights_b[1:], x_current)
    maintenance_load = weights_d[0] + np.dot(weights_d[1:], x_current)
    
    return {
        'safeguard_effect': float(safeguard_effect),
        'maintenance_load': float(maintenance_load)
    }


def calculate_control_roi(x_add: np.ndarray, costs: List[float], 
                         risk_reduction: float, ale_current: float) -> Dict[str, float]:
    """
    Calculate return on investment for control deployment.
    
    Args:
        x_add: Additional controls to deploy
        costs: Unit costs for each control type
        risk_reduction: Percentage risk reduction achieved
        ale_current: Current annualized loss expectancy
        
    Returns:
        Dictionary with ROI metrics
    """
    total_cost = np.dot(x_add, costs)
    annual_savings = ale_current * (risk_reduction / 100)
    
    roi_percentage = ((annual_savings - total_cost) / total_cost * 100) if total_cost > 0 else 0
    payback_years = (total_cost / annual_savings) if annual_savings > 0 else float('inf')
    
    return {
        'total_cost': float(total_cost),
        'annual_savings': float(annual_savings),
        'roi_percentage': float(roi_percentage),
        'payback_years': float(payback_years),
        'net_present_value_3y': float(3 * annual_savings - total_cost)
    }


def optimize_control_budget(available_budget: float, control_costs: List[float],
                           control_effectiveness: List[float]) -> Dict[str, any]:
    """
    Optimize control selection under budget constraints.
    
    Args:
        available_budget: Total budget available
        control_costs: Cost of each control type
        control_effectiveness: Effectiveness score of each control type
        
    Returns:
        Dictionary with optimal control selection
    """
    if not SCIPY_AVAILABLE:
        raise ImportError("SciPy is required for budget optimization")
    
    n_controls = len(control_costs)
    
    # Maximize effectiveness subject to budget constraint
    # This is a knapsack-like problem - we'll use linear relaxation
    c = [-eff for eff in control_effectiveness]  # Negative for maximization
    A_ub = [control_costs]
    b_ub = [available_budget]
    bounds = [(0, 1) for _ in range(n_controls)]  # Binary variables relaxed to [0,1]
    
    try:
        result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
        
        if result.success:
            selected_controls = result.x
            total_cost = np.dot(selected_controls, control_costs)
            total_effectiveness = np.dot(selected_controls, control_effectiveness)
            
            return {
                'selected_controls': selected_controls.tolist(),
                'total_cost': float(total_cost),
                'total_effectiveness': float(total_effectiveness),
                'budget_utilization': float(total_cost / available_budget * 100)
            }
        else:
            raise ValueError(f"Budget optimization failed: {result.message}")
            
    except Exception as e:
        raise ValueError(f"Budget optimization error: {e}")


def generate_control_recommendations(current_controls: List[int], 
                                   optimal_controls: np.ndarray,
                                   control_names: List[str] = None) -> List[Dict]:
    """
    Generate human-readable control recommendations.
    
    Args:
        current_controls: Current control deployment
        optimal_controls: Optimal additional controls
        control_names: Names for each control type
        
    Returns:
        List of recommendation dictionaries
    """
    if control_names is None:
        control_names = [f"Control Type {i+1}" for i in range(len(current_controls))]
    
    recommendations = []
    
    for i, (current, additional) in enumerate(zip(current_controls, optimal_controls)):
        if additional > 0.01:  # Only recommend if significant addition
            recommendations.append({
                'control_name': control_names[i],
                'current_count': current,
                'recommended_additional': round(additional, 2),
                'new_total': current + round(additional, 2),
                'priority': 'High' if additional > 2 else 'Medium' if additional > 1 else 'Low'
            })
    
    # Sort by additional controls needed (descending)
    recommendations.sort(key=lambda x: x['recommended_additional'], reverse=True)
    
    return recommendations 