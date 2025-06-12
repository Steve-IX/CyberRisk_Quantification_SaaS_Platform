from math import sqrt, exp
from random import random, gauss
from dhCheck_Task1 import dhCheckCorrectness

def Task1(a, b, c, point1, number_set, prob_set, num, point2,
         mu, sigma, xm, alpha, point3, point4):
    

    # --------------------------------------------------
    # (1) Triangular Distribution Calculations
    # --------------------------------------------------

    def triangular_cdf(x, a, b, c):
        """
        Returns the CDF of a Triangular(a, c, b) distribution at x.
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

    # Return results in the specified order. "Do not truncate!"
    return (prob1, MEAN_t, MEDIAN_t, MEAN_d, VARIANCE_d, prob2, prob3, ALE)

