"""
Database Module - Async PostgreSQL database connection and operations

This module provides database connectivity and basic operations
for the CyberRisk SaaS platform using asyncpg and databases.
"""

import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

try:
    import asyncpg
except ImportError:
    asyncpg = None

DATABASE_URL = "postgresql://localhost:5432/cyberrisk"

logger = logging.getLogger(__name__)

database = None

# Database configuration
DATABASE_URL = DATABASE_URL

# Global database connection
database = None

if asyncpg:
    database = asyncpg.create_pool(DATABASE_URL)

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'cyberrisk',
    'user': 'postgres',
    'password': 'password'
}

TABLES = {
    'organizations': '''
        CREATE TABLE IF NOT EXISTS organizations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            industry VARCHAR(100),
            size VARCHAR(50),
            subscription_tier VARCHAR(50) DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''',
    'users': '''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            organization_id INTEGER REFERENCES organizations(id),
            role VARCHAR(50) DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''',
    'simulation_runs': '''
        CREATE TABLE IF NOT EXISTS simulation_runs (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER REFERENCES organizations(id),
            scenario_name VARCHAR(255),
            parameters JSONB,
            results JSONB,
            status VARCHAR(50) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    '''
}


async def init_db():
    """Initialize database with all required tables."""
    try:
        logger.info("Initializing database...")

        async with get_db_connection() as conn:
            # Create existing tables (Phase 1-3)
            for table_name, create_sql in TABLES.items():
                await conn.execute(create_sql)
                logger.info(f"Table '{table_name}' created/verified")

            # Create Phase 4 tables
            for table_name, create_sql in PHASE_4_TABLES.items():
                await conn.execute(create_sql)
                logger.info(f"Phase 4 table '{table_name}' created/verified")

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


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


async def update_simulation_status(
        run_id: str,
        status: str,
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
async def create_organization(name: str,
                              tier: str = "starter") -> Optional[str]:
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


async def create_user(
        email: str,
        org_id: str,
        role: str = "user") -> Optional[str]:
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


async def store_simulation_run(
        run_id: str, org_id: str, parameters: Dict[str, Any]) -> bool:
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


async def store_optimization_run(
        optimization_id: str, org_id: str, parameters: Dict[str, Any]) -> bool:
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

        logger.info(
            f"Stored optimization run {optimization_id} for org {org_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to store optimization run: {e}")
        return False


async def update_simulation_run(
        run_id: str, results: Dict[str, Any], status: str = 'completed') -> bool:
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


async def update_optimization_run(
        optimization_id: str, results: Dict[str, Any], status: str = 'completed') -> bool:
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

        logger.info(
            f"Updated optimization run {optimization_id} with status {status}")
        return True

    except Exception as e:
        logger.error(f"Failed to update optimization run: {e}")
        return False


# Phase 4: Additional table schemas for enterprise features

PHASE_4_TABLES = {
    "api_keys": """
        CREATE TABLE IF NOT EXISTS api_keys (
            key_id VARCHAR(255) PRIMARY KEY,
            key_hash VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL,
            permissions JSONB NOT NULL DEFAULT '[]',
            rate_limit INTEGER NOT NULL DEFAULT 1000,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_used TIMESTAMP WITH TIME ZONE,
            expires_at TIMESTAMP WITH TIME ZONE,
            is_active BOOLEAN DEFAULT TRUE
        );

        CREATE INDEX IF NOT EXISTS idx_api_keys_organization ON api_keys(organization_id);
        CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
        CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);
    """,

    "audit_logs": """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
            action VARCHAR(255) NOT NULL,
            resource VARCHAR(255) NOT NULL,
            details JSONB NOT NULL DEFAULT '{}',
            ip_address INET,
            user_agent TEXT,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            status VARCHAR(50) DEFAULT 'success'
        );

        CREATE INDEX IF NOT EXISTS idx_audit_logs_organization ON audit_logs(organization_id);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
    """,

    "threat_intelligence": """
        CREATE TABLE IF NOT EXISTS threat_intelligence (
            threat_id VARCHAR(255) PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            category VARCHAR(100) NOT NULL,
            severity VARCHAR(50) NOT NULL,
            confidence DECIMAL(3,2) DEFAULT 0.5,
            source VARCHAR(255) NOT NULL,
            indicators JSONB NOT NULL DEFAULT '[]',
            affected_industries JSONB NOT NULL DEFAULT '[]',
            affected_regions JSONB NOT NULL DEFAULT '[]',
            mitigation_advice JSONB NOT NULL DEFAULT '[]',
            references JSONB NOT NULL DEFAULT '[]',
            first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE,
            is_active BOOLEAN DEFAULT TRUE
        );

        CREATE INDEX IF NOT EXISTS idx_threat_intel_category ON threat_intelligence(category);
        CREATE INDEX IF NOT EXISTS idx_threat_intel_severity ON threat_intelligence(severity);
        CREATE INDEX IF NOT EXISTS idx_threat_intel_active ON threat_intelligence(is_active);
        CREATE INDEX IF NOT EXISTS idx_threat_intel_updated ON threat_intelligence(last_updated);
    """,

    "sso_configurations": """
        CREATE TABLE IF NOT EXISTS sso_configurations (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
            provider VARCHAR(100) NOT NULL,
            config JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            is_active BOOLEAN DEFAULT TRUE,
            UNIQUE(organization_id, provider)
        );

        CREATE INDEX IF NOT EXISTS idx_sso_config_organization ON sso_configurations(organization_id);
        CREATE INDEX IF NOT EXISTS idx_sso_config_provider ON sso_configurations(provider);
    """,

    "vulnerability_reports": """
        CREATE TABLE IF NOT EXISTS vulnerability_reports (
            scan_id VARCHAR(255) PRIMARY KEY,
            organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
            scan_type VARCHAR(100) NOT NULL,
            target_assets JSONB NOT NULL DEFAULT '[]',
            vulnerabilities_found INTEGER DEFAULT 0,
            critical_count INTEGER DEFAULT 0,
            high_count INTEGER DEFAULT 0,
            medium_count INTEGER DEFAULT 0,
            low_count INTEGER DEFAULT 0,
            scan_started TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            scan_completed TIMESTAMP WITH TIME ZONE,
            findings JSONB NOT NULL DEFAULT '[]',
            recommendations JSONB NOT NULL DEFAULT '[]'
        );

        CREATE INDEX IF NOT EXISTS idx_vuln_reports_organization ON vulnerability_reports(organization_id);
        CREATE INDEX IF NOT EXISTS idx_vuln_reports_type ON vulnerability_reports(scan_type);
        CREATE INDEX IF NOT EXISTS idx_vuln_reports_completed ON vulnerability_reports(scan_completed);
    """,

    "ai_model_cache": """
        CREATE TABLE IF NOT EXISTS ai_model_cache (
            id SERIAL PRIMARY KEY,
            model_type VARCHAR(100) NOT NULL,
            input_hash VARCHAR(255) NOT NULL,
            prediction_result JSONB NOT NULL,
            model_version VARCHAR(50) NOT NULL,
            confidence_score DECIMAL(5,4),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(model_type, input_hash)
        );

        CREATE INDEX IF NOT EXISTS idx_ai_cache_type ON ai_model_cache(model_type);
        CREATE INDEX IF NOT EXISTS idx_ai_cache_hash ON ai_model_cache(input_hash);
        CREATE INDEX IF NOT EXISTS idx_ai_cache_expires ON ai_model_cache(expires_at);
    """,

    "analytics_cache": """
        CREATE TABLE IF NOT EXISTS analytics_cache (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
            cache_key VARCHAR(255) NOT NULL,
            cache_data JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            UNIQUE(organization_id, cache_key)
        );

        CREATE INDEX IF NOT EXISTS idx_analytics_cache_org ON analytics_cache(organization_id);
        CREATE INDEX IF NOT EXISTS idx_analytics_cache_key ON analytics_cache(cache_key);
        CREATE INDEX IF NOT EXISTS idx_analytics_cache_expires ON analytics_cache(expires_at);
    """
}

# Phase 4: Additional helper functions for new tables


async def create_api_key_record(api_key_data: Dict[str, Any]) -> bool:
    """Create API key record in database"""
    try:
        async with get_db_connection() as conn:
            query = """
                INSERT INTO api_keys
                (key_id, key_hash, name, organization_id, user_id,
                 permissions, rate_limit, expires_at, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """
            await conn.execute(
                query,
                api_key_data['key_id'], api_key_data['key_hash'],
                api_key_data['name'], api_key_data['organization_id'],
                api_key_data['user_id'], json.dumps(api_key_data['permissions']),
                api_key_data['rate_limit'], api_key_data.get('expires_at'),
                api_key_data.get('is_active', True)
            )
            return True
    except Exception as e:
        logger.error(f"Error creating API key record: {e}")
        return False


async def get_api_key_by_hash(key_hash: str) -> Optional[Dict[str, Any]]:
    """Get API key data by hash"""
    try:
        async with get_db_connection() as conn:
            query = """
                SELECT * FROM api_keys
                WHERE key_hash = $1 AND is_active = true
            """
            result = await conn.fetchrow(query, key_hash)

            if result:
                api_key_data = dict(result)
                api_key_data['permissions'] = json.loads(
                    api_key_data['permissions'])
                return api_key_data
            return None
    except Exception as e:
        logger.error(f"Error getting API key: {e}")
        return None


async def create_audit_log(audit_data: Dict[str, Any]) -> bool:
    """Create audit log entry"""
    try:
        async with get_db_connection() as conn:
            query = """
                INSERT INTO audit_logs
                (user_id, organization_id, action, resource, details,
                 ip_address, user_agent, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            await conn.execute(
                query,
                audit_data['user_id'], audit_data['organization_id'],
                audit_data['action'], audit_data['resource'],
                json.dumps(audit_data['details']), audit_data.get('ip_address'),
                audit_data.get('user_agent'), audit_data.get('status', 'success')
            )
            return True
    except Exception as e:
        logger.error(f"Error creating audit log: {e}")
        return False


async def get_audit_logs(organization_id: int, start_date: datetime,
                         end_date: datetime, user_id: Optional[int] = None,
                         action: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get audit logs for organization"""
    try:
        async with get_db_connection() as conn:
            conditions = [
                "organization_id = $1",
                "timestamp BETWEEN $2 AND $3"]
            params = [organization_id, start_date, end_date]

            if user_id:
                conditions.append(f"user_id = ${len(params) + 1}")
                params.append(user_id)

            if action:
                conditions.append(f"action = ${len(params) + 1}")
                params.append(action)

            query = f"""
                SELECT * FROM audit_logs
                WHERE {' AND '.join(conditions)}
                ORDER BY timestamp DESC
                LIMIT 1000
            """

            results = await conn.fetch(query, *params)

            audit_logs = []
            for row in results:
                log_data = dict(row)
                log_data['details'] = json.loads(log_data['details'])
                audit_logs.append(log_data)

            return audit_logs
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        return []


async def store_threat_intelligence(threat_data: Dict[str, Any]) -> bool:
    """Store threat intelligence item"""
    try:
        async with get_db_connection() as conn:
            query = """
                INSERT INTO threat_intelligence
                (threat_id, title, description, category, severity, confidence,
                 source, indicators, affected_industries, affected_regions,
                 mitigation_advice, references, first_seen, last_updated,
                 expires_at, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (threat_id) DO UPDATE SET
                title = $2, description = $3, last_updated = $14, is_active = $16
            """
            await conn.execute(
                query,
                threat_data['threat_id'], threat_data['title'], threat_data['description'],
                threat_data['category'], threat_data['severity'], threat_data['confidence'],
                threat_data['source'], json.dumps(threat_data['indicators']),
                json.dumps(threat_data['affected_industries']),
                json.dumps(threat_data['affected_regions']),
                json.dumps(threat_data['mitigation_advice']),
                json.dumps(threat_data['references']),
                threat_data['first_seen'], threat_data['last_updated'],
                threat_data.get('expires_at'), threat_data.get('is_active', True)
            )
            return True
    except Exception as e:
        logger.error(f"Error storing threat intelligence: {e}")
        return False


async def get_threat_intelligence(organization_id: Optional[int] = None,
                                  category: Optional[str] = None,
                                  severity: Optional[str] = None,
                                  limit: int = 50) -> List[Dict[str, Any]]:
    """Get threat intelligence items"""
    try:
        async with get_db_connection() as conn:
            conditions = ["is_active = true"]
            params = []

            if category:
                conditions.append(f"category = ${len(params) + 1}")
                params.append(category)

            if severity:
                conditions.append(f"severity = ${len(params) + 1}")
                params.append(severity)

            # Add expiration check
            conditions.append("(expires_at IS NULL OR expires_at > NOW())")

            query = f"""
                SELECT * FROM threat_intelligence
                WHERE {' AND '.join(conditions)}
                ORDER BY severity DESC, last_updated DESC
                LIMIT ${len(params) + 1}
            """
            params.append(limit)

            results = await conn.fetch(query, *params)

            threats = []
            for row in results:
                threat_data = dict(row)
                # Parse JSON fields
                threat_data['indicators'] = json.loads(
                    threat_data['indicators'])
                threat_data['affected_industries'] = json.loads(
                    threat_data['affected_industries'])
                threat_data['affected_regions'] = json.loads(
                    threat_data['affected_regions'])
                threat_data['mitigation_advice'] = json.loads(
                    threat_data['mitigation_advice'])
                threat_data['references'] = json.loads(
                    threat_data['references'])
                threats.append(threat_data)

            return threats
    except Exception as e:
        logger.error(f"Error getting threat intelligence: {e}")
        return []


async def store_sso_configuration(organization_id: int, provider: str,
                                  config: Dict[str, Any]) -> bool:
    """Store SSO configuration"""
    try:
        async with get_db_connection() as conn:
            query = """
                INSERT INTO sso_configurations
                (organization_id, provider, config, is_active)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (organization_id, provider)
                DO UPDATE SET config = $3, updated_at = NOW(), is_active = $4
            """
            await conn.execute(
                query, organization_id, provider, json.dumps(config), True
            )
            return True
    except Exception as e:
        logger.error(f"Error storing SSO configuration: {e}")
        return False


async def get_sso_configuration(organization_id: int,
                                provider: str) -> Optional[Dict[str, Any]]:
    """Get SSO configuration"""
    try:
        async with get_db_connection() as conn:
            query = """
                SELECT * FROM sso_configurations
                WHERE organization_id = $1 AND provider = $2 AND is_active = true
            """
            result = await conn.fetchrow(query, organization_id, provider)

            if result:
                config_data = dict(result)
                config_data['config'] = json.loads(config_data['config'])
                return config_data
            return None
    except Exception as e:
        logger.error(f"Error getting SSO configuration: {e}")
        return None


async def store_vulnerability_report(report_data: Dict[str, Any]) -> bool:
    """Store vulnerability scan report"""
    try:
        async with get_db_connection() as conn:
            query = """
                INSERT INTO vulnerability_reports
                (scan_id, organization_id, scan_type, target_assets,
                 vulnerabilities_found, critical_count, high_count,
                 medium_count, low_count, scan_started, scan_completed,
                 findings, recommendations)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """
            await conn.execute(
                query,
                report_data['scan_id'], report_data['organization_id'],
                report_data['scan_type'], json.dumps(report_data['target_assets']),
                report_data['vulnerabilities_found'], report_data['critical_count'],
                report_data['high_count'], report_data['medium_count'],
                report_data['low_count'], report_data['scan_started'],
                report_data['scan_completed'], json.dumps(report_data['findings']),
                json.dumps(report_data['recommendations'])
            )
            return True
    except Exception as e:
        logger.error(f"Error storing vulnerability report: {e}")
        return False


async def cache_analytics_data(organization_id: int,
                               cache_key: str,
                               data: Dict[str,
                                          Any],
                               ttl_minutes: int = 60) -> bool:
    """Cache analytics data"""
    try:
        async with get_db_connection() as conn:
            expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)

            query = """
                INSERT INTO analytics_cache
                (organization_id, cache_key, cache_data, expires_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (organization_id, cache_key)
                DO UPDATE SET cache_data = $3, created_at = NOW(), expires_at = $4
            """
            await conn.execute(
                query, organization_id, cache_key, json.dumps(data), expires_at
            )
            return True
    except Exception as e:
        logger.error(f"Error caching analytics data: {e}")
        return False


async def get_cached_analytics_data(
        organization_id: int, cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached analytics data"""
    try:
        async with get_db_connection() as conn:
            query = """
                SELECT cache_data FROM analytics_cache
                WHERE organization_id = $1 AND cache_key = $2
                AND expires_at > NOW()
            """
            result = await conn.fetchval(query, organization_id, cache_key)

            if result:
                return json.loads(result)
            return None
    except Exception as e:
        logger.error(f"Error getting cached analytics data: {e}")
        return None


def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


def init_database():
    """Initialize database tables"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        for table_name, table_sql in TABLES.items():
            cursor.execute(table_sql)
        conn.commit()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        conn.close()


def run_optimization_task(optimization_id: str, parameters: dict):
    """Run optimization task in background"""
    # Implementation for background optimization task
    pass