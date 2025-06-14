"""
Enterprise API Management & Security Module
Rate limiting, API keys, SSO, RBAC, audit logging, and enterprise integrations
Phase 4 Implementation
"""

import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from functools import wraps
import jwt
from fastapi import HTTPException, Request
import redis
from .database import get_db_connection

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User roles for RBAC"""
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    API_USER = "api_user"


class PermissionType(Enum):
    """Permission types for resources"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    BILLING = "billing"
    COMPLIANCE = "compliance"


@dataclass
class APIKey:
    """API key data structure"""
    key_id: str
    key_hash: str
    name: str
    organization_id: int
    user_id: int
    permissions: List[str]
    rate_limit: int
    created_at: datetime
    last_used: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: int


@dataclass
class AuditLog:
    """Audit log entry"""
    user_id: int
    organization_id: int
    action: str
    resource: str
    details: Dict[str, Any]
    ip_address: str
    user_agent: str
    timestamp: datetime
    status: str


class EnterpriseAPIManager:
    """Enterprise API management with security and rate limiting"""

    def __init__(self):
        # Initialize Redis for rate limiting and caching
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True
            )
        except BaseException:
            logger.warning("Redis not available - using in-memory fallback")
            self.redis_client = None

        # Rate limit configurations by subscription tier
        self.rate_limits = {
            'starter': RateLimitConfig(60, 1000, 10000, 10),
            'pro': RateLimitConfig(300, 10000, 100000, 50),
            'enterprise': RateLimitConfig(1000, 50000, 500000, 200)
        }

        # Permission matrix for roles
        self.role_permissions = {
            UserRole.SUPER_ADMIN: [
                p.value for p in PermissionType],
            UserRole.ORG_ADMIN: [
                PermissionType.READ.value,
                PermissionType.WRITE.value,
                PermissionType.DELETE.value,
                PermissionType.BILLING.value,
                PermissionType.COMPLIANCE.value],
            UserRole.ANALYST: [
                PermissionType.READ.value,
                PermissionType.WRITE.value,
                PermissionType.COMPLIANCE.value],
            UserRole.VIEWER: [
                PermissionType.READ.value],
            UserRole.API_USER: [
                PermissionType.READ.value,
                PermissionType.WRITE.value]}

        # JWT settings
        self.jwt_secret = "your-jwt-secret-key"  # Should be from environment
        self.jwt_algorithm = "HS256"
        self.jwt_expire_hours = 24

    async def generate_api_key(self,
                               organization_id: int,
                               user_id: int,
                               name: str,
                               permissions: List[str],
                               expires_days: Optional[int] = None) -> Tuple[str,
                                                                            APIKey]:
        """Generate a new API key for organization"""

        # Generate secure API key
        key = f"cyberisk_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_id = secrets.token_urlsafe(16)

        # Set expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        # Get organization's rate limit
        org_tier = await self._get_organization_tier(organization_id)
        rate_limit = self.rate_limits.get(
            org_tier, self.rate_limits['starter'])

        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            organization_id=organization_id,
            user_id=user_id,
            permissions=permissions,
            rate_limit=rate_limit.requests_per_hour,
            created_at=datetime.utcnow(),
            last_used=None,
            expires_at=expires_at,
            is_active=True
        )

        # Store in database
        await self._store_api_key(api_key)

        # Log API key creation
        await self.log_audit_event(
            user_id=user_id,
            organization_id=organization_id,
            action="api_key_created",
            resource=f"api_key:{key_id}",
            details={"name": name, "permissions": permissions},
            ip_address="system",
            user_agent="system"
        )

        return key, api_key

    async def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """Validate API key and return associated data"""

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        try:
            async with get_db_connection() as conn:
                query = """
                    SELECT key_id, key_hash, name, organization_id, user_id,
                           permissions, rate_limit, created_at, last_used,
                           expires_at, is_active
                    FROM api_keys
                    WHERE key_hash = $1 AND is_active = true
                """

                result = await conn.fetchrow(query, key_hash)

                if not result:
                    return None

                # Check expiration
                if result['expires_at'] and datetime.utcnow(
                ) > result['expires_at']:
                    await self._deactivate_api_key(result['key_id'])
                    return None

                # Update last used timestamp
                await self._update_api_key_usage(result['key_id'])

                return APIKey(**dict(result))

        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return None

    async def check_rate_limit(
            self,
            api_key_data: APIKey,
            endpoint: str) -> bool:
        """Check if request is within rate limits"""

        if not self.redis_client:
            # Fallback: allow all requests if Redis unavailable
            return True

        current_time = datetime.utcnow()
        key_prefix = f"rate_limit:{api_key_data.key_id}"

        # Different time windows
        minute_key = f"{key_prefix}:minute:{
            current_time.strftime('%Y%m%d%H%M')}"
        hour_key = f"{key_prefix}:hour:{current_time.strftime('%Y%m%d%H')}"
        day_key = f"{key_prefix}:day:{current_time.strftime('%Y%m%d')}"

        # Get organization's rate limits
        org_tier = await self._get_organization_tier(api_key_data.organization_id)
        limits = self.rate_limits.get(org_tier, self.rate_limits['starter'])

        try:
            # Check and increment counters
            pipe = self.redis_client.pipeline()
            pipe.incr(minute_key)
            pipe.expire(minute_key, 60)
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600)
            pipe.incr(day_key)
            pipe.expire(day_key, 86400)

            results = pipe.execute()

            minute_count = results[0]
            hour_count = results[2]
            day_count = results[4]

            # Check limits
            if minute_count > limits.requests_per_minute:
                return False
            if hour_count > limits.requests_per_hour:
                return False
            if day_count > limits.requests_per_day:
                return False

            return True

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Allow on error

    async def check_permission(self, user_role: UserRole,
                               permission: PermissionType,
                               resource: str = None) -> bool:
        """Check if user role has required permission"""

        required_permissions = self.role_permissions.get(user_role, [])
        return permission.value in required_permissions

    async def generate_jwt_token(
            self,
            user_id: int,
            organization_id: int,
            role: UserRole,
            permissions: List[str]) -> str:
        """Generate JWT token for user authentication"""

        payload = {
            'user_id': user_id,
            'organization_id': organization_id,
            'role': role.value,
            'permissions': permissions,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=self.jwt_expire_hours)
        }

        token = jwt.encode(
            payload,
            self.jwt_secret,
            algorithm=self.jwt_algorithm)
        return token

    async def validate_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return payload"""

        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[
                    self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return None

    async def log_audit_event(self,
                              user_id: int,
                              organization_id: int,
                              action: str,
                              resource: str,
                              details: Dict[str,
                                            Any],
                              ip_address: str,
                              user_agent: str,
                              status: str = "success"):
        """Log audit event for compliance and security monitoring"""

        audit_entry = AuditLog(
            user_id=user_id,
            organization_id=organization_id,
            action=action,
            resource=resource,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
            status=status
        )

        try:
            async with get_db_connection() as conn:
                query = """
                    INSERT INTO audit_logs
                    (user_id, organization_id, action, resource, details,
                     ip_address, user_agent, timestamp, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """

                await conn.execute(
                    query,
                    user_id, organization_id, action, resource,
                    json.dumps(details), ip_address, user_agent,
                    audit_entry.timestamp, status
                )

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")

    async def get_audit_logs(self, organization_id: int,
                             start_date: datetime, end_date: datetime,
                             user_id: Optional[int] = None,
                             action: Optional[str] = None) -> List[AuditLog]:
        """Retrieve audit logs for organization"""

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
                    SELECT user_id, organization_id, action, resource, details,
                           ip_address, user_agent, timestamp, status
                    FROM audit_logs
                    WHERE {' AND '.join(conditions)}
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """

                results = await conn.fetch(query, *params)

                audit_logs = []
                for row in results:
                    audit_logs.append(AuditLog(
                        user_id=row['user_id'],
                        organization_id=row['organization_id'],
                        action=row['action'],
                        resource=row['resource'],
                        details=json.loads(row['details']),
                        ip_address=row['ip_address'],
                        user_agent=row['user_agent'],
                        timestamp=row['timestamp'],
                        status=row['status']
                    ))

                return audit_logs

        except Exception as e:
            logger.error(f"Error retrieving audit logs: {e}")
            return []

    async def setup_sso_integration(
            self, organization_id: int, provider: str, config: Dict[str, Any]) -> bool:
        """Setup SSO integration for organization"""

        try:
            async with get_db_connection() as conn:
                query = """
                    INSERT INTO sso_configurations
                    (organization_id, provider, config, created_at, is_active)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (organization_id, provider)
                    DO UPDATE SET config = $3, updated_at = $4
                """

                await conn.execute(
                    query,
                    organization_id, provider, json.dumps(config),
                    datetime.utcnow(), True
                )

                return True

        except Exception as e:
            logger.error(f"Error setting up SSO integration: {e}")
            return False

    async def _get_organization_tier(self, organization_id: int) -> str:
        """Get organization's subscription tier"""

        try:
            async with get_db_connection() as conn:
                query = """
                    SELECT subscription_tier
                    FROM organizations
                    WHERE id = $1
                """

                result = await conn.fetchval(query, organization_id)
                return result or 'starter'

        except Exception as e:
            logger.error(f"Error getting organization tier: {e}")
            return 'starter'

    async def _store_api_key(self, api_key: APIKey):
        """Store API key in database"""

        async with get_db_connection() as conn:
            query = """
                INSERT INTO api_keys
                (key_id, key_hash, name, organization_id, user_id, permissions,
                 rate_limit, created_at, expires_at, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """

            await conn.execute(
                query,
                api_key.key_id, api_key.key_hash, api_key.name,
                api_key.organization_id, api_key.user_id,
                json.dumps(api_key.permissions), api_key.rate_limit,
                api_key.created_at, api_key.expires_at, api_key.is_active
            )

    async def _update_api_key_usage(self, key_id: str):
        """Update API key last used timestamp"""

        try:
            async with get_db_connection() as conn:
                query = """
                    UPDATE api_keys
                    SET last_used = $1
                    WHERE key_id = $2
                """

                await conn.execute(query, datetime.utcnow(), key_id)

        except Exception as e:
            logger.error(f"Error updating API key usage: {e}")

    async def _deactivate_api_key(self, key_id: str):
        """Deactivate expired API key"""

        try:
            async with get_db_connection() as conn:
                query = """
                    UPDATE api_keys
                    SET is_active = false
                    WHERE key_id = $1
                """

                await conn.execute(query, key_id)

        except Exception as e:
            logger.error(f"Error deactivating API key: {e}")


# Global enterprise API manager instance
enterprise_api_manager = EnterpriseAPIManager()


def get_enterprise_api_manager() -> EnterpriseAPIManager:
    """Get the global enterprise API manager instance"""
    return enterprise_api_manager

# Decorators for API protection


def require_api_key(permission: PermissionType = PermissionType.READ):
    """Decorator to require valid API key with specific permission"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get API key from header
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                raise HTTPException(status_code=401, detail="API key required")

            # Validate API key
            api_key_data = await enterprise_api_manager.validate_api_key(api_key)
            if not api_key_data:
                raise HTTPException(status_code=401, detail="Invalid API key")

            # Check rate limits
            endpoint = request.url.path
            if not await enterprise_api_manager.check_rate_limit(api_key_data, endpoint):
                raise HTTPException(
                    status_code=429, detail="Rate limit exceeded")

            # Check permissions
            if permission.value not in api_key_data.permissions:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions")

            # Add API key data to request state
            request.state.api_key_data = api_key_data

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_role(role: UserRole):
    """Decorator to require specific user role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get JWT token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(
                    status_code=401,
                    detail="Authorization header required")

            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authorization header format")

            # Validate JWT token
            payload = await enterprise_api_manager.validate_jwt_token(token)
            if not payload:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token")

            # Check role
            user_role = UserRole(payload.get('role'))
            if user_role != role and user_role != UserRole.SUPER_ADMIN:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient role privileges")

            # Add user data to request state
            request.state.user_data = payload

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
