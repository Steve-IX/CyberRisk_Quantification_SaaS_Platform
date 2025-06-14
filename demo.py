#!/usr/bin/env python3
"""
CyberRisk Core Library Demo

This script demonstrates the basic functionality of the CyberRisk 
quantification library with example scenarios.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from cyberrisk_core import calculate_ale, calculate_conditional_probabilities, optimize_controls
from cyberrisk_core.risk_metrics import format_currency, calculate_percentiles
from cyberrisk_core.control_optimizer import generate_control_recommendations
import numpy as np


def demo_ale_calculation():
    """Demonstrate ALE calculation with Monte Carlo simulation."""
    print("=" * 60)
    print("DEMO 1: Annualized Loss Expectancy (ALE) Calculation")
    print("=" * 60)
    
    # Example scenario: E-commerce website vulnerability
    print("\nScenario: E-commerce Website Data Breach")
    print("-" * 40)
    
    # Asset value parameters (triangular distribution)
    asset_min = 50_000      # Minimum asset value (£)
    asset_mode = 150_000    # Most likely asset value (£)
    asset_max = 500_000     # Maximum asset value (£)
    
    # Annual occurrence frequency (discrete distribution)
    occurrence_counts = [0, 1, 2, 3, 4, 5]  # Number of incidents per year
    occurrence_probs = [0.3, 0.4, 0.2, 0.06, 0.03, 0.01]  # Probabilities
    
    # Impact magnitude parameters
    flaw_a_mu = 9.2         # Log-normal mu for system downtime costs
    flaw_a_sigma = 1.0      # Log-normal sigma for system downtime costs
    flaw_b_scale = 5_000    # Pareto scale for regulatory fines
    flaw_b_alpha = 2.5      # Pareto alpha for regulatory fines
    
    # Simulation parameters
    iterations = 50_000
    random_seed = 42
    
    print(f"Asset Value Range: {format_currency(asset_min)} - {format_currency(asset_max)}")
    print(f"Most Likely Value: {format_currency(asset_mode)}")
    print(f"Monte Carlo Iterations: {iterations:,}")
    print(f"Random Seed: {random_seed}")
    
    # Run simulation
    print("\nRunning Monte Carlo simulation...")
    
    results = calculate_ale(
        a=asset_min,
        b=asset_max,
        c=asset_mode,
        point1=100_000,  # Threshold for asset value probability
        number_set=occurrence_counts,
        prob_set=occurrence_probs,
        num=iterations,
        point2=50_000,   # Threshold for impact probability
        mu=flaw_a_mu,
        sigma=flaw_a_sigma,
        xm=flaw_b_scale,
        alpha=flaw_b_alpha,
        point3=20_000,   # Lower bound for range probability
        point4=100_000,  # Upper bound for range probability
        random_seed=random_seed
    )
    
    # Unpack results
    prob1, mean_t, median_t, mean_d, var_d, prob2, prob3, ale = results
    
    # Display results
    print("\n" + "="*50)
    print("SIMULATION RESULTS")
    print("="*50)
    
    print(f"\nAsset Value Statistics:")
    print(f"  Mean Value: {format_currency(mean_t)}")
    print(f"  Median Value: {format_currency(median_t)}")
    print(f"  P(Value ≤ £100k): {prob1:.3f} ({prob1*100:.1f}%)")
    
    print(f"\nThreat Occurrence Statistics:")
    print(f"  Expected Annual Occurrences: {mean_d:.2f}")
    print(f"  Occurrence Variance: {var_d:.2f}")
    
    print(f"\nImpact Probability Analysis:")
    print(f"  P(Impact > £50k): {prob2:.3f} ({prob2*100:.1f}%)")
    print(f"  P(£20k ≤ Impact ≤ £100k): {prob3:.3f} ({prob3*100:.1f}%)")
    
    print(f"\n🎯 ANNUALIZED LOSS EXPECTANCY (ALE):")
    print(f"   {format_currency(ale)}")
    
    # Risk assessment
    if ale < 50_000:
        risk_level = "LOW"
        action = "Continue monitoring"
    elif ale < 200_000:
        risk_level = "MEDIUM" 
        action = "Implement additional controls"
    elif ale < 1_000_000:
        risk_level = "HIGH"
        action = "Urgent risk treatment required"
    else:
        risk_level = "CRITICAL"
        action = "Immediate action and insurance required"
    
    print(f"\n📊 Risk Assessment: {risk_level}")
    print(f"💡 Recommended Action: {action}")
    
    return ale


def demo_probability_analysis():
    """Demonstrate conditional probability analysis."""
    print("\n\n" + "=" * 60)
    print("DEMO 2: Conditional Probability Analysis")
    print("=" * 60)
    
    print("\nScenario: Two-Phase Security Screening Process")
    print("-" * 50)
    
    # Joint distribution table (3x4)
    # Rows: Y values (6, 7, 8)
    # Columns: X values (2, 3, 4, 5)
    joint_table = [
        [25, 35, 20, 15],  # Y=6
        [30, 40, 25, 10],  # Y=7
        [15, 25, 30, 20]   # Y=8
    ]
    
    total_cases = sum(sum(row) for row in joint_table)
    
    # Conditional probabilities for test results
    test_probs = [
        0.8,   # P(Test=Positive | X=2)
        0.75,  # P(Test=Positive | X=3)
        0.7,   # P(Test=Positive | X=4)
        0.65,  # P(Test=Positive | X=5)
        0.6,   # P(Test=Positive | Y=6)
        0.55   # P(Test=Positive | Y=7)
    ]
    
    print(f"Total Cases: {total_cases}")
    print(f"Joint Distribution Table:")
    print("     X=2   X=3   X=4   X=5")
    for i, row in enumerate(joint_table):
        print(f"Y={i+6}  {row[0]:3d}   {row[1]:3d}   {row[2]:3d}   {row[3]:3d}")
    
    # Run analysis
    prob1, prob2, prob3 = calculate_conditional_probabilities(
        num=total_cases,
        table=joint_table,
        probs=test_probs
    )
    
    print(f"\n" + "="*40)
    print("PROBABILITY ANALYSIS RESULTS")
    print("="*40)
    
    print(f"\nP(3 ≤ X ≤ 4): {prob1:.4f} ({prob1*100:.2f}%)")
    print(f"P(X + Y ≤ 10): {prob2:.4f} ({prob2*100:.2f}%)")
    print(f"P(Y = 8 | Test = Positive): {prob3:.4f} ({prob3*100:.2f}%)")
    
    return prob1, prob2, prob3


def demo_control_optimization():
    """Demonstrate security control optimization."""
    print("\n\n" + "=" * 60)
    print("DEMO 3: Security Control Optimization")
    print("=" * 60)
    
    print("\nScenario: Optimal Security Control Deployment")
    print("-" * 48)
    
    # Historical control deployment data (4 control types x 9 observations)
    historical_data = [
        [2, 3, 1, 4, 2, 3, 1, 2, 3],  # Firewalls
        [1, 2, 3, 2, 1, 2, 3, 1, 2],  # IDS/IPS
        [3, 2, 4, 1, 3, 2, 4, 3, 2],  # Endpoint Protection
        [1, 1, 2, 2, 1, 1, 2, 1, 1]   # Security Training
    ]
    
    # Historical outcomes
    safeguard_effects = [85, 78, 92, 70, 88, 82, 95, 87, 80]  # Effectiveness scores
    maintenance_loads = [45, 52, 38, 65, 42, 48, 35, 44, 50]  # Maintenance burden
    
    # Current deployment
    current_controls = [2, 1, 3, 1]  # Current count of each control type
    
    # Optimization parameters
    control_costs = [10_000, 15_000, 8_000, 5_000]  # Cost per unit
    control_limits = [5, 4, 6, 3]  # Maximum allowed per type
    
    # Targets
    safeguard_target = 90.0    # Minimum safeguard effect required
    maintenance_limit = 50.0   # Maximum maintenance load allowed
    
    control_names = ["Firewalls", "IDS/IPS", "Endpoint Protection", "Security Training"]
    
    print("Historical Data Analysis:")
    for i, name in enumerate(control_names):
        avg_deployment = np.mean(historical_data[i])
        print(f"  {name}: Average deployment = {avg_deployment:.1f}")
    
    print(f"\nCurrent Deployment:")
    for i, (name, count) in enumerate(zip(control_names, current_controls)):
        print(f"  {name}: {count} units (£{control_costs[i]:,} each)")
    
    print(f"\nOptimization Targets:")
    print(f"  Minimum Safeguard Effect: {safeguard_target}")
    print(f"  Maximum Maintenance Load: {maintenance_limit}")
    
    # Run optimization
    print("\nRunning optimization...")
    
    try:
        weights_b, weights_d, x_add = optimize_controls(
            x=historical_data,
            y=safeguard_effects,
            z=maintenance_loads,
            x_initial=current_controls,
            c=control_costs,
            x_bound=control_limits,
            se_bound=safeguard_target,
            ml_bound=maintenance_limit
        )
        
        # Generate recommendations
        recommendations = generate_control_recommendations(
            current_controls=current_controls,
            optimal_controls=x_add,
            control_names=control_names
        )
        
        # Calculate costs
        total_additional_cost = sum(add * cost for add, cost in zip(x_add, control_costs))
        
        print(f"\n" + "="*50)
        print("OPTIMIZATION RESULTS")
        print("="*50)
        
        print(f"\nRegression Model Coefficients:")
        print(f"Safeguard Effect Model: {weights_b}")
        print(f"Maintenance Load Model: {weights_d}")
        
        print(f"\nOptimal Additional Controls:")
        for i, (name, additional) in enumerate(zip(control_names, x_add)):
            if additional > 0.01:
                cost = additional * control_costs[i]
                print(f"  {name}: +{additional:.2f} units (£{cost:,.2f})")
        
        print(f"\nTotal Additional Investment: £{total_additional_cost:,.2f}")
        
        if recommendations:
            print(f"\n📋 RECOMMENDATIONS:")
            for rec in recommendations:
                print(f"  • {rec['control_name']}: Add {rec['recommended_additional']:.1f} units")
                print(f"    Priority: {rec['priority']}")
                print(f"    Cost: £{rec['total_cost']:,.2f}")
        else:
            print(f"\n✅ Current deployment is already optimal!")
            
    except Exception as e:
        print(f"\n❌ Optimization failed: {e}")
        print("Note: Make sure SciPy is installed for optimization features")
        
    return None


def demo_integration_example():
    """Show how components work together."""
    print("\n\n" + "=" * 60)
    print("DEMO 4: Integrated Risk Management Workflow")
    print("=" * 60)
    
    print("\nScenario: Complete Risk Assessment & Control Optimization")
    print("-" * 58)
    
    # Step 1: Calculate baseline ALE
    print("Step 1: Baseline Risk Assessment")
    baseline_ale = 125_000  # From previous calculation (simplified)
    
    # Step 2: Simulate control effectiveness
    print("Step 2: Control Effectiveness Analysis")
    control_effectiveness = 0.35  # 35% risk reduction
    
    # Step 3: Calculate residual risk
    residual_ale = baseline_ale * (1 - control_effectiveness)
    risk_reduction = baseline_ale - residual_ale
    
    # Step 4: ROI calculation
    control_investment = 45_000  # From optimization
    annual_savings = risk_reduction
    roi_percentage = ((annual_savings - control_investment) / control_investment) * 100
    payback_years = control_investment / annual_savings
    
    print(f"\n" + "="*50)
    print("INTEGRATED ANALYSIS RESULTS")
    print("="*50)
    
    print(f"\n💰 Financial Impact:")
    print(f"  Baseline ALE: {format_currency(baseline_ale)}")
    print(f"  Residual ALE: {format_currency(residual_ale)}")
    print(f"  Risk Reduction: {format_currency(risk_reduction)}")
    
    print(f"\n📊 Investment Analysis:")
    print(f"  Control Investment: {format_currency(control_investment)}")
    print(f"  Annual Risk Savings: {format_currency(annual_savings)}")
    print(f"  ROI: {roi_percentage:.1f}%")
    print(f"  Payback Period: {payback_years:.1f} years")
    
    print(f"\n🎯 Business Case:")
    if roi_percentage > 20:
        print("  ✅ STRONG business case - High ROI")
    elif roi_percentage > 0:
        print("  ✅ POSITIVE business case - Acceptable ROI")
    else:
        print("  ❌ WEAK business case - Consider alternatives")
    
    print(f"\n📝 Executive Summary:")
    print(f"  Investment of {format_currency(control_investment)} in security controls")
    print(f"  reduces annual cyber risk by {format_currency(risk_reduction)},")
    print(f"  delivering {roi_percentage:.0f}% ROI with {payback_years:.1f}-year payback.")


def main():
    """Run all demos."""
    print("🛡️  CyberRisk Quantification Library Demo")
    print("🚀 Transforming Cyber Risk into Actionable Business Intelligence")
    print()
    
    try:
        # Run individual demos
        ale_result = demo_ale_calculation()
        prob_results = demo_probability_analysis()
        demo_control_optimization()
        demo_integration_example()
        
        print("\n\n" + "="*60)
        print("🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nNext Steps:")
        print("1. Start the FastAPI server: uvicorn api.main:app --reload")
        print("2. Visit http://localhost:8000/docs for API documentation")
        print("3. Create a demo JWT token: python api/auth.py")
        print("4. Test the API endpoints with the token")
        print("\nFor SaaS deployment:")
        print("• Configure PostgreSQL database")
        print("• Set up authentication with Auth0/Clerk")
        print("• Deploy to AWS Lambda/Fargate")
        print("• Build Next.js frontend")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 