"""
CyberRisk SaaS API - Main FastAPI Application

This is the main entry point for the CyberRisk quantification SaaS platform.
It provides RESTful endpoints for Monte Carlo simulation, optimization, and reporting.
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPBearer
from typing import Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import logging

from cyberrisk_core import optimize_controls
from .models import SimulationRequest, OptimizationRequest
from .database import get_database, init_db, store_simulation_run, get_simulation_run
from .auth import get_current_user
from .tasks import run_simulation_task
from .reports import generate_simulation_pdf, generate_optimization_pdf, generate_compliance_pdf, store_compliance_report
from .billing import get_billing_service, check_usage_limit, record_simulation_usage
from .ai_models import get_ai_risk_assessment, initialize_ai_models
from .analytics import get_analytics_service
from .threat_intelligence import get_threat_intelligence_engine
from .enterprise import get_enterprise_api_manager, require_api_key, require_role, UserRole, PermissionType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CyberRisk Quantification API",
    description="Monte Carlo simulation and optimization for cyber risk management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc")

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://yourdomain.com"],
    # Update with actual domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for demo (replace with database in production)
simulation_results = {}
user_sessions = {}

security = HTTPBearer()


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting CyberRisk Quantification SaaS Platform...")

    # Initialize database
    await init_db()

    # Initialize AI models for Phase 4
    try:
        await initialize_ai_models()
        logger.info("AI models initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize AI models: {e}")

    # Initialize threat intelligence
    try:
        threat_engine = get_threat_intelligence_engine()
        await threat_engine.collect_threat_intelligence()
        logger.info("Threat intelligence initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize threat intelligence: {e}")

    logger.info("Application startup complete")


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
                detail="Monthly simulation limit exceeded. Please upgrade your plan.")
        
        # Check iteration limit
        billing_service = get_billing_service()
        limits = await billing_service.get_usage_limits(user_tier)
        max_iterations = limits.get("max_iterations", 50000)
        
        if max_iterations != -1 and request.iterations > max_iterations:
            raise HTTPException(
                status_code=400, detail=f"Iteration limit exceeded. Maximum {
                    max_iterations:,    } iterations allowed for {user_tier} tier.")
        
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
        
        logger.info(
            f"Simulation {run_id} queued for user {
                current_user.get('sub')}")
        
        return {
            "run_id": run_id,
            "status": "pending",
            "message": "Simulation queued successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to start simulation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Simulation start failed: {
                str(e)}")


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
        total_cost = sum(
            add * cost for add,
            cost in zip(
                x_add,
                request.control_costs))
        
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
        for i, (current, additional) in enumerate(
                zip(request.current_controls, x_add)):
            if additional > 0.01:
                response["results"]["recommendations"].append({
                    "control_type": f"Control {i + 1}",
                    "current_count": current,
                    "recommended_additional": round(additional, 2),
                    "unit_cost": request.control_costs[i],
                    "total_cost": round(additional * request.control_costs[i], 2)
                })
        
        logger.info(
            f"Optimization completed for user {
                current_user.get('sub')}")
        return response
        
    except Exception as e:
        logger.error(f"Optimization failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Optimization failed: {
                str(e)}")


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
    current_user: dict = Depends(get_current_user)
):
    """Create a Stripe checkout session for subscription upgrade."""
    try:
        billing_service = get_billing_service()
        
        # Extract request parameters
        tier = request.get('tier')
        annual = request.get('annual', False)
        success_url = request.get('success_url')
        cancel_url = request.get('cancel_url')

        if not tier:
            raise HTTPException(
                status_code=400,
                detail="Subscription tier is required")

        # Create checkout session
        checkout_session = await billing_service.create_checkout_session(
            customer_email=current_user['email'],
            tier=tier,
            annual=annual,
            success_url=success_url,
            cancel_url=cancel_url,
            org_id=current_user.get('org_id')
        )
        
        return {
            "status": "success",
            "checkout_session": checkout_session
        }
        
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/billing/webhook")
async def handle_stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    try:
        payload = await request.body()
        signature = request.headers.get('stripe-signature')

        if not signature:
            raise HTTPException(
                status_code=400,
                detail="Missing Stripe signature")

        billing_service = get_billing_service()
        result = await billing_service.handle_webhook(payload, signature)

        return {"status": "success", "result": result}

    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/billing/status")
async def get_billing_status(current_user: dict = Depends(get_current_user)):
    """Get billing status and usage information for the current organization."""
    try:
        org_id = current_user.get('org_id')
        if not org_id:
            raise HTTPException(
                status_code=400,
                detail="Organization ID not found")

        billing_service = get_billing_service()
        status = await billing_service.get_subscription_status(org_id)

        return {
            "status": "success",
            "billing_status": status
        }

    except Exception as e:
        logger.error(f"Failed to get billing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(
            status_code=500,
            detail=f"Usage limits fetch failed: {
                str(e)}")


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
            detail="Monthly PDF download limit exceeded. Please upgrade your plan.")
    
    try:
        # Generate PDF
        pdf_bytes = await generate_simulation_pdf(run_id, current_user)
        
        # Record PDF download usage
        billing_service = get_billing_service()
        await billing_service.record_usage(user_org_id, "pdf_downloads", 1)
        
        # Get scenario name for filename
        scenario_name = result["request"].get("scenario_name", "simulation")
        filename = f"cyberrisk_report_{scenario_name.replace(' ',
                                                             '_')}_{run_id[:8]}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(
            f"Failed to generate PDF for simulation {run_id}: {
                str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {
                str(e)}")


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
        optimization_name = optimization_data.get(
            "optimization_name", "optimization")
        filename = f"cyberrisk_optimization_{
            optimization_name.replace(
                ' ', '_')}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate optimization PDF: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {
                str(e)}")


@app.post("/api/v1/reports/compliance")
async def generate_compliance_report(
    request: dict,
    current_user: dict = Depends(get_current_user)
):
    """Generate a compliance report (CSRD, NIS2, etc.)."""

    # Check usage limits
    org_id = current_user.get('org_id')
    user_tier = current_user.get('tier', 'starter')

    if not await check_usage_limit(org_id, user_tier, "pdf_downloads"):
        raise HTTPException(
            status_code=429,
            detail="PDF download limit exceeded")

    try:
        report_type = request.get('report_type', 'CSRD').upper()
        simulation_run_id = request.get('simulation_run_id')
        additional_data = request.get('additional_data', {})

        if not simulation_run_id:
            raise HTTPException(
                status_code=400,
                detail="Simulation run ID is required")

        # Get simulation data
        simulation_data = await get_simulation_run(simulation_run_id)
        if not simulation_data:
            raise HTTPException(
                status_code=404,
                detail="Simulation run not found")

        # Check if user has access to this simulation
        if simulation_data.get('org_id') != org_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Prepare user info
        user_info = {
            'org_name': current_user.get('org_name', 'Your Organization'),
            'email': current_user.get('email'),
            'org_id': org_id
        }

        # Generate compliance report
        pdf_bytes = await generate_compliance_pdf(
            report_type, simulation_data, user_info, additional_data
        )

        # Store report metadata
        report_data = {
            'report_type': report_type,
            'simulation_run_id': simulation_run_id,
            'additional_data': additional_data,
            'generated_by': current_user.get('email')
        }

        report_id = await store_compliance_report(
            org_id, report_type, simulation_run_id, report_data
        )

        # Record usage
        await record_simulation_usage(org_id, {
            'type': 'compliance_report',
            'report_type': report_type,
            'report_id': report_id
        })

        # Return PDF as response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{report_type}_compliance_report_{simulation_run_id[:8]}.pdf"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate compliance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/reports/compliance/history")
async def get_compliance_reports_history(
    report_type: str = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get compliance reports history for the organization."""
    try:
        org_id = current_user.get('org_id')
        if not org_id:
            raise HTTPException(
                status_code=400,
                detail="Organization ID not found")

        # Build query
        where_clause = "WHERE org_id = %s"
        params = [org_id]

        if report_type:
            where_clause += " AND report_type = %s"
            params.append(report_type.upper())

        query = f"""
        SELECT id, report_type, simulation_run_id, generated_at, downloaded_at,
               report_data->>'generated_by' as generated_by
        FROM compliance_reports
        {where_clause}
        ORDER BY generated_at DESC
        LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                reports = await cursor.fetchall()

        return {
            "status": "success",
            "reports": [dict(report) for report in reports],
            "total": len(reports)
        }

    except Exception as e:
        logger.error(f"Failed to get compliance reports history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Enhanced simulation endpoint with usage tracking
@app.post("/api/v1/simulate")
async def create_simulation(
    request: SimulationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Create a new simulation run with enhanced usage tracking."""

    # Check usage limits
    org_id = current_user.get('org_id')
    user_tier = current_user.get('tier', 'starter')

    if not await check_usage_limit(org_id, user_tier, "simulations"):
        raise HTTPException(
            status_code=429,
            detail="Simulation limit exceeded")

    # Check iteration limits
    limits = await get_billing_service().get_usage_limits(user_tier)
    max_iterations = limits.get('max_iterations', 50000)

    if max_iterations > 0 and request.iterations > max_iterations:
        raise HTTPException(
            status_code=400,
            detail=f"Iteration limit exceeded. Maximum allowed: {max_iterations}")

    try:
        # Generate run ID
        run_id = str(uuid.uuid4())

        # Store simulation request in database
        await store_simulation_run(run_id, org_id, request.dict())

        # Run simulation in background
        background_tasks.add_task(
            run_simulation_task,
            run_id,
            request.dict(),
            org_id
        )

        # Record usage
        await record_simulation_usage(org_id, {
            'run_id': run_id,
            'scenario_name': request.scenario_name,
            'iterations': request.iterations
        })

        return {
            "status": "accepted",
            "run_id": run_id,
            "message": "Simulation queued for processing"
        }

    except Exception as e:
        logger.error(f"Simulation request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# PHASE 4: AI-POWERED RISK ASSESSMENT ENDPOINTS

@app.post("/api/v1/ai/risk-assessment", response_model=Dict[str, Any])
@require_api_key(PermissionType.READ)
async def ai_risk_assessment(
    request: Request,
    organization_features: Dict[str, float]
):
    """Generate AI-powered risk assessment"""

    try:
        api_key_data = request.state.api_key_data

        # Record API usage
        await record_api_usage(api_key_data.organization_id, "ai_risk_assessment")

        # Get AI risk assessment
        ai_assessor = get_ai_risk_assessment()
        prediction = ai_assessor.predict_risk(organization_features)

        # Log audit event
        enterprise_manager = get_enterprise_api_manager()
        await enterprise_manager.log_audit_event(
            user_id=api_key_data.user_id,
            organization_id=api_key_data.organization_id,
            action="ai_risk_assessment",
            resource="ai/risk-assessment",
            details={"features": organization_features},
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", "unknown")
        )

        return {
            "success": True,
            "prediction": {
                "predicted_risk": prediction.predicted_risk,
                "confidence_interval": prediction.confidence_interval,
                "risk_factors": prediction.risk_factors,
                "trend_analysis": prediction.trend_analysis,
                "recommendations": prediction.recommendations,
                "model_confidence": prediction.model_confidence
            }
        }

    except Exception as e:
        logger.error(f"AI risk assessment failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="AI risk assessment failed")


@app.get("/api/v1/ai/threat-landscape/{organization_id}")
@require_api_key(PermissionType.READ)
async def get_threat_landscape(
    request: Request,
    organization_id: int
):
    """Get AI-powered threat landscape analysis"""

    try:
        api_key_data = request.state.api_key_data

        # Check organization access
        if api_key_data.organization_id != organization_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to organization")

        # Get threat intelligence
        threat_engine = get_threat_intelligence_engine()
        threats = await threat_engine.get_organization_threats(organization_id)

        # Convert to serializable format
        threat_data = []
        for threat in threats:
            threat_data.append({
                "threat_id": threat.threat_id,
                "title": threat.title,
                "description": threat.description,
                "category": threat.category.value,
                "severity": threat.severity.value,
                "source": threat.source,
                "first_seen": threat.first_seen.isoformat(),
                "is_active": threat.is_active
            })

        return {
            "success": True,
            "organization_id": organization_id,
            "threat_count": len(threat_data),
            "threats": threat_data,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Threat landscape retrieval failed: {e}")
        raise HTTPException(status_code=500,
                            detail="Threat landscape retrieval failed")

# PHASE 4: ADVANCED ANALYTICS ENDPOINTS


@app.get("/api/v1/analytics/dashboard/{organization_id}")
@require_api_key(PermissionType.READ)
async def get_analytics_dashboard(
    request: Request,
    organization_id: int,
    time_range: str = "30d"
):
    """Get advanced analytics dashboard data"""

    try:
        api_key_data = request.state.api_key_data

        # Check organization access
        if api_key_data.organization_id != organization_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to organization")

        # Get analytics service
        analytics_service = get_analytics_service()
        dashboard_data = await analytics_service.get_dashboard_data(organization_id, time_range)

        # Convert to serializable format
        metrics_data = []
        for metric in dashboard_data.key_metrics:
            metrics_data.append({
                "metric_name": metric.metric_name,
                "value": metric.value,
                "change_percentage": metric.change_percentage,
                "trend": metric.trend,
                "benchmark_percentile": metric.benchmark_percentile,
                "timestamp": metric.timestamp.isoformat()
            })

        return {
            "success": True,
            "organization_id": organization_id,
            "time_range": time_range,
            "key_metrics": metrics_data,
            "threat_intelligence": dashboard_data.threat_intelligence,
            "compliance_status": dashboard_data.compliance_status,
            "optimization_insights": dashboard_data.optimization_insights,
            "real_time_alerts": dashboard_data.real_time_alerts,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Analytics dashboard failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Analytics dashboard failed")


@app.get("/api/v1/analytics/real-time/{organization_id}")
@require_api_key(PermissionType.READ)
async def get_real_time_metrics(
    request: Request,
    organization_id: int
):
    """Get real-time metrics for live dashboard updates"""

    try:
        api_key_data = request.state.api_key_data

        # Check organization access
        if api_key_data.organization_id != organization_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to organization")

        # Get real-time metrics
        analytics_service = get_analytics_service()
        metrics = await analytics_service.get_real_time_metrics(organization_id)

        return {
            "success": True,
            "organization_id": organization_id,
            "metrics": metrics
        }

    except Exception as e:
        logger.error(f"Real-time metrics failed: {e}")
        raise HTTPException(status_code=500, detail="Real-time metrics failed")

# PHASE 4: ENTERPRISE API MANAGEMENT ENDPOINTS


@app.post("/api/v1/enterprise/api-keys")
@require_role(UserRole.ORG_ADMIN)
async def create_api_key(
    request: Request,
    api_key_request: Dict[str, Any]
):
    """Create new API key for organization"""

    try:
        user_data = request.state.user_data
        organization_id = user_data["organization_id"]
        user_id = user_data["user_id"]

        # Get enterprise manager
        enterprise_manager = get_enterprise_api_manager()

        # Generate API key
        api_key, api_key_data = await enterprise_manager.generate_api_key(
            organization_id=organization_id,
            user_id=user_id,
            name=api_key_request.get("name", "API Key"),
            permissions=api_key_request.get("permissions", ["read"]),
            expires_days=api_key_request.get("expires_days")
        )

        return {
            "success": True,
            "api_key": api_key,
            "key_id": api_key_data.key_id,
            "name": api_key_data.name,
            "permissions": api_key_data.permissions,
            "rate_limit": api_key_data.rate_limit,
            "expires_at": api_key_data.expires_at.isoformat() if api_key_data.expires_at else None,
            "created_at": api_key_data.created_at.isoformat()}

    except Exception as e:
        logger.error(f"API key creation failed: {e}")
        raise HTTPException(status_code=500, detail="API key creation failed")


@app.get("/api/v1/enterprise/audit-logs/{organization_id}")
@require_role(UserRole.ORG_ADMIN)
async def get_audit_logs(
    request: Request,
    organization_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None
):
    """Get audit logs for organization"""

    try:
        user_data = request.state.user_data

        # Check organization access
        if user_data["organization_id"] != organization_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to organization")

        # Parse dates
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
        else:
            start_dt = datetime.utcnow() - timedelta(days=30)

        if end_date:
            end_dt = datetime.fromisoformat(end_date)
        else:
            end_dt = datetime.utcnow()

        # Get audit logs
        enterprise_manager = get_enterprise_api_manager()
        audit_logs = await enterprise_manager.get_audit_logs(
            organization_id, start_dt, end_dt, user_id, action
        )

        # Convert to serializable format
        logs_data = []
        for log in audit_logs:
            logs_data.append({
                "user_id": log.user_id,
                "action": log.action,
                "resource": log.resource,
                "details": log.details,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "timestamp": log.timestamp.isoformat(),
                "status": log.status
            })

        return {
            "success": True,
            "organization_id": organization_id,
            "audit_logs": logs_data,
            "total_count": len(logs_data),
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat()
        }

    except Exception as e:
        logger.error(f"Audit logs retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Audit logs retrieval failed")


@app.post("/api/v1/enterprise/sso-setup/{organization_id}")
@require_role(UserRole.ORG_ADMIN)
async def setup_sso(
    request: Request,
    organization_id: int,
    sso_config: Dict[str, Any]
):
    """Setup SSO integration for organization"""

    try:
        user_data = request.state.user_data

        # Check organization access
        if user_data["organization_id"] != organization_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to organization")

        # Setup SSO
        enterprise_manager = get_enterprise_api_manager()
        success = await enterprise_manager.setup_sso_integration(
            organization_id=organization_id,
            provider=sso_config.get("provider"),
            config=sso_config.get("config", {})
        )

        if success:
            return {
                "success": True,
                "message": "SSO integration configured successfully",
                "organization_id": organization_id,
                "provider": sso_config.get("provider")
            }
        else:
            raise HTTPException(status_code=500, detail="SSO setup failed")

    except Exception as e:
        logger.error(f"SSO setup failed: {e}")
        raise HTTPException(status_code=500, detail="SSO setup failed")

# PHASE 4: THREAT INTELLIGENCE ENDPOINTS


@app.get("/api/v1/threat-intelligence/latest")
@require_api_key(PermissionType.READ)
async def get_latest_threats(
    request: Request,
    limit: int = 20,
    severity: Optional[str] = None,
    category: Optional[str] = None
):
    """Get latest threat intelligence"""

    try:
        # Get threat intelligence
        threat_engine = get_threat_intelligence_engine()
        all_threats = await threat_engine.collect_threat_intelligence()

        # Filter threats
        filtered_threats = all_threats
        if severity:
            filtered_threats = [
                t for t in filtered_threats if t.severity.value == severity]
        if category:
            filtered_threats = [
                t for t in filtered_threats if t.category.value == category]

        # Limit results
        limited_threats = filtered_threats[:limit]

        # Convert to serializable format
        threats_data = []
        for threat in limited_threats:
            threats_data.append({
                "threat_id": threat.threat_id,
                "title": threat.title,
                "description": threat.description,
                "category": threat.category.value,
                "severity": threat.severity.value,
                "source": threat.source,
                "first_seen": threat.first_seen.isoformat(),
                "is_active": threat.is_active
            })

        return {
            "success": True,
            "threats": threats_data,
            "total_count": len(threats_data),
            "filters": {
                "severity": severity,
                "category": category,
                "limit": limit
            },
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Threat intelligence retrieval failed: {e}")
        raise HTTPException(status_code=500,
                            detail="Threat intelligence retrieval failed")

# Helper function for API usage tracking


async def record_api_usage(organization_id: int, endpoint: str):
    """Record API usage for billing and rate limiting"""
    try:
        # This would integrate with existing usage tracking
        logger.info(
            f"API usage recorded: org={organization_id}, endpoint={endpoint}")
    except Exception as e:
        logger.error(f"Failed to record API usage: {e}")


def get_db_connection():
    """Get database connection for sync operations"""
    # This is a sync wrapper for the async get_database function
    return get_database()


def run_optimization_task(optimization_id: str, parameters: dict):
    """Run optimization task in background"""
    try:
        # Implementation for background optimization task
        logger.info(f"Running optimization task: {optimization_id}")
        # This would be implemented with actual optimization logic
        pass
    except Exception as e:
        logger.error(f"Optimization task failed: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 
