"""
CyberRisk SaaS API - Main FastAPI Application

This is the main entry point for the CyberRisk quantification SaaS platform.
It provides RESTful endpoints for Monte Carlo simulation, optimization, and reporting.
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
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
from .reports import generate_simulation_pdf, generate_optimization_pdf
from .billing import get_billing_service, check_usage_limit

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
        # Check usage limits
        user_tier = current_user.get("tier", "starter")
        user_org_id = current_user.get("org_id", "demo-org")
        
        # Check simulation limit
        if not await check_usage_limit(user_org_id, user_tier, "simulations_per_month"):
            raise HTTPException(
                status_code=429, 
                detail="Monthly simulation limit exceeded. Please upgrade your plan."
            )
        
        # Check iteration limit
        billing_service = get_billing_service()
        limits = await billing_service.get_usage_limits(user_tier)
        max_iterations = limits.get("max_iterations", 50000)
        
        if max_iterations != -1 and request.iterations > max_iterations:
            raise HTTPException(
                status_code=400,
                detail=f"Iteration limit exceeded. Maximum {max_iterations:,} iterations allowed for {user_tier} tier."
            )
        
        # Generate unique run ID
        run_id = str(uuid.uuid4())
        
        # Record usage
        billing_service = get_billing_service()
        await billing_service.record_usage(user_org_id, "simulations", 1)
        
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


@app.post("/api/v1/billing/checkout")
async def create_checkout_session(
    request: dict,
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a Stripe checkout session for subscription signup.
    """
    try:
        billing_service = get_billing_service()
        
        tier = request.get("tier", "starter")
        annual = request.get("annual", False)
        success_url = request.get("success_url", "http://localhost:3000/success")
        cancel_url = request.get("cancel_url", "http://localhost:3000/pricing")
        
        session = await billing_service.create_checkout_session(
            customer_email=current_user.get("email"),
            tier=tier,
            annual=annual,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        return session
        
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        raise HTTPException(status_code=500, detail=f"Checkout creation failed: {str(e)}")


@app.get("/api/v1/billing/usage-limits")
async def get_usage_limits(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get usage limits for the current user's subscription tier.
    """
    try:
        billing_service = get_billing_service()
        tier = current_user.get("tier", "starter")
        
        limits = await billing_service.get_usage_limits(tier)
        
        return {
            "tier": tier,
            "limits": limits,
            "current_usage": {
                "simulations_this_month": 0,  # Would be fetched from database
                "pdf_downloads_this_month": 0,
                "users": 1
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get usage limits: {e}")
        raise HTTPException(status_code=500, detail=f"Usage limits fetch failed: {str(e)}")


@app.get("/api/v1/billing/pricing")
async def get_pricing():
    """
    Get subscription pricing tiers.
    """
    return {
        "tiers": [
            {
                "name": "Starter",
                "id": "starter",
                "price_monthly": 49,
                "price_annual": 490,  # 2 months free
                "features": [
                    "2 users",
                    "50 simulations/month",
                    "50k max iterations",
                    "10 PDF downloads/month",
                    "Email support"
                ],
                "limits": {
                    "users": 2,
                    "simulations_per_month": 50,
                    "max_iterations": 50000,
                    "pdf_downloads": 10
                }
            },
            {
                "name": "Pro",
                "id": "pro",
                "price_monthly": 199,
                "price_annual": 1990,
                "features": [
                    "10 users",
                    "500 simulations/month",
                    "500k max iterations",
                    "100 PDF downloads/month",
                    "Priority support",
                    "API access"
                ],
                "limits": {
                    "users": 10,
                    "simulations_per_month": 500,
                    "max_iterations": 500000,
                    "pdf_downloads": 100
                }
            },
            {
                "name": "Enterprise",
                "id": "enterprise",
                "price_monthly": 499,
                "price_annual": 4990,
                "features": [
                    "25 users",
                    "Unlimited simulations",
                    "Unlimited iterations",
                    "Unlimited PDF downloads",
                    "Dedicated support",
                    "Custom integrations",
                    "White-label options"
                ],
                "limits": {
                    "users": 25,
                    "simulations_per_month": -1,
                    "max_iterations": -1,
                    "pdf_downloads": -1
                }
            }
        ]
    }


@app.get("/api/v1/results/{run_id}/pdf")
async def download_simulation_pdf(
    run_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Download a PDF report for a completed simulation.
    """
    # Check if simulation exists and user has access
    if run_id not in simulation_results:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    result = simulation_results[run_id]
    
    # Check if user has access to this simulation
    if result.get("user_id") != current_user.get("sub"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if simulation is completed
    if result.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Simulation not completed")
    
    # Check PDF download limits
    user_tier = current_user.get("tier", "starter")
    user_org_id = current_user.get("org_id", "demo-org")
    
    if not await check_usage_limit(user_org_id, user_tier, "pdf_downloads"):
        raise HTTPException(
            status_code=429,
            detail="Monthly PDF download limit exceeded. Please upgrade your plan."
        )
    
    try:
        # Generate PDF
        pdf_bytes = await generate_simulation_pdf(run_id, current_user)
        
        # Record PDF download usage
        billing_service = get_billing_service()
        await billing_service.record_usage(user_org_id, "pdf_downloads", 1)
        
        # Get scenario name for filename
        scenario_name = result["request"].get("scenario_name", "simulation")
        filename = f"cyberrisk_report_{scenario_name.replace(' ', '_')}_{run_id[:8]}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate PDF for simulation {run_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@app.post("/api/v1/optimize/pdf")
async def download_optimization_pdf(
    optimization_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate and download a PDF report for optimization results.
    """
    try:
        # Generate PDF
        pdf_bytes = await generate_optimization_pdf(optimization_data, current_user)
        
        # Generate filename
        optimization_name = optimization_data.get("optimization_name", "optimization")
        filename = f"cyberrisk_optimization_{optimization_name.replace(' ', '_')}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate optimization PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 