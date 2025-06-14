"""
CyberRisk SaaS API - Main FastAPI Application

This is the main entry point for the CyberRisk quantification SaaS platform.
It provides RESTful endpoints for Monte Carlo simulation, optimization, and reporting.
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import asyncio
import logging

from cyberrisk_core import calculate_ale, optimize_controls
from .models import SimulationRequest, SimulationResponse, OptimizationRequest
from .database import get_database, init_db
from .auth import get_current_user
from .tasks import run_simulation_task

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CyberRisk Quantification API",
    description="Monte Carlo simulation and optimization for cyber risk management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],  # Update with actual domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for demo (replace with database in production)
simulation_results = {}
user_sessions = {}


@app.on_event("startup")
async def startup_event():
    """Initialize database and other startup tasks."""
    await init_db()
    logger.info("CyberRisk API started successfully")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "CyberRisk Quantification API",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "up",
            "database": "up",  # Add actual database check
            "simulation_engine": "up"
        }
    }


@app.post("/api/v1/simulate", response_model=Dict[str, Any])
async def start_simulation(
    request: SimulationRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Start a Monte Carlo simulation for cyber risk quantification.
    
    This endpoint queues a simulation job and returns immediately with a run_id.
    Use the /results/{run_id} endpoint to check progress and retrieve results.
    """
    try:
        # Generate unique run ID
        run_id = str(uuid.uuid4())
        
        # Store initial simulation state
        simulation_results[run_id] = {
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "user_id": current_user.get("sub"),
            "request": request.dict()
        }
        
        # Queue background simulation task
        background_tasks.add_task(
            run_simulation_task,
            run_id=run_id,
            request_data=request.dict(),
            results_store=simulation_results
        )
        
        logger.info(f"Simulation {run_id} queued for user {current_user.get('sub')}")
        
        return {
            "run_id": run_id,
            "status": "pending",
            "message": "Simulation queued successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to start simulation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Simulation start failed: {str(e)}")


@app.get("/api/v1/results/{run_id}")
async def get_simulation_results(
    run_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Retrieve simulation results by run ID.
    
    Returns the current status and results (if completed) for the specified simulation.
    """
    if run_id not in simulation_results:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    result = simulation_results[run_id]
    
    # Check if user has access to this simulation
    if result.get("user_id") != current_user.get("sub"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return result


@app.post("/api/v1/optimize")
async def optimize_controls_endpoint(
    request: OptimizationRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Optimize security control deployment using linear programming.
    
    This endpoint runs synchronously and returns the optimal control configuration.
    """
    try:
        # Run optimization using core library
        weights_b, weights_d, x_add = optimize_controls(
            x=request.historical_data,
            y=request.safeguard_effects,
            z=request.maintenance_loads,
            x_initial=request.current_controls,
            c=request.control_costs,
            x_bound=request.control_limits,
            se_bound=request.safeguard_target,
            ml_bound=request.maintenance_limit
        )
        
        # Calculate additional metrics
        total_cost = sum(add * cost for add, cost in zip(x_add, request.control_costs))
        
        response = {
            "optimization_id": str(uuid.uuid4()),
            "status": "completed",
            "results": {
                "additional_controls": x_add.tolist(),
                "total_additional_cost": total_cost,
                "safeguard_weights": weights_b.tolist(),
                "maintenance_weights": weights_d.tolist(),
                "recommendations": []
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Generate human-readable recommendations
        for i, (current, additional) in enumerate(zip(request.current_controls, x_add)):
            if additional > 0.01:
                response["results"]["recommendations"].append({
                    "control_type": f"Control {i+1}",
                    "current_count": current,
                    "recommended_additional": round(additional, 2),
                    "unit_cost": request.control_costs[i],
                    "total_cost": round(additional * request.control_costs[i], 2)
                })
        
        logger.info(f"Optimization completed for user {current_user.get('sub')}")
        return response
        
    except Exception as e:
        logger.error(f"Optimization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@app.get("/api/v1/simulations")
async def list_user_simulations(
    current_user: Dict = Depends(get_current_user),
    limit: int = 10,
    offset: int = 0
):
    """
    List simulation history for the current user.
    """
    user_id = current_user.get("sub")
    
    # Filter simulations by user
    user_simulations = [
        {
            "run_id": run_id,
            "status": data["status"],
            "created_at": data["created_at"],
            "iterations": data["request"].get("iterations", 0)
        }
        for run_id, data in simulation_results.items()
        if data.get("user_id") == user_id
    ]
    
    # Apply pagination
    total = len(user_simulations)
    paginated = user_simulations[offset:offset + limit]
    
    return {
        "simulations": paginated,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.delete("/api/v1/results/{run_id}")
async def delete_simulation(
    run_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Delete a simulation and its results.
    """
    if run_id not in simulation_results:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    result = simulation_results[run_id]
    
    # Check if user has access to this simulation
    if result.get("user_id") != current_user.get("sub"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    del simulation_results[run_id]
    
    return {"message": "Simulation deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 