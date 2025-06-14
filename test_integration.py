#!/usr/bin/env python3
"""
Quick Integration Test for Phase 2 API Endpoints

Tests that the API server starts and responds correctly to requests.
"""

import asyncio
import json
import time
from urllib.request import urlopen
from urllib.error import URLError

async def test_api_health():
    """Test that the API server is running and healthy."""
    print("🔍 Testing API Health...")
    
    max_retries = 10
    for i in range(max_retries):
        try:
            with urlopen("http://localhost:8001/api/v1/health", timeout=5) as response:
                data = json.loads(response.read().decode())
                print(f"  ✅ API Health: {data.get('status', 'Unknown')}")
                return True
        except URLError:
            print(f"  ⏳ Waiting for API server... ({i+1}/{max_retries})")
            time.sleep(2)
    
    print("  ❌ API server not responding")
    return False

async def test_billing_endpoints():
    """Test billing endpoints are accessible."""
    print("\n💳 Testing Billing Endpoints...")
    
    endpoints = [
        "/api/v1/billing/pricing-tiers",
        "/api/v1/billing/usage-limits"
    ]
    
    passed = 0
    for endpoint in endpoints:
        try:
            with urlopen(f"http://localhost:8001{endpoint}", timeout=5) as response:
                if response.getcode() == 200:
                    print(f"  ✅ {endpoint} - OK")
                    passed += 1
                else:
                    print(f"  ❌ {endpoint} - HTTP {response.getcode()}")
        except URLError as e:
            print(f"  ❌ {endpoint} - {e}")
    
    return passed == len(endpoints)

async def test_api_docs():
    """Test that API documentation is accessible."""
    print("\n📚 Testing API Documentation...")
    
    try:
        with urlopen("http://localhost:8001/docs", timeout=5) as response:
            if response.getcode() == 200:
                print("  ✅ Swagger docs accessible at http://localhost:8001/docs")
                return True
            else:
                print(f"  ❌ Docs returned HTTP {response.getcode()}")
                return False
    except URLError as e:
        print(f"  ❌ Docs not accessible: {e}")
        return False

async def main():
    """Run integration tests."""
    print("🚀 CyberRisk Phase 2 Integration Test")
    print("=" * 50)
    
    # Test 1: API Health
    health_ok = await test_api_health()
    
    if not health_ok:
        print("\n❌ API server not running. Start with:")
        print("  uvicorn api.main:app --port 8001 --reload")
        return
    
    # Test 2: Billing endpoints
    billing_ok = await test_billing_endpoints()
    
    # Test 3: API docs  
    docs_ok = await test_api_docs()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 INTEGRATION TEST SUMMARY")
    print("=" * 50)
    
    tests = [
        ("API Health", health_ok),
        ("Billing Endpoints", billing_ok),
        ("API Documentation", docs_ok)
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Result: {passed}/{total} integration tests passed")
    
    if passed == total:
        print("\n🎉 Phase 2 Integration Test SUCCESSFUL!")
        print("\n🔗 Test URLs:")
        print("  • API Health: http://localhost:8001/api/v1/health")
        print("  • API Docs: http://localhost:8001/docs")
        print("  • Pricing: http://localhost:8001/api/v1/billing/pricing-tiers")
        print("\n🚀 Ready to test with frontend!")
        print("  cd frontend && npm run dev")
    else:
        print("\n⚠️  Some integration tests failed")

if __name__ == "__main__":
    asyncio.run(main()) 