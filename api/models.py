"""
API Models - Pydantic schemas for request/response validation

This module defines the data models used by the FastAPI endpoints
for simulation requests, optimization parameters, and responses.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SimulationStatus(str, Enum):
    """Simulation status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationRequest(BaseModel):
    """Request model for Monte Carlo simulation."""

    # Triangular distribution parameters for Asset Value
    asset_value_min: float = Field(..., gt=0,
                                   description="Triangular distribution minimum")
    asset_value_mode: float = Field(..., gt=0,
                                    description="Triangular distribution mode")
    asset_value_max: float = Field(..., gt=0,
                                   description="Triangular distribution maximum")

    # Discrete occurrence distribution
    occurrence_counts: List[int] = Field(...,
                                         min_items=1,
                                         description="Occurrence count values")
    occurrence_probabilities: List[float] = Field(
        ..., min_items=1, description="Occurrence probabilities")

    # Monte Carlo parameters
    iterations: int = Field(
        default=10000,
        ge=1000,
        le=1000000,
        description="Number of MC iterations")

    # Impact distribution parameters (log-normal for flaw A)
    flaw_a_mu: float = Field(...,
                             description="Log-normal mu parameter for flaw A")
    flaw_a_sigma: float = Field(...,
                                gt=0,
                                description="Log-normal sigma parameter for flaw A")

    # Impact distribution parameters (Pareto for flaw B)
    flaw_b_scale: float = Field(...,
                                gt=0,
                                description="Pareto scale parameter for flaw B")
    flaw_b_alpha: float = Field(...,
                                gt=0,
                                description="Pareto alpha parameter for flaw B")

    # Probability calculation points
    threshold_point1: float = Field(..., gt=0,
                                    description="Threshold for P(AV <= point1)")
    threshold_point2: float = Field(..., gt=0,
                                    description="Threshold for P(impact > point2)")
    range_point3: float = Field(...,
                                gt=0,
                                description="Lower bound for range probability")
    range_point4: float = Field(...,
                                gt=0,
                                description="Upper bound for range probability")

    # Optional metadata
    scenario_name: Optional[str] = Field(
        None, description="Human-readable scenario name")
    description: Optional[str] = Field(
        None, description="Scenario description")
    random_seed: Optional[int] = Field(
        None, description="Random seed for reproducibility")

    @validator('occurrence_probabilities')
    def probabilities_sum_to_one(cls, v, values):
        """Validate that probabilities sum to approximately 1.0."""
        if abs(sum(v) - 1.0) > 0.001:
            raise ValueError('Occurrence probabilities must sum to 1.0')
        return v

    @validator('occurrence_probabilities', each_item=True)
    def probabilities_non_negative(cls, v):
        """Validate that each probability is non-negative."""
        if v < 0:
            raise ValueError('Probabilities must be non-negative')
        return v

    @validator('asset_value_mode')
    def mode_within_bounds(cls, v, values):
        """Validate that mode is between min and max."""
        if 'asset_value_min' in values and 'asset_value_max' in values:
            if not (values['asset_value_min'] <=
                    v <= values['asset_value_max']):
                raise ValueError(
                    'Asset value mode must be between min and max')
        return v


class SimulationResults(BaseModel):
    """Results from Monte Carlo simulation."""

    prob1: float = Field(..., description="P(AV <= threshold_point1)")
    mean_triangular: float = Field(...,
                                   description="Mean of triangular distribution")
    median_triangular: float = Field(...,
                                     description="Median of triangular distribution")
    mean_occurrences: float = Field(...,
                                    description="Mean of occurrence distribution")
    variance_occurrences: float = Field(...,
                                        description="Variance of occurrence distribution")
    prob2: float = Field(..., description="P(total_impact > threshold_point2)")
    prob3: float = Field(...,
                         description="P(range_point3 <= total_impact <= range_point4)")
    ale: float = Field(..., description="Annualized Loss Expectancy")

    # Additional metrics
    percentiles: Optional[Dict[str, float]] = Field(
        None, description="Loss percentiles (P50, P90, P95, P99)")
    currency: str = Field(
        default="GBP",
        description="Currency for monetary values")


class SimulationResponse(BaseModel):
    """Response model for simulation requests."""

    run_id: str = Field(..., description="Unique simulation run identifier")
    status: SimulationStatus = Field(...,
                                     description="Current simulation status")
    created_at: datetime = Field(...,
                                 description="Simulation creation timestamp")
    completed_at: Optional[datetime] = Field(
        None, description="Simulation completion timestamp")

    # Request metadata
    iterations: int = Field(..., description="Number of iterations requested")
    scenario_name: Optional[str] = Field(None, description="Scenario name")

    # Results (only present when status=completed)
    results: Optional[SimulationResults] = Field(
        None, description="Simulation results")

    # Error information (only present when status=failed)
    error_message: Optional[str] = Field(
        None, description="Error message if failed")


class OptimizationRequest(BaseModel):
    """Request model for control optimization."""

    # Historical data (4 control types x 9 observations)
    historical_data: List[List[float]] = Field(
        ...,
        min_items=4,
        max_items=4,
        description="Historical control deployment data [4x9 matrix]"
    )

    # Outcome variables
    safeguard_effects: List[float] = Field(...,
                                           min_items=9,
                                           max_items=9,
                                           description="Historical safeguard effects")
    maintenance_loads: List[float] = Field(...,
                                           min_items=9,
                                           max_items=9,
                                           description="Historical maintenance loads")

    # Current state
    current_controls: List[int] = Field(...,
                                        min_items=4,
                                        max_items=4,
                                        description="Current control deployment")

    # Optimization parameters
    control_costs: List[float] = Field(...,
                                       min_items=4,
                                       max_items=4,
                                       description="Unit costs per control type")
    control_limits: List[int] = Field(...,
                                      min_items=4,
                                      max_items=4,
                                      description="Maximum allowed per control type")

    # Targets and constraints
    safeguard_target: float = Field(...,
                                    description="Minimum required safeguard effect")
    maintenance_limit: float = Field(...,
                                     description="Maximum allowed maintenance load")

    # Optional metadata
    optimization_name: Optional[str] = Field(
        None, description="Human-readable optimization name")
    control_names: Optional[List[str]] = Field(
        None, description="Names for each control type")

    @validator('historical_data')
    def validate_historical_data_shape(cls, v):
        """Validate that historical data has correct shape."""
        if len(v) != 4:
            raise ValueError(
                'Historical data must have exactly 4 control types')
        for i, control_data in enumerate(v):
            if len(control_data) != 9:
                raise ValueError(
                    f'Control type {
                        i + 1} must have exactly 9 historical observations')
        return v


class OptimizationResults(BaseModel):
    """Results from control optimization."""

    additional_controls: List[float] = Field(...,
                                             description="Additional controls to deploy")
    total_additional_cost: float = Field(...,
                                         description="Total cost of additional controls")

    # Model coefficients
    safeguard_weights: List[float] = Field(...,
                                           description="Regression weights for safeguard model")
    maintenance_weights: List[float] = Field(...,
                                             description="Regression weights for maintenance model")

    # Human-readable recommendations
    recommendations: List[Dict[str,
                               Any]] = Field(...,
                                             description="Control deployment recommendations")

    # Performance metrics
    current_safeguard_effect: Optional[float] = Field(
        None, description="Current safeguard effect")
    projected_safeguard_effect: Optional[float] = Field(
        None, description="Projected safeguard effect")
    current_maintenance_load: Optional[float] = Field(
        None, description="Current maintenance load")
    projected_maintenance_load: Optional[float] = Field(
        None, description="Projected maintenance load")


class OptimizationResponse(BaseModel):
    """Response model for optimization requests."""

    optimization_id: str = Field(...,
                                 description="Unique optimization identifier")
    status: str = Field(..., description="Optimization status")
    timestamp: datetime = Field(..., description="Optimization timestamp")

    # Results
    results: OptimizationResults = Field(...,
                                         description="Optimization results")


class UserSimulation(BaseModel):
    """User simulation list item."""

    run_id: str = Field(..., description="Simulation run ID")
    status: SimulationStatus = Field(..., description="Simulation status")
    created_at: datetime = Field(..., description="Creation timestamp")
    scenario_name: Optional[str] = Field(None, description="Scenario name")
    iterations: int = Field(..., description="Number of iterations")
    ale: Optional[float] = Field(None, description="ALE result (if completed)")


class SimulationListResponse(BaseModel):
    """Response model for simulation list."""

    simulations: List[UserSimulation] = Field(...,
                                              description="List of user simulations")
    total: int = Field(..., description="Total number of simulations")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Page offset")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp")
