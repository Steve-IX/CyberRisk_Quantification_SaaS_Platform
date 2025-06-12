
from dhCheck_Task2 import dhCheckCorrectness

def Task2(num, table, probs):
    # Unpack the joint distribution table
    a, b, c, d = table[0]
    e, f, g, h = table[1]
    i, j, k, l = table[2]
    
    # Total number of cases (should equal num)
    total = a + b + c + d + e + f + g + h + i + j + k + l
    
    # Sums by X (columns)
    X2 = a + e + i  # X = 2
    X3 = b + f + j  # X = 3
    X4 = c + g + k  # X = 4
    X5 = d + h + l  # X = 5
    
    # Sums by Y (rows)
    Y6 = a + b + c + d  # Y = 6
    Y7 = e + f + g + h  # Y = 7
    Y8 = i + j + k + l  # Y = 8
    
    # (1) prob1: P(3 ≤ X ≤ 4)
    prob1 = (X3 + X4) / total
    
    # (1) prob2: P(X + Y ≤ 10)
    # Qualifying cells: (X=2,Y=6): a, (X=2,Y=7): e, (X=2,Y=8): i, (X=3,Y=6): b, (X=3,Y=7): f, (X=4,Y=6): c.
    prob2 = (a + e + i + b + f + c) / total
    
    # (2) Compute P(Y=8 | T)
    # Unpack the test probabilities
    PX2, PX3, PX4, PX5, PY6, PY7 = probs
    
    # P(T) computed from the X-side
    PT_X = PX2 * X2 + PX3 * X3 + PX4 * X4 + PX5 * X5
    
    # P(T) computed from the Y-side:
    # Let P(T|Y=8) be unknown. Then,
    # PY6*Y6 + PY7*Y7 + P(T|Y=8)*Y8 = PT_X.
    # Solve for P(T|Y=8):
    PT_given_Y8 = (PT_X - (PY6 * Y6 + PY7 * Y7)) / Y8
    
    # Now, by Bayes' theorem,
    # P(Y=8|T) = [P(T|Y=8) * P(Y=8)] / P(T)
    # where P(Y=8) = Y8/total and P(T) = PT_X/total.
    # The totals cancel out:
    prob3 = (PT_given_Y8 * Y8) / PT_X

    return (prob1, prob2, prob3)
    

