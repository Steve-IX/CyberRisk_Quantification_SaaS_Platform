"""
Probability Model Module - Two-Phase Security Process Analysis

This module provides functions for analyzing conditional probabilities in 
two-phase security screening processes, including:
- Joint probability table analysis
- Marginalization calculations  
- Bayes theorem applications
"""

from typing import List, Tuple


def Task2(num: int, table: List[List[int]], probs: List[float]) -> Tuple[float, float, float]:
    """
    Analyze a two-phase security screening process using joint probability tables.
    
    Args:
        num: Total number of cases (should equal sum of all table entries)
        table: 3x4 joint distribution table as [[a,b,c,d], [e,f,g,h], [i,j,k,l]]
               where rows represent Y values (6,7,8) and columns represent X values (2,3,4,5)
        probs: List of conditional probabilities [P(T|X=2), P(T|X=3), P(T|X=4), P(T|X=5), P(T|Y=6), P(T|Y=7)]
        
    Returns:
        Tuple containing (prob1, prob2, prob3) where:
        - prob1: P(3 ≤ X ≤ 4)
        - prob2: P(X + Y ≤ 10)  
        - prob3: P(Y=8 | T) using Bayes theorem
    """
    # Unpack the joint distribution table
    a, b, c, d = table[0]  # Y=6 row
    e, f, g, h = table[1]  # Y=7 row  
    i, j, k, l = table[2]  # Y=8 row
    
    # Total number of cases (should equal num)
    total = a + b + c + d + e + f + g + h + i + j + k + l
    
    # Marginal sums by X (columns)
    X2 = a + e + i  # X = 2
    X3 = b + f + j  # X = 3
    X4 = c + g + k  # X = 4
    X5 = d + h + l  # X = 5
    
    # Marginal sums by Y (rows)
    Y6 = a + b + c + d  # Y = 6
    Y7 = e + f + g + h  # Y = 7
    Y8 = i + j + k + l  # Y = 8
    
    # (1) prob1: P(3 ≤ X ≤ 4)
    prob1 = (X3 + X4) / total
    
    # (2) prob2: P(X + Y ≤ 10)
    # Qualifying cells where X + Y ≤ 10:
    # (X=2,Y=6): a, (X=2,Y=7): e, (X=2,Y=8): i  
    # (X=3,Y=6): b, (X=3,Y=7): f
    # (X=4,Y=6): c
    prob2 = (a + e + i + b + f + c) / total
    
    # (3) Compute P(Y=8 | T) using Bayes theorem
    # Unpack the conditional test probabilities
    PX2, PX3, PX4, PX5, PY6, PY7 = probs
    
    # P(T) computed from the X-side using law of total probability
    PT_X = (PX2 * X2 + PX3 * X3 + PX4 * X4 + PX5 * X5) / total
    
    # P(T) computed from the Y-side:
    # Let P(T|Y=8) be unknown. Then by law of total probability:
    # P(T) = P(T|Y=6)*P(Y=6) + P(T|Y=7)*P(Y=7) + P(T|Y=8)*P(Y=8)
    # Solve for P(T|Y=8):
    PT_given_Y8 = (PT_X - (PY6 * Y6 + PY7 * Y7) / total) / (Y8 / total)
    
    # Now, by Bayes' theorem:
    # P(Y=8|T) = [P(T|Y=8) * P(Y=8)] / P(T)
    prob3 = (PT_given_Y8 * (Y8 / total)) / PT_X

    return (prob1, prob2, prob3)


def analyze_joint_distribution(table: List[List[int]]) -> dict:
    """
    Analyze a joint probability distribution table.
    
    Args:
        table: Joint distribution table as list of lists
        
    Returns:
        Dictionary containing marginal distributions and statistics
    """
    # Convert to more convenient format
    rows = len(table)
    cols = len(table[0]) if rows > 0 else 0
    total = sum(sum(row) for row in table)
    
    # Calculate marginals
    row_marginals = [sum(row) for row in table]
    col_marginals = [sum(table[i][j] for i in range(rows)) for j in range(cols)]
    
    # Convert to probabilities
    row_probs = [m / total for m in row_marginals] if total > 0 else []
    col_probs = [m / total for m in col_marginals] if total > 0 else []
    
    return {
        'total': total,
        'row_marginals': row_marginals,
        'col_marginals': col_marginals,
        'row_probabilities': row_probs,
        'col_probabilities': col_probs,
        'joint_probabilities': [[cell / total for cell in row] for row in table] if total > 0 else table
    }


def calculate_conditional_probability(joint_prob: float, marginal_prob: float) -> float:
    """
    Calculate conditional probability P(A|B) = P(A,B) / P(B).
    
    Args:
        joint_prob: Joint probability P(A,B)
        marginal_prob: Marginal probability P(B)
        
    Returns:
        Conditional probability P(A|B)
    """
    if marginal_prob == 0:
        raise ValueError("Cannot calculate conditional probability: marginal probability is zero")
    
    return joint_prob / marginal_prob


def bayes_theorem(prior: float, likelihood: float, evidence: float) -> float:
    """
    Apply Bayes' theorem: P(A|B) = P(B|A) * P(A) / P(B).
    
    Args:
        prior: Prior probability P(A)
        likelihood: Likelihood P(B|A)  
        evidence: Evidence P(B)
        
    Returns:
        Posterior probability P(A|B)
    """
    if evidence == 0:
        raise ValueError("Cannot apply Bayes' theorem: evidence probability is zero")
    
    return (likelihood * prior) / evidence 