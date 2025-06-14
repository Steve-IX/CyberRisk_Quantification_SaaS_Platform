"""
Risk Metrics Module - Monte Carlo Simulation for Annualized Loss Expectancy (ALE)

This module provides functions for calculating cyber risk metrics using:
- Triangular distributions for asset values
- Discrete distributions for occurrence frequencies  
- Log-normal and Pareto distributions for impact magnitudes
- Monte Carlo simulation for loss expectancy calculations
"""

from math import sqrt, exp, log
from random import random, gauss, seed
from typing import List, Tuple, Optional
import numpy as np


def Task1(a: float, b: float, c: float, point1: float, 
         number_set: List[int], prob_set: List[float], 
         num: int, point2: float, mu: float, sigma: float, 
         xm: float, alpha: float, point3: float, point4: float,
         random_seed: Optional[int] = None) -> Tuple[float, ...]:
    """
    Calculate Annualized Loss Expectancy (ALE) using Monte Carlo simulation.
    
    Args:
        a, b, c: Triangular distribution parameters for Asset Value (AV)
        point1: Threshold for probability calculation P(AV <= point1)
        number_set: List of occurrence count values [N0, N1, ..., N9]
        prob_set: List of probabilities [P0, P1, ..., P9] for occurrence counts
        num: Number of Monte Carlo iterations
        point2: Threshold for P(total_impact > point2)
        mu, sigma: Log-normal distribution parameters for flaw A
        xm, alpha: Pareto distribution parameters for flaw B  
        point3, point4: Range for P(point3 <= total_impact <= point4)
        random_seed: Optional seed for reproducible results
        
    Returns:
        Tuple containing (prob1, mean_t, median_t, mean_d, var_d, prob2, prob3, ale)
    """
    
    if random_seed is not None:
        seed(random_seed)
        np.random.seed(random_seed)

    # --------------------------------------------------
    # (1) Triangular Distribution Calculations
    # --------------------------------------------------

    def triangular_cdf(x: float, a: float, b: float, c: float) -> float:
        """
        Returns the CDF of a Triangular(a, c, b) distribution at x.
        
        Args:
            x: Value to evaluate CDF at
            a: Lower bound
            b: Upper bound  
            c: Mode
            
        Returns:
            CDF value at x
        """
        if x <= a:
            return 0.0
        elif a <= x <= c:
            return ((x - a)**2) / ((b - a) * (c - a))
        elif c < x <= b:
            return 1.0 - ((b - x)**2) / ((b - a) * (b - c))
        else:  # x > b
            return 1.0

    # 1(i) Compute prob1 = Probability(AV <= point1)
    prob1 = triangular_cdf(point1, a, b, c)

    # 1(ii) Mean and Median of the Triangular distribution
    # Mean of Triangular(a, c, b) is (a + b + c) / 3
    MEAN_t = (a + b + c) / 3.0

    # Median calculation:
    # F(c) = (c - a)/(b - a). Compare it to 0.5 to decide which side the median is on.
    F_c = (c - a) / float(b - a)
    if abs(F_c - 0.5) < 1e-15:
        # If F_c == 0.5, then the median is exactly c
        MEDIAN_t = c
    elif F_c > 0.5:
        # Median is on [a, c]
        MEDIAN_t = a + sqrt(0.5 * (b - a) * (c - a))
    else:
        # Median is on [c, b]
        MEDIAN_t = b - sqrt(0.5 * (b - a) * (b - c))

    # --------------------------------------------------
    # (2) Discrete Distribution (Annual Occurrences)
    # --------------------------------------------------
    # number_set = [N0..N9], prob_set = [P0..P9]
    # MEAN_d = sum(Ni * Pi), i=0..9
    # VARIANCE_d = E[X^2] - (E[X])^2

    MEAN_d = 0.0
    E_X2 = 0.0  # For variance calculation

    for (N_i, P_i) in zip(number_set, prob_set):
        MEAN_d += N_i * P_i
        E_X2 += (N_i**2) * P_i

    VARIANCE_d = E_X2 - (MEAN_d**2)

    # --------------------------------------------------
    # (3) Monte Carlo Simulation
    # --------------------------------------------------
    # We generate 'num' samples of:
    #   impact_A ~ Lognormal(mu, sigma)  => A = exp( gauss(mu, sigma) )
    #   impact_B ~ Pareto(xm, alpha)     => B = xm / ( (1 - U)^(1/alpha) ), U in (0,1)
    # Then total_impact = A + B.

    total_impacts = []
    for _ in range(num):
        # Generate flaw A impact (lognormal)
        # ln(A) ~ Normal(mu, sigma^2)
        A = exp(gauss(mu, sigma))

        # Generate flaw B impact (Pareto)
        U = random()
        B = xm / ((1 - U)**(1.0 / alpha))

        total_impacts.append(A + B)

    # 3(ii) prob2 = Probability(total_impact > point2)
    count_greater_point2 = sum(1 for val in total_impacts if val > point2)
    prob2 = count_greater_point2 / float(num)

    # 3(iii) prob3 = Probability(point3 <= total_impact <= point4)
    count_between = sum(1 for val in total_impacts if point3 <= val <= point4)
    prob3 = count_between / float(num)

    # --------------------------------------------------
    # (4) Calculate ALE
    # --------------------------------------------------
    # SLE = AV * EF = MEDIAN_t * prob2
    # ARO = MEAN_d
    # ALE = ARO * SLE = MEAN_d * (MEDIAN_t * prob2)
    ALE = MEAN_d * (MEDIAN_t * prob2)

    # Return results in the specified order
    return (prob1, MEAN_t, MEDIAN_t, MEAN_d, VARIANCE_d, prob2, prob3, ALE)


def calculate_percentiles(values: List[float], percentiles: List[float] = None) -> dict:
    """
    Calculate percentiles from simulation results.
    
    Args:
        values: List of simulated values
        percentiles: List of percentile values to calculate (default: [50, 90, 95, 99])
        
    Returns:
        Dictionary mapping percentile to value
    """
    if percentiles is None:
        percentiles = [50, 90, 95, 99]
    
    values_array = np.array(values)
    result = {}
    
    for p in percentiles:
        result[f"P{p}"] = float(np.percentile(values_array, p))
    
    return result


def format_currency(amount: float, currency: str = "GBP") -> str:
    """
    Format monetary amounts for reporting.
    
    Args:
        amount: Monetary amount
        currency: Currency code (default: GBP)
        
    Returns:
        Formatted currency string
    """
    if currency == "GBP":
        return f"£{amount:,.2f}"
    elif currency == "EUR":
        return f"€{amount:,.2f}"
    elif currency == "USD":
        return f"${amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}" 