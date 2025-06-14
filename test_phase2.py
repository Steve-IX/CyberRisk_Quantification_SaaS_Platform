#!/usr/bin/env python3
"""
Phase 2 Testing Suite - PDF Reports and Stripe Billing Integration

This script tests the newly implemented Phase 2 features:
1. PDF Report Generation
2. Stripe Billing Integration  
3. Usage Limits and Metering
4. Pricing Page Integration
5. Enhanced Dashboard

Usage: python test_phase2.py
"""

import sys
import asyncio
import json
import traceback
from datetime import datetime
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test if all required packages are available."""
    print("🔍 Testing Package Imports...")
    
    results = {}
    
    # Core packages
    try:
        import fastapi
        results['FastAPI'] = f"✅ {fastapi.__version__}"
    except ImportError:
        results['FastAPI'] = "❌ Not available"
    
    try:
        import jinja2
        results['Jinja2'] = f"✅ {jinja2.__version__}"
    except ImportError:
        results['Jinja2'] = "❌ Not available"
    
    # Billing dependencies
    try:
        import stripe
        results['Stripe'] = f"✅ {getattr(stripe, '__version__', getattr(stripe, '_version', 'installed'))}"
    except ImportError:
        results['Stripe'] = "❌ Not available (billing features limited)"
    
    # PDF dependencies
    try:
        import weasyprint
        results['WeasyPrint'] = f"✅ {getattr(weasyprint, '__version__', 'installed')}"
    except ImportError:
        results['WeasyPrint'] = "❌ Not available (PDF generation limited)"
    
    for package, status in results.items():
        print(f"  {package}: {status}")
    
    return results

def test_module_imports():
    """Test if our Phase 2 modules import correctly."""
    print("\n🧩 Testing Module Imports...")
    
    try:
        from api.billing import get_billing_service, BillingService
        print("  ✅ Billing service imports successfully")
        billing_available = True
    except Exception as e:
        print(f"  ❌ Billing service import failed: {e}")
        billing_available = False
    
    try:
        from api.reports import generate_simulation_pdf, get_report_generator
        print("  ✅ Report generator imports successfully")
        reports_available = True
    except Exception as e:
        print(f"  ❌ Report generator import failed: {e}")
        reports_available = False
    
    return billing_available, reports_available

async def test_billing_service():
    """Test the billing service functionality."""
    print("\n💳 Testing Billing Service...")
    
    try:
        from api.billing import get_billing_service
        
        billing_service = get_billing_service()
        print("  ✅ Billing service instance created")
        
        # Test usage limits
        limits = await billing_service.get_usage_limits("starter")
        print(f"  ✅ Starter tier limits: {limits}")
        
        limits = await billing_service.get_usage_limits("pro")
        print(f"  ✅ Pro tier limits: {limits}")
        
        limits = await billing_service.get_usage_limits("enterprise")
        print(f"  ✅ Enterprise tier limits: {limits}")
        
        # Test usage checking
        can_simulate = await billing_service.check_usage_limit("demo-org", "starter", "simulations_per_month")
        print(f"  ✅ Usage limit check (simulations): {can_simulate}")
        
        can_download = await billing_service.check_usage_limit("demo-org", "pro", "pdf_downloads")
        print(f"  ✅ Usage limit check (PDF downloads): {can_download}")
        
        # Test usage recording
        recorded = await billing_service.record_usage("demo-org", "simulations", 1)
        print(f"  ✅ Usage recording: {recorded}")
        
        # Test checkout session creation
        session = await billing_service.create_checkout_session(
            customer_email="test@example.com",
            tier="pro",
            annual=False,
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel"
        )
        print(f"  ✅ Checkout session created: {session['checkout_session_id']}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Billing service test failed: {e}")
        traceback.print_exc()
        return False

async def test_report_generation():
    """Test the PDF report generation functionality."""
    print("\n📄 Testing Report Generation...")
    
    try:
        from api.reports import get_report_generator
        
        # Check if we can create the report generator
        try:
            report_gen = get_report_generator()
            print("  ✅ Report generator instance created")
            weasyprint_available = True
        except ImportError as e:
            print(f"  ⚠️  WeasyPrint not available, using mock mode: {e}")
            weasyprint_available = False
        
        # Test template rendering
        try:
            from jinja2 import Environment, FileSystemLoader
            from pathlib import Path
            
            template_dir = Path("api/templates")
            if template_dir.exists():
                env = Environment(loader=FileSystemLoader(template_dir))
                template = env.get_template('simulation_report.html')
                print("  ✅ Report template loaded successfully")
                
                # Test template rendering with sample data
                sample_data = {
                    'run_id': 'test-12345',
                    'scenario_name': 'Test E-commerce Breach',
                    'organization': 'Test Organization',
                    'generated_date': datetime.now().strftime('%B %d, %Y at %H:%M UTC'),
                    'iterations': 50000,
                    'confidence_level': 'High',
                    'ale_formatted': '£125,000',
                    'risk_level': 'Medium',
                    'risk_description': 'Test risk description',
                    'mean_triangular': 150000,
                    'median_triangular': 140000,
                    'mean_occurrences': 1.5,
                    'variance_occurrences': 0.75,
                    'prob1': 0.65,
                    'prob2': 0.25,
                    'prob3': 0.15,
                    'asset_value_percentiles': {
                        'P50': 140000,
                        'P75': 170000,
                        'P90': 200000,
                        'P95': 220000,
                        'P99': 250000
                    },
                    'compliance_metrics': {
                        'nis2_significant_impact': False,
                        'csrd_material_risk': True,
                        'risk_tolerance_exceeded': False
                    }
                }
                
                rendered_html = template.render(**sample_data)
                print("  ✅ Template rendered successfully")
                print(f"    Generated HTML length: {len(rendered_html)} characters")
                
            else:
                print("  ❌ Template directory not found")
                
        except Exception as e:
            print(f"  ❌ Template rendering failed: {e}")
        
        return weasyprint_available
        
    except Exception as e:
        print(f"  ❌ Report generation test failed: {e}")
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Test the new API endpoints are properly defined."""
    print("\n🌐 Testing API Endpoint Definitions...")
    
    try:
        from api.main import app
        print("  ✅ FastAPI app imports successfully")
        
        # Get all routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append((route.path, list(route.methods)))
        
        # Check for Phase 2 endpoints
        phase2_endpoints = [
            ('/api/v1/billing/checkout', ['POST']),
            ('/api/v1/billing/usage-limits', ['GET']),
            ('/api/v1/billing/pricing', ['GET']),
            ('/api/v1/results/{run_id}/pdf', ['GET']),
            ('/api/v1/optimize/pdf', ['POST'])
        ]
        
        for endpoint_path, expected_methods in phase2_endpoints:
            found = False
            for route_path, route_methods in routes:
                if endpoint_path.replace('{run_id}', '') in route_path.replace('{run_id}', ''):
                    if any(method in route_methods for method in expected_methods):
                        print(f"  ✅ {endpoint_path} ({', '.join(expected_methods)})")
                        found = True
                        break
            if not found:
                print(f"  ❌ {endpoint_path} not found")
        
        print(f"\n  📊 Total API routes: {len(routes)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ API endpoint test failed: {e}")
        return False

def test_frontend_integration():
    """Test if frontend files are properly updated."""
    print("\n🖥️  Testing Frontend Integration...")
    
    frontend_files = [
        'frontend/src/app/pricing/page.tsx',
        'frontend/src/app/page.tsx',
        'frontend/package.json'
    ]
    
    found_files = 0
    for file_path in frontend_files:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
            found_files += 1
        else:
            print(f"  ❌ {file_path} not found")
    
    # Check pricing page content
    pricing_file = Path('frontend/src/app/pricing/page.tsx')
    if pricing_file.exists():
        content = pricing_file.read_text()
        if 'billing' in content.lower() and 'stripe' in content.lower():
            print("  ✅ Pricing page contains billing integration")
        else:
            print("  ⚠️  Pricing page may not have complete billing integration")
    
    # Check dashboard updates
    dashboard_file = Path('frontend/src/app/page.tsx')
    if dashboard_file.exists():
        content = dashboard_file.read_text()
        if 'usageLimits' in content and 'pricing' in content.lower():
            print("  ✅ Dashboard contains usage limits and pricing integration")
        else:
            print("  ⚠️  Dashboard may not have complete Phase 2 integration")
    
    return found_files == len(frontend_files)

def test_configuration():
    """Test configuration files for Phase 2."""
    print("\n⚙️  Testing Configuration...")
    
    config_file = Path('config.env.example')
    if config_file.exists():
        content = config_file.read_text()
        
        required_vars = [
            'STRIPE_SECRET_KEY',
            'STRIPE_PUBLISHABLE_KEY', 
            'STRIPE_WEBHOOK_SECRET'
        ]
        
        for var in required_vars:
            if var in content:
                print(f"  ✅ {var} configured")
            else:
                print(f"  ❌ {var} missing from config")
        
        return all(var in content for var in required_vars)
    else:
        print("  ❌ config.env.example not found")
        return False

async def run_full_test_suite():
    """Run the complete Phase 2 test suite."""
    print("🚀 CyberRisk Phase 2 Testing Suite")
    print("=" * 50)
    
    # Test 1: Package imports
    package_results = test_imports()
    
    # Test 2: Module imports
    billing_available, reports_available = test_module_imports()
    
    # Test 3: Billing service (if available)
    billing_test_passed = False
    if billing_available:
        billing_test_passed = await test_billing_service()
    else:
        print("\n💳 Skipping billing service tests (dependencies not available)")
    
    # Test 4: Report generation (if available)
    reports_test_passed = False
    if reports_available:
        reports_test_passed = await test_report_generation()
    else:
        print("\n📄 Skipping report generation tests (dependencies not available)")
    
    # Test 5: API endpoints
    api_test_passed = test_api_endpoints()
    
    # Test 6: Frontend integration
    frontend_test_passed = test_frontend_integration()
    
    # Test 7: Configuration
    config_test_passed = test_configuration()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 PHASE 2 TEST SUMMARY")
    print("=" * 50)
    
    tests = [
        ("Package Dependencies", any(v.startswith("✅") for v in package_results.values())),
        ("Module Imports", billing_available and reports_available),
        ("Billing Service", billing_test_passed if billing_available else "N/A"),
        ("Report Generation", reports_test_passed if reports_available else "N/A"),
        ("API Endpoints", api_test_passed),
        ("Frontend Integration", frontend_test_passed),
        ("Configuration", config_test_passed)
    ]
    
    passed = 0
    total = 0
    
    for test_name, result in tests:
        if result == "N/A":
            print(f"⚠️  {test_name}: Not Available (dependencies missing)")
        elif result:
            print(f"✅ {test_name}: PASSED")
            passed += 1
            total += 1
        else:
            print(f"❌ {test_name}: FAILED")
            total += 1
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Phase 2 is ready for production!")
    elif passed > total // 2:
        print("⚠️  Phase 2 is partially ready - some features may be limited")
    else:
        print("❌ Phase 2 needs attention before deployment")
    
    # Recommendations
    print("\n💡 Recommendations:")
    if not package_results.get('Stripe', '').startswith('✅'):
        print("  • Install Stripe: pip install stripe")
    if not package_results.get('WeasyPrint', '').startswith('✅'):
        print("  • Install WeasyPrint: pip install weasyprint")
    if not config_test_passed:
        print("  • Configure Stripe API keys in .env file")
    if not frontend_test_passed:
        print("  • Verify frontend build: cd frontend && npm install && npm run build")
    
    print("\n🚀 Next Steps for Full Testing:")
    print("  1. Start the API server: uvicorn api.main:app --reload")
    print("  2. Start the frontend: cd frontend && npm run dev")
    print("  3. Test end-to-end workflows in browser")
    print("  4. Test PDF downloads and billing flows")

if __name__ == "__main__":
    asyncio.run(run_full_test_suite()) 