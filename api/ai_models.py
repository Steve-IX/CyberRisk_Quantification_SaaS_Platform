"""
AI-Powered Risk Assessment Module
Enterprise-grade machine learning models for predictive cyber risk analysis
Phase 4 Implementation
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskPrediction:
    """Risk prediction result with confidence intervals"""
    predicted_risk: float
    confidence_interval: Tuple[float, float]
    risk_factors: Dict[str, float]
    trend_analysis: Dict[str, float]
    recommendations: List[str]
    model_confidence: float


@dataclass
class ThreatIntelligence:
    """Threat intelligence data structure"""
    threat_type: str
    severity: float
    likelihood: float
    impact_factor: float
    industry_relevance: float
    geographic_relevance: float
    temporal_relevance: float


class AIRiskAssessment:
    """AI-powered risk assessment engine with machine learning capabilities"""

    def __init__(self):
        self.risk_model = None
        self.likelihood_model = None
        self.impact_model = None
        self.scaler = StandardScaler()
        self.feature_names = [
            'organization_size',
            'industry_risk_score',
            'security_maturity',
            'previous_incidents',
            'technology_stack_risk',
            'geographic_risk',
            'regulatory_complexity',
            'supply_chain_risk',
            'data_sensitivity',
            'internet_exposure',
            'employee_risk_factor',
            'budget_security_ratio']
        self.threat_intelligence_db = []

    def initialize_models(self):
        """Initialize and train AI models for risk assessment"""
        logger.info("Initializing AI risk assessment models...")

        # Generate synthetic training data for demonstration
        # In production, this would use real historical data
        training_data = self._generate_training_data()

        # Train risk prediction model
        self.risk_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )

        # Train likelihood model
        self.likelihood_model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            random_state=42
        )

        # Train impact model
        self.impact_model = RandomForestRegressor(
            n_estimators=80,
            max_depth=8,
            random_state=42
        )

        # Prepare training data
        X = training_data[self.feature_names]
        y_risk = training_data['total_risk_score']
        y_likelihood = training_data['incident_likelihood']
        y_impact = training_data['financial_impact']

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train models
        self.risk_model.fit(X_scaled, y_risk)
        self.likelihood_model.fit(X_scaled, y_likelihood)
        self.impact_model.fit(X_scaled, y_impact)

        # Calculate model performance
        risk_score = self.risk_model.score(X_scaled, y_risk)
        likelihood_score = self.likelihood_model.score(X_scaled, y_likelihood)
        impact_score = self.impact_model.score(X_scaled, y_impact)

        logger.info(
            f"Model training complete - Risk R²: {
                risk_score:.3f}, " f"Likelihood R²: {
                likelihood_score:.3f}, Impact R²: {
                impact_score:.3f}")

        return {
            'risk_score': risk_score,
            'likelihood_score': likelihood_score,
            'impact_score': impact_score
        }

    def _generate_training_data(self, n_samples: int = 10000) -> pd.DataFrame:
        """Generate synthetic training data for model training"""
        np.random.seed(42)

        data = []
        for _ in range(n_samples):
            # Generate synthetic organization features
            org_size = np.random.uniform(10, 100000)  # Number of employees
            industry_risk = np.random.uniform(1, 10)  # Industry risk score
            security_maturity = np.random.uniform(
                1, 5)  # Security maturity level
            previous_incidents = np.random.poisson(2)  # Historical incidents
            tech_risk = np.random.uniform(1, 8)  # Technology stack risk
            geo_risk = np.random.uniform(1, 7)  # Geographic risk
            regulatory_complexity = np.random.uniform(
                1, 9)  # Regulatory complexity
            supply_chain_risk = np.random.uniform(1, 6)  # Supply chain risk
            data_sensitivity = np.random.uniform(1, 10)  # Data sensitivity
            internet_exposure = np.random.uniform(1, 8)  # Internet exposure
            employee_risk = np.random.uniform(1, 7)  # Employee risk factor
            budget_ratio = np.random.uniform(
                0.01, 0.2)  # Security budget ratio

            # Calculate synthetic targets based on features
            total_risk = (
                industry_risk * 0.2 +
                (10 - security_maturity) * 0.25 +
                previous_incidents * 0.15 +
                tech_risk * 0.15 +
                geo_risk * 0.1 +
                regulatory_complexity * 0.05 +
                supply_chain_risk * 0.05 +
                data_sensitivity * 0.05 +
                np.random.normal(0, 1)  # Noise
            )

            incident_likelihood = min(max(
                total_risk * 0.1 + np.random.normal(0, 0.2), 0), 1)

            financial_impact = (
                org_size * 100 * (total_risk / 10) *
                (data_sensitivity / 10) * np.random.lognormal(0, 0.5)
            )

            data.append({
                'organization_size': org_size,
                'industry_risk_score': industry_risk,
                'security_maturity': security_maturity,
                'previous_incidents': previous_incidents,
                'technology_stack_risk': tech_risk,
                'geographic_risk': geo_risk,
                'regulatory_complexity': regulatory_complexity,
                'supply_chain_risk': supply_chain_risk,
                'data_sensitivity': data_sensitivity,
                'internet_exposure': internet_exposure,
                'employee_risk_factor': employee_risk,
                'budget_security_ratio': budget_ratio,
                'total_risk_score': total_risk,
                'incident_likelihood': incident_likelihood,
                'financial_impact': financial_impact
            })

        return pd.DataFrame(data)

    def predict_risk(self, organization_features: Dict) -> RiskPrediction:
        """Generate AI-powered risk prediction for an organization"""
        if not self.risk_model:
            self.initialize_models()

        # Prepare feature vector
        features = np.array([[
            organization_features.get(feature, 5.0)
            for feature in self.feature_names
        ]])

        # Scale features
        features_scaled = self.scaler.transform(features)

        # Make predictions
        risk_score = self.risk_model.predict(features_scaled)[0]
        likelihood = self.likelihood_model.predict(features_scaled)[0]
        impact = self.impact_model.predict(features_scaled)[0]

        # Calculate confidence intervals using ensemble predictions
        risk_predictions = []
        for estimator in self.risk_model.estimators_:
            risk_predictions.append(estimator.predict(features_scaled)[0])

        confidence_interval = (
            np.percentile(risk_predictions, 5),
            np.percentile(risk_predictions, 95)
        )

        # Feature importance analysis
        feature_importance = dict(zip(
            self.feature_names,
            self.risk_model.feature_importances_
        ))

        # Generate trend analysis
        trend_analysis = self._analyze_risk_trends(organization_features)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            organization_features, risk_score, likelihood, impact
        )

        # Calculate model confidence
        model_confidence = min(max(
            1 - (confidence_interval[1] - confidence_interval[0]) / risk_score,
            0.6
        ), 0.98)

        return RiskPrediction(
            predicted_risk=risk_score,
            confidence_interval=confidence_interval,
            risk_factors=feature_importance,
            trend_analysis=trend_analysis,
            recommendations=recommendations,
            model_confidence=model_confidence
        )

    def _analyze_risk_trends(self, features: Dict) -> Dict[str, float]:
        """Analyze risk trends based on organization features"""
        trends = {}

        # Industry trend analysis
        industry_risk = features.get('industry_risk_score', 5.0)
        trends['industry_trend'] = 0.1 if industry_risk > 7 else -0.05

        # Security maturity trend
        security_maturity = features.get('security_maturity', 3.0)
        trends['security_improvement'] = (
            0.15 if security_maturity < 3 else -0.1)

        # Technology risk trend
        tech_risk = features.get('technology_stack_risk', 5.0)
        trends['technology_modernization'] = 0.2 if tech_risk > 6 else -0.05

        # Overall trend
        trends['overall_trend'] = sum(trends.values()) / len(trends)

        return trends

    def _generate_recommendations(
            self,
            features: Dict,
            risk_score: float,
            likelihood: float,
            impact: float) -> List[str]:
        """Generate AI-powered security recommendations"""
        recommendations = []

        # High-risk recommendations
        if risk_score > 7:
            recommendations.append(
                "Immediate risk assessment and mitigation required")
            recommendations.append(
                "Consider engaging external security consultants")

        # Security maturity recommendations
        security_maturity = features.get('security_maturity', 3.0)
        if security_maturity < 3:
            recommendations.append(
                "Implement security awareness training program")
            recommendations.append("Establish incident response procedures")
            recommendations.append(
                "Deploy endpoint detection and response (EDR) solutions")

        # Technology stack recommendations
        tech_risk = features.get('technology_stack_risk', 5.0)
        if tech_risk > 6:
            recommendations.append("Conduct technology risk assessment")
            recommendations.append("Implement zero-trust architecture")
            recommendations.append(
                "Upgrade legacy systems with security vulnerabilities")

        # Budget recommendations
        budget_ratio = features.get('budget_security_ratio', 0.05)
        if budget_ratio < 0.05:
            recommendations.append("Increase cybersecurity budget allocation")
            recommendations.append(
                "Justify security investments with risk quantification")

        # Industry-specific recommendations
        industry_risk = features.get('industry_risk_score', 5.0)
        if industry_risk > 7:
            recommendations.append(
                "Implement industry-specific security controls")
            recommendations.append(
                "Join industry threat intelligence sharing groups")

        return recommendations[:5]  # Return top 5 recommendations

    def update_threat_intelligence(
            self, threat_data: List[ThreatIntelligence]):
        """Update threat intelligence database with new threat data"""
        self.threat_intelligence_db.extend(threat_data)
        logger.info(
            f"Updated threat intelligence with {
                len(threat_data)} new threats")

    def get_threat_landscape(self, organization_profile: Dict) -> Dict:
        """Get current threat landscape relevant to organization"""
        relevant_threats = []

        for threat in self.threat_intelligence_db:
            relevance_score = (
                threat.industry_relevance * 0.4 +
                threat.geographic_relevance * 0.3 +
                threat.temporal_relevance * 0.3
            )

            if relevance_score > 0.6:
                relevant_threats.append({
                    'threat_type': threat.threat_type,
                    'severity': threat.severity,
                    'likelihood': threat.likelihood,
                    'relevance_score': relevance_score
                })

        # Sort by relevance and severity
        relevant_threats.sort(
            key=lambda x: x['relevance_score'] * x['severity'],
            reverse=True
        )

        return {
            'top_threats': relevant_threats[:10],
            'threat_count': len(relevant_threats),
            'average_severity': (
                np.mean([t['severity'] for t in relevant_threats])
                if relevant_threats else 0
            ),
            'updated_at': datetime.utcnow().isoformat()
        }

    def save_models(self, model_path: str):
        """Save trained models to disk"""
        models = {
            'risk_model': self.risk_model,
            'likelihood_model': self.likelihood_model,
            'impact_model': self.impact_model,
            'scaler': self.scaler,
            'feature_names': self.feature_names
        }

        joblib.dump(models, model_path)
        logger.info(f"Models saved to {model_path}")

    def load_models(self, model_path: str):
        """Load trained models from disk"""
        models = joblib.load(model_path)

        self.risk_model = models['risk_model']
        self.likelihood_model = models['likelihood_model']
        self.impact_model = models['impact_model']
        self.scaler = models['scaler']
        self.feature_names = models['feature_names']

        logger.info(f"Models loaded from {model_path}")


# Global AI risk assessment instance
ai_risk_assessor = AIRiskAssessment()


def get_ai_risk_assessment() -> AIRiskAssessment:
    """Get the global AI risk assessment instance"""
    return ai_risk_assessor


async def initialize_ai_models():
    """Initialize AI models on startup"""
    try:
        await ai_risk_assessor.initialize_models()
        logger.info("AI risk assessment models initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize AI models: {e}")
        raise
