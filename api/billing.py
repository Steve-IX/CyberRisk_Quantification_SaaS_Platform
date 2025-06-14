"""
Billing Module - Enhanced Stripe integration for subscription management

This module provides comprehensive Stripe integration for handling subscriptions,
usage metering, webhook processing, and payment management for the CyberRisk SaaS platform.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import hmac
import hashlib
import json

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False

from .database import get_db_connection

logger = logging.getLogger(__name__)

# Stripe configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

if STRIPE_AVAILABLE and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Price IDs for each tier (these would be set in your Stripe dashboard)
STRIPE_PRICE_IDS = {
    "starter_monthly": os.getenv("STRIPE_STARTER_MONTHLY_PRICE_ID", "price_starter_monthly"),
    "starter_annual": os.getenv("STRIPE_STARTER_ANNUAL_PRICE_ID", "price_starter_annual"),
    "pro_monthly": os.getenv("STRIPE_PRO_MONTHLY_PRICE_ID", "price_pro_monthly"),
    "pro_annual": os.getenv("STRIPE_PRO_ANNUAL_PRICE_ID", "price_pro_annual"),
    "enterprise_monthly": os.getenv("STRIPE_ENTERPRISE_MONTHLY_PRICE_ID", "price_enterprise_monthly"),
    "enterprise_annual": os.getenv("STRIPE_ENTERPRISE_ANNUAL_PRICE_ID", "price_enterprise_annual"),
}


class SubscriptionTier(str, Enum):
    """Subscription tier enumeration."""
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class BillingService:
    """Enhanced Stripe billing service for subscription management."""
    
    def __init__(self):
        if not STRIPE_AVAILABLE:
            logger.warning("Stripe not available - using mock billing service")
        
        if not STRIPE_SECRET_KEY:
            logger.warning("Stripe secret key not configured - billing features disabled")
    
    async def get_usage_limits(self, tier: str) -> Dict[str, int]:
        """
        Get usage limits for a subscription tier.
        
        Args:
            tier: Subscription tier
            
        Returns:
            Usage limits dictionary
        """
        limits = {
            "starter": {
                "users": 2,
                "simulations_per_month": 50,
                "max_iterations": 50000,
                "pdf_downloads": 10,
                "api_calls_per_hour": 100,
                "optimization_runs": 5
            },
            "pro": {
                "users": 10,
                "simulations_per_month": 500,
                "max_iterations": 500000,
                "pdf_downloads": 100,
                "api_calls_per_hour": 1000,
                "optimization_runs": 100
            },
            "enterprise": {
                "users": 25,
                "simulations_per_month": -1,  # Unlimited
                "max_iterations": -1,
                "pdf_downloads": -1,
                "api_calls_per_hour": 10000,
                "optimization_runs": -1
            }
        }
        
        return limits.get(tier, limits["starter"])
    
    async def check_usage_limit(self, org_id: str, tier: str, usage_type: str) -> bool:
        """
        Check if organization is within usage limits.
        
        Args:
            org_id: Organization ID
            tier: Subscription tier
            usage_type: Type of usage to check
            
        Returns:
            True if within limits, False if exceeded
        """
        limits = await self.get_usage_limits(tier)
        limit = limits.get(usage_type)
        
        if limit == -1:  # Unlimited
            return True
        
        # Get current usage from database
        current_usage = await self._get_current_usage(org_id, usage_type)
        return current_usage < limit
    
    async def _get_current_usage(self, org_id: str, usage_type: str) -> int:
        """Get current usage for an organization this month."""
        query = """
        SELECT COUNT(*) as usage_count FROM usage_tracking 
        WHERE org_id = %s AND usage_type = %s 
        AND created_at >= DATE_TRUNC('month', CURRENT_DATE)
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (org_id, usage_type))
                result = await cursor.fetchone()
                return result['usage_count'] if result else 0
    
    async def record_usage(self, org_id: str, usage_type: str, 
                          quantity: int = 1, metadata: Dict[str, Any] = None) -> bool:
        """
        Record usage for billing and limit tracking.
        
        Args:
            org_id: Organization ID
            usage_type: Type of usage (simulations, pdf_downloads, etc.)
            quantity: Quantity used
            metadata: Additional metadata
            
        Returns:
            True if recorded successfully
        """
        try:
            query = """
            INSERT INTO usage_tracking (org_id, usage_type, quantity, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """
            
            async with get_db_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, (
                        org_id, usage_type, quantity, 
                        json.dumps(metadata) if metadata else None,
                        datetime.utcnow()
                    ))
                    await conn.commit()
            
            logger.info(f"Recorded {quantity} {usage_type} usage for org {org_id}")
            
            # Report usage to Stripe for metered billing if applicable
            await self._report_stripe_usage(org_id, usage_type, quantity)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record usage: {e}")
            return False
    
    async def _report_stripe_usage(self, org_id: str, usage_type: str, quantity: int):
        """Report usage to Stripe for metered billing."""
        if not STRIPE_AVAILABLE or not STRIPE_SECRET_KEY:
            return
        
        try:
            # Get subscription info for the organization
            subscription_info = await self._get_subscription_info(org_id)
            if not subscription_info or not subscription_info.get('stripe_subscription_id'):
                return
            
            # Report usage to Stripe (for usage-based add-ons)
            # This is a placeholder - in production you'd configure usage-based pricing
            pass
            
        except Exception as e:
            logger.error(f"Failed to report Stripe usage: {e}")
    
    async def create_checkout_session(self, customer_email: str, tier: str,
                                     annual: bool = False, 
                                     success_url: str = None,
                                     cancel_url: str = None,
                                     org_id: str = None) -> Dict[str, Any]:
        """
        Create a Stripe Checkout session for subscription signup.
        
        Args:
            customer_email: Customer email
            tier: Subscription tier
            annual: Annual billing
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL
            org_id: Organization ID for metadata
            
        Returns:
            Checkout session data
        """
        if not STRIPE_AVAILABLE or not STRIPE_SECRET_KEY:
            # Return mock data for development
            return self._create_mock_checkout_session(tier, annual)
        
        try:
            # Get the appropriate price ID
            price_key = f"{tier}_{'annual' if annual else 'monthly'}"
            price_id = STRIPE_PRICE_IDS.get(price_key)
            
            if not price_id:
                raise ValueError(f"Price ID not configured for {price_key}")
            
            # Create or retrieve customer
            customer = await self._create_or_get_customer(customer_email, org_id)
            
            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=customer.id,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url or 'https://your-domain.com/success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=cancel_url or 'https://your-domain.com/cancel',
                metadata={
                    'org_id': org_id,
                    'tier': tier,
                    'billing_cycle': 'annual' if annual else 'monthly'
                },
                subscription_data={
                    'metadata': {
                        'org_id': org_id,
                        'tier': tier
                    }
                }
            )
            
            return {
                "checkout_session_id": checkout_session.id,
                "checkout_url": checkout_session.url,
                "tier": tier,
                "billing_cycle": "annual" if annual else "monthly",
                "customer_id": customer.id
            }
            
        except Exception as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise
    
    async def _create_or_get_customer(self, email: str, org_id: str = None):
        """Create or retrieve a Stripe customer."""
        try:
            # Try to find existing customer
            customers = stripe.Customer.list(email=email, limit=1)
            if customers.data:
                return customers.data[0]
            
            # Create new customer
            customer = stripe.Customer.create(
                email=email,
                metadata={'org_id': org_id} if org_id else {}
            )
            
            return customer
            
        except Exception as e:
            logger.error(f"Failed to create/get customer: {e}")
            raise
    
    def _create_mock_checkout_session(self, tier: str, annual: bool) -> Dict[str, Any]:
        """Create mock checkout session for development."""
        tier_prices = {
            "starter": 49 if not annual else 490,
            "pro": 199 if not annual else 1990,
            "enterprise": 499 if not annual else 4990
        }
        
        return {
            "checkout_session_id": f"demo_{tier}_{int(datetime.now().timestamp())}",
            "checkout_url": f"https://demo.stripe.com/checkout?tier={tier}&price={tier_prices[tier]}",
            "tier": tier,
            "price": tier_prices[tier],
            "billing_cycle": "annual" if annual else "monthly"
        }
    
    async def handle_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Handle Stripe webhook events.
        
        Args:
            payload: Raw webhook payload
            signature: Stripe signature header
            
        Returns:
            Processing result
        """
        if not STRIPE_AVAILABLE or not STRIPE_WEBHOOK_SECRET:
            logger.warning("Stripe webhook handling not configured")
            return {"status": "ignored", "reason": "not_configured"}
        
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, signature, STRIPE_WEBHOOK_SECRET
            )
            
            # Handle different event types
            if event['type'] == 'checkout.session.completed':
                await self._handle_checkout_completed(event['data']['object'])
            elif event['type'] == 'customer.subscription.created':
                await self._handle_subscription_created(event['data']['object'])
            elif event['type'] == 'customer.subscription.updated':
                await self._handle_subscription_updated(event['data']['object'])
            elif event['type'] == 'customer.subscription.deleted':
                await self._handle_subscription_cancelled(event['data']['object'])
            elif event['type'] == 'invoice.payment_succeeded':
                await self._handle_payment_succeeded(event['data']['object'])
            elif event['type'] == 'invoice.payment_failed':
                await self._handle_payment_failed(event['data']['object'])
            
            return {"status": "processed", "event_type": event['type']}
            
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            raise
    
    async def _handle_checkout_completed(self, session):
        """Handle successful checkout completion."""
        org_id = session.get('metadata', {}).get('org_id')
        tier = session.get('metadata', {}).get('tier')
        
        if org_id and tier:
            # Update organization subscription status
            await self._update_organization_subscription(
                org_id, tier, session.get('subscription'), 'active'
            )
            
            logger.info(f"Checkout completed for org {org_id}, tier {tier}")
    
    async def _handle_subscription_created(self, subscription):
        """Handle subscription creation."""
        org_id = subscription.get('metadata', {}).get('org_id')
        tier = subscription.get('metadata', {}).get('tier')
        
        if org_id:
            await self._update_organization_subscription(
                org_id, tier, subscription['id'], subscription['status']
            )
    
    async def _handle_subscription_updated(self, subscription):
        """Handle subscription updates."""
        org_id = subscription.get('metadata', {}).get('org_id')
        
        if org_id:
            # Update subscription status and tier if needed
            await self._sync_subscription_status(org_id, subscription)
    
    async def _handle_subscription_cancelled(self, subscription):
        """Handle subscription cancellation."""
        org_id = subscription.get('metadata', {}).get('org_id')
        
        if org_id:
            await self._update_organization_subscription(
                org_id, None, subscription['id'], 'cancelled'
            )
    
    async def _handle_payment_succeeded(self, invoice):
        """Handle successful payment."""
        # Record successful payment and reset usage counters if needed
        pass
    
    async def _handle_payment_failed(self, invoice):
        """Handle failed payment."""
        # Notify organization of payment failure
        pass
    
    async def _update_organization_subscription(self, org_id: str, tier: str, 
                                              subscription_id: str, status: str):
        """Update organization subscription in database."""
        query = """
        UPDATE organizations 
        SET tier = %s, stripe_subscription_id = %s, subscription_status = %s, updated_at = %s
        WHERE id = %s
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (
                    tier, subscription_id, status, datetime.utcnow(), org_id
                ))
                await conn.commit()
    
    async def _sync_subscription_status(self, org_id: str, subscription):
        """Sync subscription status from Stripe."""
        # Implementation would sync all subscription details
        pass
    
    async def _get_subscription_info(self, org_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription information for an organization."""
        query = """
        SELECT tier, stripe_subscription_id, subscription_status 
        FROM organizations WHERE id = %s
        """
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, (org_id,))
                result = await cursor.fetchone()
                return dict(result) if result else None
    
    async def get_subscription_status(self, org_id: str) -> Dict[str, Any]:
        """
        Get detailed subscription status for an organization.
        
        Args:
            org_id: Organization ID
            
        Returns:
            Subscription status and usage information
        """
        subscription_info = await self._get_subscription_info(org_id)
        if not subscription_info:
            return {
                "tier": "starter",
                "status": "inactive",
                "usage": {},
                "limits": await self.get_usage_limits("starter")
            }
        
        tier = subscription_info.get('tier', 'starter')
        limits = await self.get_usage_limits(tier)
        
        # Get current usage for all tracked types
        usage = {}
        for usage_type in limits.keys():
            usage[usage_type] = await self._get_current_usage(org_id, usage_type)
        
        return {
            "tier": tier,
            "status": subscription_info.get('subscription_status', 'inactive'),
            "stripe_subscription_id": subscription_info.get('stripe_subscription_id'),
            "usage": usage,
            "limits": limits,
            "usage_percentage": {
                k: (usage[k] / v * 100) if v > 0 else 0 
                for k, v in limits.items() if v > 0
            }
        }


# Global billing service instance
billing_service = None

def get_billing_service() -> BillingService:
    """Get or create the global billing service instance."""
    global billing_service
    
    if billing_service is None:
        billing_service = BillingService()
    
    return billing_service


# Helper functions for common operations
async def check_usage_limit(org_id: str, tier: str, usage_type: str) -> bool:
    """Check if within usage limits."""
    service = get_billing_service()
    return await service.check_usage_limit(org_id, tier, usage_type)


async def record_simulation_usage(org_id: str, metadata: Dict[str, Any] = None) -> bool:
    """Record a simulation usage event."""
    service = get_billing_service()
    return await service.record_usage(org_id, "simulations", 1, metadata)


async def record_optimization_usage(org_id: str, metadata: Dict[str, Any] = None) -> bool:
    """Record an optimization usage event."""
    service = get_billing_service()
    return await service.record_usage(org_id, "optimization_runs", 1, metadata) 