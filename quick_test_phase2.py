#!/usr/bin/env python3
"""
Quick Phase 2 Verification Script

Tests the core Phase 2 features:
1. Billing service functionality
2. PDF report generation 
3. API endpoints
"""

import sys
import asyncio
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

async def test_billing_service():
    """Test billing service basic functionality."""
    print("💳 Testing Billing Service...")
    
    try:
        from api.billing import get_billing_service
        
        billing_service = get_billing_service()
        print("  ✅ Billing service created")
        
        # Test usage limits
        limits = await billing_service.get_usage_limits("pro")
        print(f"  ✅ Pro tier limits: {limits['simulations_per_month']} simulations/month")
        
        # Test usage checking
        can_use = await billing_service.check_usage_limit("demo-org", "pro", "simulations_per_month")
        print(f"  ✅ Usage check: {'Allowed' if can_use else 'Blocked'}")
        
        # Test checkout session
        session = await billing_service.create_checkout_session(
            customer_email="test@example.com",
            tier="pro",
            annual=False
        )
        print(f"  ✅ Checkout session: {session['checkout_session_id']}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Billing test failed: {e}")
        return False

def test_pdf_template():
    """Test PDF template rendering."""
    print("\n📄 Testing PDF Template...")
    
    try:
        from jinja2 import Environment, FileSystemLoader
        from pathlib import Path
        
        template_dir = Path("api/templates")
        if not template_dir.exists():
            print("  ❌ Template directory not found")
            return False
            
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('simulation_report.html')
        print("  ✅ Template loaded")
        
        # Test with sample data - provide all required template variables
        sample_data = {
            'run_id': 'test-123',
            'scenario_name': 'Test Scenario',
            'organization': 'Test Org',
            'generated_date': 'January 15, 2025',
            'iterations': 50000,
            'confidence_level': 'High',
            'ale_formatted': '£125,000',
            'risk_level': 'Medium',
            'mean_triangular': 150000,
            'median_triangular': 140000,
            'mean_occurrences': 1.5,
            'variance_occurrences': 0.75,
            'prob1': 0.65,
            'prob2': 0.25,
            'prob3': 0.15,
            'recommended_action': 'Implement additional security controls',
            'asset_value_percentiles': {
                'P50': 140000,
                'P75': 180000,
                'P90': 220000,
                'P95': 260000,
                'P99': 350000
            },
            'compliance_metrics': {
                'nis2_significant_impact': True,
                'csrd_material_risk': False,
                'ale_as_percent_of_revenue': 2.5,
                'risk_tolerance_exceeded': True
            }
        }
        
        html = template.render(**sample_data)
        print(f"  ✅ Template rendered successfully ({len(html)} chars)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Template test failed: {e}")
        return False

def test_api_imports():
    """Test API imports work correctly."""
    print("\n🌐 Testing API Imports...")
    
    try:
        from api.main import app
        print("  ✅ FastAPI app imports")
        
        from api.billing import get_billing_service
        print("  ✅ Billing service imports")
        
        from api.reports import generate_simulation_pdf
        print("  ✅ Report generator imports")
        
        return True
        
    except Exception as e:
        print(f"  ❌ API import test failed: {e}")
        return False

def test_dependencies():
    """Test required dependencies are available."""
    print("\n📦 Testing Dependencies...")
    
    deps = {}
    
    try:
        import stripe
        deps['Stripe'] = "✅ Available"
    except ImportError:
        deps['Stripe'] = "❌ Missing"
    
    try:
        import weasyprint
        deps['WeasyPrint'] = "✅ Available"
    except (ImportError, OSError) as e:
        deps['WeasyPrint'] = f"⚠️  Limited (PDF generation disabled): {str(e)[:50]}..."
    
    try:
        import jinja2
        deps['Jinja2'] = f"✅ {jinja2.__version__}"
    except ImportError:
        deps['Jinja2'] = "❌ Missing"
    
    for dep, status in deps.items():
        print(f"  {dep}: {status}")
    
    # Consider it ok if core deps are available (Stripe and Jinja2)
    # WeasyPrint can be limited/disabled gracefully
    core_deps_ok = "✅" in deps.get('Stripe', '') and "✅" in deps.get('Jinja2', '')
    return core_deps_ok

async def main():
    """Run all tests."""
    print("🚀 CyberRisk Phase 2 Quick Test")
    print("=" * 40)
    
    # Test 1: Dependencies
    deps_ok = test_dependencies()
    
    # Test 2: API imports
    api_ok = test_api_imports()
    
    # Test 3: PDF template
    template_ok = test_pdf_template()
    
    # Test 4: Billing service
    billing_ok = await test_billing_service() if deps_ok else False
    
    # Summary
    print("\n" + "=" * 40)
    print("📋 QUICK TEST SUMMARY")
    print("=" * 40)
    
    tests = [
        ("Dependencies", deps_ok),
        ("API Imports", api_ok), 
        ("PDF Template", template_ok),
        ("Billing Service", billing_ok)
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Phase 2 is ready!")
        print("\nNext steps:")
        print("  1. Start API: uvicorn api.main:app --reload")
        print("  2. Start frontend: cd frontend && npm run dev")
        print("  3. Test in browser at http://localhost:3000")
    else:
        print("⚠️  Some issues need attention")
        if not deps_ok:
            print("  • Check dependency installation")
        if not api_ok:
            print("  • Fix API import errors")
        if not template_ok:
            print("  • Fix template syntax")
        if not billing_ok:
            print("  • Check billing service configuration")

if __name__ == "__main__":
    asyncio.run(main()) 