#!/usr/bin/env python3
"""
Test both API and Frontend services
"""

import urllib.request
import json
import socket

def test_port(host, port, service_name):
    """Test if a port is listening"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"✅ {service_name} port {port} is listening")
            return True
        else:
            print(f"❌ {service_name} port {port} is not responding")
            return False
    except Exception as e:
        print(f"❌ {service_name} port {port} error: {e}")
        return False

def test_api_health():
    """Test API health endpoint"""
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as response:
            data = json.loads(response.read().decode())
            print(f"✅ API Health: {data.get('status', 'Unknown')}")
            return True
    except Exception as e:
        print(f"❌ API Health check failed: {e}")
        return False

def test_frontend():
    """Test if frontend is serving content"""
    try:
        with urllib.request.urlopen("http://localhost:3000", timeout=5) as response:
            content = response.read().decode()
            if "CyberRisk" in content or "Next.js" in content or len(content) > 100:
                print("✅ Frontend is serving content")
                return True
            else:
                print("❌ Frontend returned unexpected content")
                return False
    except Exception as e:
        print(f"❌ Frontend check failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing CyberRisk Phase 2 Services\n")
    
    # Test ports
    api_port = test_port("localhost", 8000, "API")
    frontend_port = test_port("localhost", 3000, "Frontend")
    
    print()
    
    # Test API health
    if api_port:
        test_api_health()
    
    # Test frontend
    if frontend_port:
        test_frontend()
    
    print("\n📋 Service Status:")
    print(f"  API (Port 8000): {'✅ Running' if api_port else '❌ Not Running'}")
    print(f"  Frontend (Port 3000): {'✅ Running' if frontend_port else '❌ Not Running'}")
    
    print("\n🌐 Access URLs:")
    print("  API: http://localhost:8000")
    print("  Frontend: http://localhost:3000")
    print("  API Docs: http://localhost:8000/docs") 