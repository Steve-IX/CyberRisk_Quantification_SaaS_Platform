
import numpy as np
from scipy.optimize import linprog
from dhCheck_Task3 import dhCheckCorrectness

def Task3(x, y, z, x_initial, c, x_bound, se_bound, ml_bound):
    # Estimate weights_b and weights_d via linear regression.
    # x is given as a list of 4 lists (each of length 9). We need a (9 x 4) design matrix.
    X_features = np.array(x).T  # shape: (9,4)
    n = X_features.shape[0]     # number of samples = 9
    ones = np.ones((n, 1))
    X_design = np.hstack((ones, X_features))  # design matrix with intercept (9 x 5)
    
    # Convert y and z to numpy arrays
    y = np.array(y)
    z = np.array(z)
    
    # Compute least squares estimates
    weights_b, _, _, _ = np.linalg.lstsq(X_design, y, rcond=None)
    weights_d, _, _, _ = np.linalg.lstsq(X_design, z, rcond=None)
    
    # Solving the linear programming problem.
    # x_initial be the current deployment. Additional controls: x_add.
    # The new safeguard effect becomes:
    #    new_safeguard = weights_b[0] + weights_b[1]* (x_initial[0] + x_add[0]) + ... + weights_b[4]* (x_initial[3] + x_add[3])
    
    # Compute current safeguard effect and current maintenance load.
    current_safeguard = weights_b[0] + np.dot(weights_b[1:], x_initial)
    current_maintenance = weights_d[0] + np.dot(weights_d[1:], x_initial)
    
    # Compute the gap that additional controls must cover.
    safeguard_gap = se_bound - current_safeguard
    maintenance_gap = ml_bound - current_maintenance
    
    # Setup LP constraints.
    # For safeguard, we have: weights_b[1:]*x_add >= safeguard_gap.
    # Multiplying both sides by -1 to obtain
    A_ub = np.array([
        -weights_b[1:],   # safeguard constraint
         weights_d[1:]    # maintenance constraint
    ])
    b_ub = np.array([
        -safeguard_gap,
         maintenance_gap
    ])
    
    # Variable bounds: x_add[i] must be nonnegative and not exceed (x_bound[i] - x_initial[i])
    bounds = []
    for i in range(4):
        bounds.append((0, x_bound[i] - x_initial[i]))
    
    # The objective is to minimize total cost: c[0]*x_add[0] + ... + c[3]*x_add[3]
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
    x_add = res.x  # additional security controls
    
    return (weights_b, weights_d, x_add)
    
