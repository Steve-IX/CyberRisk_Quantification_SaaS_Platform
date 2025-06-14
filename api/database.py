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
    """Create database tables if they don't exist."""
    if not database:
        return
    
    # Organizations table
    await database.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            tier VARCHAR(50) NOT NULL DEFAULT 'starter',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Users table
    await database.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID REFERENCES organizations(id),
            email VARCHAR(255) UNIQUE NOT NULL,
            role VARCHAR(50) DEFAULT 'user',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Assets table
    await database.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID REFERENCES organizations(id),
            name VARCHAR(255) NOT NULL,
            category VARCHAR(100),
            value_gbp DECIMAL(12,2),
            criticality INTEGER CHECK (criticality BETWEEN 1 AND 5),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Scenarios table
    await database.execute("""
        CREATE TABLE IF NOT EXISTS scenarios (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID REFERENCES organizations(id),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            threat_event VARCHAR(255),
            affected_assets UUID[],
            frequency_params JSONB,
            impact_params JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Simulation runs table
    await database.execute("""
        CREATE TABLE IF NOT EXISTS simulation_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            scenario_id UUID REFERENCES scenarios(id),
            user_id UUID REFERENCES users(id),
            status VARCHAR(50) DEFAULT 'pending',
            iterations INTEGER,
            parameters JSONB,
            results JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP,
            error_message TEXT
        )
    """)
    
    # Control optimizations table
    await database.execute("""
        CREATE TABLE IF NOT EXISTS control_optimizations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID REFERENCES organizations(id),
            user_id UUID REFERENCES users(id),
            name VARCHAR(255),
            parameters JSONB NOT NULL,
            results JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    logger.info("Database tables created successfully")


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