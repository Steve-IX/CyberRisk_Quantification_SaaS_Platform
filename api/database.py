"""
Database Module - Async PostgreSQL database connection and operations

This module provides database connectivity and basic operations
for the CyberRisk SaaS platform using asyncpg and databases.
"""

import os
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging
import uuid

try:
    from databases import Database
    import asyncpg
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://user:password@localhost:5432/cyberrisk"
)

# Global database connection
database = None

if DATABASE_AVAILABLE:
    database = Database(DATABASE_URL)


async def init_db():
    """Initialize database connection and create tables if needed."""
    global database
    
    if not DATABASE_AVAILABLE:
        logger.warning("Database dependencies not available - using in-memory storage")
        return
    
    try:
        await database.connect()
        logger.info("Database connected successfully")
        
        # Create tables if they don't exist
        await create_tables()
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        # Fall back to in-memory storage
        database = None


async def disconnect_db():
    """Disconnect from database."""
    if database:
        await database.disconnect()
        logger.info("Database disconnected")


async def get_database():
    """Get database connection (dependency injection).""" 
    return database


async def create_tables():
    """Create all necessary database tables."""
    conn = await get_db_connection()
    
    try:
        # Organizations table with enhanced billing fields
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                tier VARCHAR(50) NOT NULL DEFAULT 'starter',
                stripe_customer_id VARCHAR(255),
                stripe_subscription_id VARCHAR(255),
                subscription_status VARCHAR(50) DEFAULT 'inactive',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                email VARCHAR(255) UNIQUE NOT NULL,
                role VARCHAR(50) DEFAULT 'analyst',
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Assets table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                value_gbp DECIMAL(12,2),
                criticality INTEGER CHECK (criticality BETWEEN 1 AND 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Scenarios table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS scenarios (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                threat_event VARCHAR(255),
                affected_assets UUID[],
                frequency_params JSONB,
                impact_params JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Simulation runs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS simulation_runs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                scenario_id UUID REFERENCES scenarios(id) ON DELETE SET NULL,
                parameters JSONB NOT NULL,
                results JSONB,
                status VARCHAR(50) DEFAULT 'pending',
                iterations INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)

        # Optimization runs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS optimization_runs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                optimization_name VARCHAR(255),
                parameters JSONB NOT NULL,
                results JSONB,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)

        # Usage tracking table for billing
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS usage_tracking (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                usage_type VARCHAR(100) NOT NULL,
                quantity INTEGER DEFAULT 1,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Compliance reports table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS compliance_reports (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
                report_type VARCHAR(100) NOT NULL, -- 'CSRD', 'NIS2', 'CUSTOM'
                simulation_run_id UUID REFERENCES simulation_runs(id) ON DELETE CASCADE,
                report_data JSONB NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                downloaded_at TIMESTAMP
            )
        """)

        # Create indexes for better performance
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_organizations_tier ON organizations(tier)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(org_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_simulation_runs_org_id ON simulation_runs(org_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_optimization_runs_org_id ON optimization_runs(org_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_tracking_org_type ON usage_tracking(org_id, usage_type)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_tracking_created_at ON usage_tracking(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_compliance_reports_org_type ON compliance_reports(org_id, report_type)")

        await conn.commit()
        logger.info("Database tables created successfully")
        
    except Exception as e:
        await conn.rollback()
        logger.error(f"Failed to create tables: {e}")
        raise
    finally:
        await conn.close()


# Database operations for simulations
async def save_simulation_run(run_id: str, user_id: str, scenario_data: Dict, 
                            iterations: int) -> Optional[str]:
    """Save a new simulation run to database."""
    if not database:
        return None
    
    try:
        query = """
            INSERT INTO simulation_runs (id, user_id, status, iterations, parameters)
            VALUES (:id, :user_id, :status, :iterations, :parameters)
        """
        
        await database.execute(query, {
            "id": run_id,
            "user_id": user_id,
            "status": "pending",
            "iterations": iterations,
            "parameters": json.dumps(scenario_data)
        })
        
        return run_id
        
    except Exception as e:
        logger.error(f"Failed to save simulation run: {e}")
        return None


async def update_simulation_status(run_id: str, status: str, 
                                 results: Optional[Dict] = None,
                                 error_message: Optional[str] = None) -> bool:
    """Update simulation run status and results."""
    if not database:
        return False
    
    try:
        if status == "completed":
            query = """
                UPDATE simulation_runs 
                SET status = :status, results = :results, completed_at = NOW()
                WHERE id = :run_id
            """
            await database.execute(query, {
                "status": status,
                "results": json.dumps(results) if results else None,
                "run_id": run_id
            })
        elif status == "failed":
            query = """
                UPDATE simulation_runs 
                SET status = :status, error_message = :error_message, completed_at = NOW()
                WHERE id = :run_id
            """
            await database.execute(query, {
                "status": status,
                "error_message": error_message,
                "run_id": run_id
            })
        else:
            query = """
                UPDATE simulation_runs 
                SET status = :status
                WHERE id = :run_id
            """
            await database.execute(query, {
                "status": status,
                "run_id": run_id
            })
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to update simulation status: {e}")
        return False


async def get_simulation_run(run_id: str) -> Optional[Dict]:
    """Get simulation run by ID."""
    if not database:
        return None
    
    try:
        query = "SELECT * FROM simulation_runs WHERE id = :run_id"
        row = await database.fetch_one(query, {"run_id": run_id})
        
        if row:
            return dict(row)
        return None
        
    except Exception as e:
        logger.error(f"Failed to get simulation run: {e}")
        return None


async def get_user_simulations(user_id: str, limit: int = 10, 
                             offset: int = 0) -> List[Dict]:
    """Get simulation runs for a user."""
    if not database:
        return []
    
    try:
        query = """
            SELECT id, status, iterations, created_at, completed_at, 
                   parameters->>'scenario_name' as scenario_name,
                   results->>'ale' as ale
            FROM simulation_runs 
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """
        
        rows = await database.fetch_all(query, {
            "user_id": user_id,
            "limit": limit,
            "offset": offset
        })
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"Failed to get user simulations: {e}")
        return []


async def delete_simulation_run(run_id: str, user_id: str) -> bool:
    """Delete a simulation run."""
    if not database:
        return False
    
    try:
        query = """
            DELETE FROM simulation_runs 
            WHERE id = :run_id AND user_id = :user_id
        """
        
        result = await database.execute(query, {
            "run_id": run_id,
            "user_id": user_id
        })
        
        return result > 0
        
    except Exception as e:
        logger.error(f"Failed to delete simulation run: {e}")
        return False


# Organization and user management
async def create_organization(name: str, tier: str = "starter") -> Optional[str]:
    """Create a new organization."""
    if not database:
        return None
    
    try:
        query = """
            INSERT INTO organizations (name, tier)
            VALUES (:name, :tier)
            RETURNING id
        """
        
        result = await database.fetch_one(query, {
            "name": name,
            "tier": tier
        })
        
        return str(result["id"]) if result else None
        
    except Exception as e:
        logger.error(f"Failed to create organization: {e}")
        return None


async def create_user(email: str, org_id: str, role: str = "user") -> Optional[str]:
    """Create a new user."""
    if not database:
        return None
    
    try:
        query = """
            INSERT INTO users (email, org_id, role)
            VALUES (:email, :org_id, :role)
            RETURNING id
        """
        
        result = await database.fetch_one(query, {
            "email": email,
            "org_id": org_id,
            "role": role
        })
        
        return str(result["id"]) if result else None
        
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        return None


async def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email address."""
    if not database:
        return None
    
    try:
        query = """
            SELECT u.*, o.name as org_name, o.tier as org_tier
            FROM users u
            JOIN organizations o ON u.org_id = o.id
            WHERE u.email = :email
        """
        
        row = await database.fetch_one(query, {"email": email})
        
        if row:
            return dict(row)
        return None
        
    except Exception as e:
        logger.error(f"Failed to get user by email: {e}")
        return None


# Health check
async def check_database_health() -> Dict[str, Any]:
    """Check database connection health."""
    if not database:
        return {
            "status": "unavailable",
            "message": "Database not configured or dependencies missing"
        }
    
    try:
        # Simple query to test connection
        await database.fetch_one("SELECT 1 as test")
        
        return {
            "status": "healthy",
            "message": "Database connection OK"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy", 
            "message": f"Database error: {str(e)}"
        }


async def store_simulation_run(run_id: str, org_id: str, parameters: Dict[str, Any]) -> bool:
    """
    Store a simulation run request in the database.
    
    Args:
        run_id: Unique simulation run identifier
        org_id: Organization ID
        parameters: Simulation parameters
        
    Returns:
        True if stored successfully
    """
    try:
        query = """
        INSERT INTO simulation_runs (id, org_id, parameters, status, iterations, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (
                    run_id,
                    org_id,
                    json.dumps(parameters),
                    'pending',
                    parameters.get('iterations', 10000),
                    datetime.utcnow()
                ))
                await conn.commit()
        
        logger.info(f"Stored simulation run {run_id} for org {org_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store simulation run: {e}")
        return False


async def store_optimization_run(optimization_id: str, org_id: str, parameters: Dict[str, Any]) -> bool:
    """
    Store an optimization run request in the database.
    
    Args:
        optimization_id: Unique optimization identifier
        org_id: Organization ID  
        parameters: Optimization parameters
        
    Returns:
        True if stored successfully
    """
    try:
        query = """
        INSERT INTO optimization_runs (id, org_id, optimization_name, parameters, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (
                    optimization_id,
                    org_id,
                    parameters.get('optimization_name', 'Optimization Run'),
                    json.dumps(parameters),
                    'pending',
                    datetime.utcnow()
                ))
                await conn.commit()
        
        logger.info(f"Stored optimization run {optimization_id} for org {org_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store optimization run: {e}")
        return False


async def update_simulation_run(run_id: str, results: Dict[str, Any], status: str = 'completed') -> bool:
    """
    Update a simulation run with results.
    
    Args:
        run_id: Simulation run identifier
        results: Simulation results
        status: Run status
        
    Returns:
        True if updated successfully
    """
    try:
        query = """
        UPDATE simulation_runs 
        SET results = %s, status = %s, completed_at = %s
        WHERE id = %s
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (
                    json.dumps(results),
                    status,
                    datetime.utcnow(),
                    run_id
                ))
                await conn.commit()
        
        logger.info(f"Updated simulation run {run_id} with status {status}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update simulation run: {e}")
        return False


async def update_optimization_run(optimization_id: str, results: Dict[str, Any], status: str = 'completed') -> bool:
    """
    Update an optimization run with results.
    
    Args:
        optimization_id: Optimization identifier
        results: Optimization results
        status: Run status
        
    Returns:
        True if updated successfully
    """
    try:
        query = """
        UPDATE optimization_runs 
        SET results = %s, status = %s, completed_at = %s
        WHERE id = %s
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (
                    json.dumps(results),
                    status,
                    datetime.utcnow(),
                    optimization_id
                ))
                await conn.commit()
        
        logger.info(f"Updated optimization run {optimization_id} with status {status}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update optimization run: {e}")
        return False


async def get_simulation_run(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a simulation run by ID.
    
    Args:
        run_id: Simulation run identifier
        
    Returns:
        Simulation run data or None
    """
    try:
        query = """
        SELECT id, org_id, parameters, results, status, iterations, created_at, completed_at
        FROM simulation_runs 
        WHERE id = %s
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (run_id,))
                result = await cursor.fetchone()
        
        if result:
            return dict(result)
        return None
        
    except Exception as e:
        logger.error(f"Failed to get simulation run: {e}")
        return None


async def get_optimization_run(optimization_id: str) -> Optional[Dict[str, Any]]:
    """
    Get an optimization run by ID.
    
    Args:
        optimization_id: Optimization identifier
        
    Returns:
        Optimization run data or None
    """
    try:
        query = """
        SELECT id, org_id, optimization_name, parameters, results, status, created_at, completed_at
        FROM optimization_runs 
        WHERE id = %s
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (optimization_id,))
                result = await cursor.fetchone()
        
        if result:
            return dict(result)
        return None
        
    except Exception as e:
        logger.error(f"Failed to get optimization run: {e}")
        return None


async def get_organization_runs(org_id: str, run_type: str = 'simulation', 
                              limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Get simulation or optimization runs for an organization.
    
    Args:
        org_id: Organization ID
        run_type: Type of runs ('simulation' or 'optimization')
        limit: Maximum number of results
        offset: Offset for pagination
        
    Returns:
        List of run records
    """
    try:
        if run_type == 'simulation':
            table = 'simulation_runs'
            fields = 'id, parameters, results, status, iterations, created_at, completed_at'
        else:
            table = 'optimization_runs'
            fields = 'id, optimization_name, parameters, results, status, created_at, completed_at'
        
        query = f"""
        SELECT {fields}
        FROM {table}
        WHERE org_id = %s
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (org_id, limit, offset))
                results = await cursor.fetchall()
        
        return [dict(result) for result in results]
        
    except Exception as e:
        logger.error(f"Failed to get organization runs: {e}")
        return []


async def create_organization(name: str, tier: str = 'starter') -> str:
    """
    Create a new organization.
    
    Args:
        name: Organization name
        tier: Subscription tier
        
    Returns:
        Organization ID
    """
    try:
        org_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO organizations (id, name, tier, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (
                    org_id,
                    name,
                    tier,
                    datetime.utcnow(),
                    datetime.utcnow()
                ))
                await conn.commit()
        
        logger.info(f"Created organization {org_id}: {name}")
        return org_id
        
    except Exception as e:
        logger.error(f"Failed to create organization: {e}")
        raise


async def get_organization(org_id: str) -> Optional[Dict[str, Any]]:
    """
    Get organization by ID.
    
    Args:
        org_id: Organization ID
        
    Returns:
        Organization data or None
    """
    try:
        query = """
        SELECT id, name, tier, stripe_customer_id, stripe_subscription_id, 
               subscription_status, created_at, updated_at
        FROM organizations 
        WHERE id = %s
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (org_id,))
                result = await cursor.fetchone()
        
        if result:
            return dict(result)
        return None
        
    except Exception as e:
        logger.error(f"Failed to get organization: {e}")
        return None


async def create_user(email: str, org_id: str, role: str = 'analyst') -> str:
    """
    Create a new user.
    
    Args:
        email: User email
        org_id: Organization ID
        role: User role
        
    Returns:
        User ID
    """
    try:
        user_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO users (id, org_id, email, role, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (
                    user_id,
                    org_id,
                    email,
                    role,
                    True,
                    datetime.utcnow(),
                    datetime.utcnow()
                ))
                await conn.commit()
        
        logger.info(f"Created user {user_id}: {email}")
        return user_id
        
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get user by email address.
    
    Args:
        email: User email
        
    Returns:
        User data with organization info or None
    """
    try:
        query = """
        SELECT u.id, u.email, u.role, u.is_active, u.created_at,
               o.id as org_id, o.name as org_name, o.tier as org_tier
        FROM users u
        JOIN organizations o ON u.org_id = o.id
        WHERE u.email = %s AND u.is_active = true
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (email,))
                result = await cursor.fetchone()
        
        if result:
            return dict(result)
        return None
        
    except Exception as e:
        logger.error(f"Failed to get user by email: {e}")
        return None 