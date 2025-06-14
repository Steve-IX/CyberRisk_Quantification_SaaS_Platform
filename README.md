# CyberRisk Quantification SaaS Platform

**A complete cyber risk quantification platform for NIS2 & CSRD compliance**

Transform your cyber risk data into actionable business intelligence with Monte Carlo simulation, control optimization, and automated compliance reporting.

---

## 🚀 What's New: SaaS Platform

This project has been transformed from a simple Monte Carlo toolkit into a **production-ready SaaS platform** for cyber risk quantification. Perfect for UK-EU companies facing NIS2 and CSRD reporting requirements.

### ✨ Key Features

| Feature | Description | Business Value |
|---------|-------------|----------------|
| **Monte Carlo Risk Simulation** | FAIR-style quantitative risk analysis with 10k+ iterations | Convert "High/Medium/Low" to £ figures your board understands |
| **Control Optimization** | Linear programming to find cheapest path to risk targets | Defend security budgets with mathematical precision |
| **NIS2/CSRD Compliance** | Auto-generate regulatory annexes from simulation outputs | Save dozens of analyst hours per quarter |
| **RESTful API** | FastAPI with OpenAPI docs and JWT authentication | Integrate with existing security tools and workflows |
| **Async Processing** | Background simulation tasks with real-time progress | Handle enterprise-scale risk models without timeouts |

---

## 🏗️ Architecture

```
┌─ Next.js Frontend (Coming Soon)
│  ├─ Risk Dashboard
│  ├─ Simulation Builder  
│  └─ Compliance Reports
│
├─ FastAPI Backend
│  ├─ /api/v1/simulate (POST)
│  ├─ /api/v1/optimize (POST)
│  └─ /api/v1/results/{id} (GET)
│
├─ CyberRisk Core Library
│  ├─ Monte Carlo Engine
│  ├─ Probability Models
│  └─ Control Optimizer
│
└─ PostgreSQL Database
   ├─ Simulation Results
   ├─ User Organizations
   └─ Asset Inventory
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Clone the repository
git clone https://github.com/Steve-IX/Monte-Carlo-Probability-and-Optimization-in-Python.git
cd Monte-Carlo-Probability-and-Optimization-in-Python

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Demo

```bash
# Test the core library with examples
python demo.py
```

This will run comprehensive demos showing:
- ALE calculation for an e-commerce data breach scenario
- Conditional probability analysis for security screening
- Control optimization for firewall/IDS/endpoint deployment
- Integrated risk management workflow with ROI analysis

### 3. Start the API Server

```bash
# Start FastAPI development server
uvicorn api.main:app --reload

# API will be available at:
# - Swagger UI: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
# - Health check: http://localhost:8000/health
```

### 4. Get Authentication Token

```bash
# Generate a demo JWT token
python api/auth.py
```

Use this token in the `Authorization: Bearer <token>` header for API requests.

---

## 📊 API Usage Examples

### Start a Risk Simulation

```bash
curl -X POST "http://localhost:8000/api/v1/simulate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_value_min": 50000,
    "asset_value_mode": 150000,
    "asset_value_max": 500000,
    "occurrence_counts": [0, 1, 2, 3, 4, 5],
    "occurrence_probabilities": [0.3, 0.4, 0.2, 0.06, 0.03, 0.01],
    "iterations": 10000,
    "flaw_a_mu": 9.2,
    "flaw_a_sigma": 1.0,
    "flaw_b_scale": 5000,
    "flaw_b_alpha": 2.5,
    "threshold_point1": 100000,
    "threshold_point2": 50000,
    "range_point3": 20000,
    "range_point4": 100000,
    "scenario_name": "E-commerce Data Breach"
  }'
```

### Get Simulation Results

```bash
curl -X GET "http://localhost:8000/api/v1/results/{run_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Optimize Security Controls

```bash
curl -X POST "http://localhost:8000/api/v1/optimize" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "historical_data": [
      [2, 3, 1, 4, 2, 3, 1, 2, 3],
      [1, 2, 3, 2, 1, 2, 3, 1, 2],
      [3, 2, 4, 1, 3, 2, 4, 3, 2],
      [1, 1, 2, 2, 1, 1, 2, 1, 1]
    ],
    "safeguard_effects": [85, 78, 92, 70, 88, 82, 95, 87, 80],
    "maintenance_loads": [45, 52, 38, 65, 42, 48, 35, 44, 50],
    "current_controls": [2, 1, 3, 1],
    "control_costs": [10000, 15000, 8000, 5000],
    "control_limits": [5, 4, 6, 3],
    "safeguard_target": 90.0,
    "maintenance_limit": 50.0
  }'
```

---

## 💼 Business Use Cases

### 1. **Board Risk Reporting**
- Convert technical vulnerabilities into £ figures
- Generate executive-ready risk dashboards
- Track risk reduction ROI over time

### 2. **NIS2 Compliance** (EU Directive 2022/2555)
- Automated risk management measure documentation
- Supply chain security risk quantification
- Incident impact calculations

### 3. **CSRD Reporting** (EU Directive 2022/2464)
- Cyber risk materiality assessments
- Financial impact disclosures
- Sustainability risk integration

### 4. **Security Investment Planning**
- Optimize control portfolios under budget constraints
- Quantify insurance vs. controls trade-offs
- Justify security spending with hard numbers

---

## 🎯 Pricing & Go-to-Market

| Tier | Price/Month | Users | Simulations | Target Customers |
|------|-------------|-------|-------------|------------------|
| **Starter** | £49 | 2 | 50 | Small consultancies, vCISOs |
| **Pro** | £199 | 10 | 500 | Mid-market (50-500 employees) |
| **Enterprise** | £499 | 25 | Unlimited | Large enterprises, MSPs |

**Launch Strategy:**
- Target UK/EU companies with 50-500 employees holding PII/cardholder data
- Focus on sectors facing NIS2 requirements (critical infrastructure, digital services)
- Partner with Cyber Essentials assessors and vCISO consultancies

---

## 🛠️ Development Roadmap

### Phase 1: MVP (Weeks 1-4) ✅
- [x] Core Monte Carlo library
- [x] FastAPI backend with auth
- [x] PostgreSQL integration
- [x] Comprehensive product specification

### Phase 2: SaaS MVP (Weeks 5-8)
- [ ] Next.js frontend dashboard
- [ ] File upload for asset/scenario data
- [ ] PDF report generation
- [ ] Stripe billing integration

### Phase 3: Market Ready (Weeks 9-12)
- [ ] Control optimization UI
- [ ] NIS2/CSRD report templates
- [ ] Multi-tenant organization support
- [ ] Performance optimization

### Phase 4: Scale (Months 4-6)
- [ ] Vulnerability scanner integrations
- [ ] Third-party risk analysis
- [ ] Insurance portal integrations
- [ ] AI-powered risk narratives

---

## 🏢 Enterprise Features

### Database Schema
- Multi-tenant organization support
- Asset inventory management
- Scenario library with templates
- Audit trails and compliance logging

### Security & Compliance
- JWT authentication with role-based access
- SOC 2 Type II controls mapping
- ISO 27001 Annex A implementation
- GDPR data retention policies

### Performance & Scale
- Async background processing
- Redis caching for simulation results
- Auto-scaling with AWS Lambda/Fargate
- CDN delivery for reports and dashboards

---

## 🤝 Contributing

We welcome contributions! Please see:
- `PRODUCT_SPEC.md` for detailed technical specifications
- Issues for feature requests and bug reports
- Pull requests for code contributions

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest black flake8

# Run tests
pytest

# Format code
black .

# Run linting
flake8
```

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🆘 Support

- **Documentation:** See `PRODUCT_SPEC.md` for complete technical specifications
- **API Docs:** http://localhost:8000/docs (when running locally)
- **Issues:** GitHub Issues for bug reports and feature requests
- **Commercial Support:** Contact for enterprise licensing and support

---

**Ready to transform your cyber risk management? Start with the demo and see your risks in £ rather than colors!** 🎯
