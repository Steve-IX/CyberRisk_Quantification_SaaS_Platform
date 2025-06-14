"""
Authentication Module - JWT token validation and user management

This module provides authentication and authorization functionality
for the CyberRisk SaaS API using JWT tokens.
"""

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Dict, Optional
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security scheme
security = HTTPBearer()


class AuthError(HTTPException):
    """Custom authentication error."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_access_token(
        data: dict,
        expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token.

    Args:
        data: Dictionary containing user data to encode
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str) -> Dict:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        AuthError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Check if token has expired
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise AuthError("Token has expired")

        return payload

    except JWTError as e:
        raise AuthError(f"Invalid token: {str(e)}")


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Extract and validate current user from JWT token.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        User information dictionary

    Raises:
        AuthError: If authentication fails
    """
    token = credentials.credentials

    try:
        payload = verify_token(token)

        # Extract user information
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthError("Invalid token: missing user ID")

        # For demo purposes, return basic user info
        # In production, you'd fetch from database
        user_info = {
            "sub": user_id,
            "email": payload.get("email"),
            "org_id": payload.get("org_id"),
            "role": payload.get("role", "user"),
            "tier": payload.get("tier", "starter")
        }

        return user_info

    except AuthError:
        raise
    except Exception as e:
        raise AuthError(f"Authentication failed: {str(e)}")


def check_user_permissions(user: Dict, required_permission: str) -> bool:
    """
    Check if user has required permission.

    Args:
        user: User information dictionary
        required_permission: Permission string to check

    Returns:
        True if user has permission, False otherwise
    """
    user_role = user.get("role", "user")

    # Simple role-based permission system
    permissions = {
        "admin": ["*"],  # Admin has all permissions
        "analyst": ["simulate", "optimize", "view_reports"],
        "user": ["simulate", "view_reports"]
    }

    user_permissions = permissions.get(user_role, [])

    return "*" in user_permissions or required_permission in user_permissions


def check_usage_limits(user: Dict, operation: str) -> bool:
    """
    Check if user is within usage limits for their tier.

    Args:
        user: User information dictionary
        operation: Operation type (e.g., "simulation", "optimization")

    Returns:
        True if within limits, False otherwise
    """
    # In production, you'd check actual usage from database
    # For demo, we'll assume user is within limits
    return True


async def require_permission(permission: str):
    """
    Dependency to require specific permission.

    Args:
        permission: Required permission string

    Returns:
        Dependency function
    """
    async def permission_checker(
            user: Dict = Depends(get_current_user)) -> Dict:
        if not check_user_permissions(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: {permission} required"
            )
        return user

    return permission_checker


# Demo function to create a test token
def create_demo_token(
        user_id: str = "demo-user",
        email: str = "demo@example.com") -> str:
    """
    Create a demo token for testing purposes.

    Args:
        user_id: User ID
        email: User email

    Returns:
        JWT token for demo user
    """
    token_data = {
        "sub": user_id,
        "email": email,
        "org_id": "demo-org",
        "role": "analyst",
        "tier": "pro"
    }

    return create_access_token(token_data)


# Optional: Create a demo token for testing
if __name__ == "__main__":
    demo_token = create_demo_token()
    print(f"Demo token: {demo_token}")

    # Verify the token works
    try:
        payload = verify_token(demo_token)
        print(f"Token verified: {payload}")
    except AuthError as e:
        print(f"Token verification failed: {e.detail}")


async def check_rate_limit(user_id: int, endpoint: str) -> bool:
    """Check if user has exceeded rate limits"""
    try:
        # Get user's subscription tier to determine limits
        user = await get_user(user_id)
        subscription_tier = user.get('subscription_tier', 'free')

        # Define rate limits per tier (requests per hour)
        rate_limits = {
            'free': 10,
            'starter': 50,
            'professional': 200,
            'enterprise': 1000
        }

        # Check current usage
        current_usage = await get_current_usage(user_id, endpoint)
        limit = rate_limits.get(subscription_tier, 10)

        return current_usage < limit

    except Exception as e:
        logger.error(f"Rate limit check failed: {e}")
        return False


async def get_user(user_id: int) -> Dict:
    """Get user information by ID"""
    # Mock implementation for demo
    return {
        "id": user_id,
        "subscription_tier": "free",
        "email": f"user{user_id}@example.com"
    }


async def get_current_usage(user_id: int, endpoint: str) -> int:
    """Get current usage count for user and endpoint"""
    # Mock implementation for demo
    return 5  # Return some sample usage
