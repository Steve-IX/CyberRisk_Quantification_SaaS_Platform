"""
Automated Threat Intelligence Module
Real-time threat feeds, vulnerability scanning, and threat analysis
Phase 4 Implementation
"""

import asyncio
import json
import hashlib
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import re
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from .database import get_db_connection

logger = logging.getLogger(__name__)


class ThreatSeverity(Enum):
    """Threat severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ThreatCategory(Enum):
    """Threat categories"""
    MALWARE = "malware"
    RANSOMWARE = "ransomware"
    PHISHING = "phishing"
    VULNERABILITY = "vulnerability"
    DATA_BREACH = "data_breach"
    SUPPLY_CHAIN = "supply_chain"
    INSIDER_THREAT = "insider_threat"
    APT = "apt"
    DDOS = "ddos"
    FRAUD = "fraud"


@dataclass
class ThreatIntelligenceItem:
    """Threat intelligence data structure"""
    threat_id: str
    title: str
    description: str
    category: ThreatCategory
    severity: ThreatSeverity
    confidence: float  # 0.0 to 1.0
    source: str
    indicators: List[Dict[str, str]]  # IOCs, domains, IPs, etc.
    affected_industries: List[str]
    affected_regions: List[str]
    mitigation_advice: List[str]
    references: List[str]
    first_seen: datetime
    last_updated: datetime
    expires_at: Optional[datetime]
    is_active: bool


@dataclass
class VulnerabilityReport:
    """Vulnerability assessment report"""
    scan_id: str
    organization_id: int
    scan_type: str
    target_assets: List[str]
    vulnerabilities_found: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    scan_started: datetime
    scan_completed: datetime
    findings: List[Dict[str, Any]]
    recommendations: List[str]


@dataclass
class ThreatAssessment:
    """Organization-specific threat assessment"""
    organization_id: int
    assessment_date: datetime
    overall_threat_level: str
    active_threats: int
    critical_threats: int
    industry_specific_threats: List[ThreatIntelligenceItem]
    geographic_threats: List[ThreatIntelligenceItem]
    technology_threats: List[ThreatIntelligenceItem]
    risk_score_impact: float
    recommended_actions: List[str]


class ThreatIntelligenceEngine:
    """Automated threat intelligence engine"""

    def __init__(self):
        self.threat_feeds = {
            'cisa_known_exploited': 'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json',
            'mitre_attack': 'https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json',
            'nvd_recent': 'https://services.nvd.nist.gov/rest/json/cves/2.0',
            # Add more threat feeds as needed
        }

        self.industry_mapping = {
            'financial': ['banking', 'finance', 'fintech', 'insurance'],
            'healthcare': ['healthcare', 'medical', 'hospital', 'pharma'],
            'technology': ['tech', 'software', 'it', 'saas'],
            'manufacturing': ['manufacturing', 'industrial', 'automotive'],
            'retail': ['retail', 'ecommerce', 'consumer'],
            'energy': ['energy', 'utilities', 'oil', 'gas'],
            'government': ['government', 'public', 'defense']
        }

        self.threat_cache = {}
        self.cache_ttl = 3600  # 1 hour

    async def collect_threat_intelligence(
            self) -> List[ThreatIntelligenceItem]:
        """Collect threat intelligence from multiple sources"""

        # Simulated threat collection for Phase 4
        sample_threats = [
            ThreatIntelligenceItem(
                threat_id="threat_001",
                title="New Ransomware Variant",
                description="A new ransomware variant targeting healthcare organizations",
                category=ThreatCategory.RANSOMWARE,
                severity=ThreatSeverity.HIGH,
                confidence=0.85,
                source="Custom Intelligence",
                indicators=[
                    {'type': 'hash', 'value': 'a1b2c3d4e5f6...'},
                    {'type': 'domain', 'value': 'malicious-domain.com'},
                    {'type': 'ip', 'value': '192.168.1.100'}
                ],
                affected_industries=['healthcare'],
                affected_regions=['north_america', 'europe'],
                mitigation_advice=[
                    'Implement network segmentation',
                    'Regular backup verification',
                    'Employee phishing training'
                ],
                references=['https://example-threat-intel.com/report/123'],
                first_seen=datetime.utcnow() - timedelta(days=2),
                last_updated=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30),
                is_active=True
            ),
            ThreatIntelligenceItem(
                threat_id="threat_002",
                title="Critical Vulnerability",
                description="Zero-day vulnerability in web frameworks",
                category=ThreatCategory.VULNERABILITY,
                severity=ThreatSeverity.CRITICAL,
                confidence=0.9,
                source="Security Research",
                indicators=[
                    {'type': 'cve', 'value': 'CVE-2024-0001', 'cvss_score': '9.8'},
                    {'type': 'cve', 'value': 'CVE-2024-0002', 'cvss_score': '8.1'}
                ],
                affected_industries=['all'],
                affected_regions=['global'],
                mitigation_advice=['Apply security patch immediately', 'Implement input sanitization and parameterized queries'],
                references=[
                    'https://nvd.nist.gov/vuln/detail/CVE-2024-0001',
                    'https://nvd.nist.gov/vuln/detail/CVE-2024-0002'
                ],
                first_seen=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                expires_at=None,
                is_active=True
            )
        ]

        self.threats = sample_threats
        logger.info(
            f"Collected {
                len(sample_threats)} threat intelligence items")
        return sample_threats

    async def _collect_cisa_threats(self) -> List[ThreatIntelligenceItem]:
        """Collect threats from CISA Known Exploited Vulnerabilities"""

        threats = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.threat_feeds['cisa_known_exploited'], timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()

                        for vuln in data.get('vulnerabilities', []):
                            threat = ThreatIntelligenceItem(
                                threat_id=f"cisa_{
                                    vuln.get(
                                        'cveID', 'unknown')}",
                                title=f"CISA KEV: {
                                    vuln.get(
                                        'vulnerabilityName',
                                        'Unknown Vulnerability')}",
                                description=vuln.get(
                                    'shortDescription', 'No description available'),
                                category=ThreatCategory.VULNERABILITY,
                                severity=self._map_severity(
                                    vuln.get('vulnerabilityName', '')),
                                confidence=0.9,  # CISA has high confidence
                                source='CISA Known Exploited Vulnerabilities',
                                indicators=[{
                                    'type': 'cve',
                                    'value': vuln.get('cveID', ''),
                                    'vendor': vuln.get('vendorProject', ''),
                                    'product': vuln.get('product', '')
                                }],
                                affected_industries=['all'],
                                affected_regions=['global'],
                                mitigation_advice=[
                                    vuln.get(
                                        'requiredAction',
                                        'Apply vendor patches')],
                                references=[
                                    f"https://cve.mitre.org/cgi-bin/cvename.cgi?name={vuln.get('cveID', '')}"],
                                first_seen=datetime.fromisoformat(
                                    vuln.get('dateAdded', datetime.utcnow().isoformat())),
                                last_updated=datetime.utcnow(),
                                expires_at=None,
                                is_active=True
                            )
                            threats.append(threat)

        except Exception as e:
            logger.error(f"Error collecting CISA threats: {e}")

        return threats[:50]  # Limit to recent 50 threats

    async def _collect_nvd_threats(self) -> List[ThreatIntelligenceItem]:
        """Collect recent vulnerabilities from NVD"""

        threats = []

        try:
            # Get last 7 days of CVEs
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)

            url = f"{
                self.threat_feeds['nvd_recent']}?pubStartDate={
                start_date.strftime('%Y-%m-%d')}T00:00:00.000&pubEndDate={
                end_date.strftime('%Y-%m-%d')}T23:59:59.999"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()

                        for vuln in data.get('vulnerabilities', []):
                            cve_data = vuln.get('cve', {})
                            cve_id = cve_data.get('id', 'unknown')

                            # Extract severity from CVSS
                            severity = ThreatSeverity.MEDIUM
                            cvss_data = cve_data.get('metrics', {})
                            if 'cvssMetricV31' in cvss_data:
                                cvss_score = cvss_data['cvssMetricV31'][0].get(
                                    'cvssData', {}).get('baseScore', 5.0)
                                severity = self._cvss_to_severity(cvss_score)

                            threat = ThreatIntelligenceItem(
                                threat_id=f"nvd_{cve_id}",
                                title=f"NVD CVE: {cve_id}",
                                description=cve_data.get('descriptions', [{}])[0].get('value', 'No description available'),
                                category=ThreatCategory.VULNERABILITY,
                                severity=severity,
                                confidence=0.8,
                                source='National Vulnerability Database',
                                indicators=[{
                                    'type': 'cve',
                                    'value': cve_id,
                                    'cvss_score': str(cvss_score) if 'cvss_score' in locals() else 'unknown'
                                }],
                                affected_industries=['all'],
                                affected_regions=['global'],
                                mitigation_advice=['Apply vendor patches when available', 'Monitor for exploits'],
                                references=[f"https://nvd.nist.gov/vuln/detail/{cve_id}"],
                                first_seen=datetime.fromisoformat(cve_data.get('published', datetime.utcnow().isoformat())),
                                last_updated=datetime.utcnow(),
                                expires_at=None,
                                is_active=True
                            )
                            threats.append(threat)

        except Exception as e:
            logger.error(f"Error collecting NVD threats: {e}")

        return threats[:30]  # Limit to recent 30 threats

    async def _collect_custom_threats(self) -> List[ThreatIntelligenceItem]:
        """Collect from custom threat intelligence sources"""

        # Simulated threat intelligence for demonstration
        # In production, this would integrate with commercial threat feeds

        custom_threats = [
            ThreatIntelligenceItem(
                threat_id="custom_ransomware_2024_001",
                title="New Ransomware Variant Targeting Healthcare",
                description="A new ransomware variant has been observed targeting healthcare organizations with advanced persistence techniques.",
                category=ThreatCategory.RANSOMWARE,
                severity=ThreatSeverity.HIGH,
                confidence=0.85,
                source="Custom Threat Intelligence",
                indicators=[
                    {'type': 'hash', 'value': 'a1b2c3d4e5f6...'},
                    {'type': 'domain', 'value': 'malicious-domain.com'},
                    {'type': 'ip', 'value': '192.168.1.100'}
                ],
                affected_industries=['healthcare'],
                affected_regions=['north_america', 'europe'],
                mitigation_advice=[
                    'Implement network segmentation',
                    'Regular backup verification',
                    'Employee phishing training'
                ],
                references=['https://example-threat-intel.com/report/123'],
                first_seen=datetime.utcnow() - timedelta(days=2),
                last_updated=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30),
                is_active=True
            ),
            ThreatIntelligenceItem(
                threat_id="custom_supply_chain_2024_001",
                title="Supply Chain Attack on Software Dependencies",
                description="Malicious packages discovered in popular software repositories affecting multiple industries.",
                category=ThreatCategory.SUPPLY_CHAIN,
                severity=ThreatSeverity.CRITICAL,
                confidence=0.9,
                source="Custom Threat Intelligence",
                indicators=[
                    {'type': 'package', 'value': 'malicious-package-name'},
                    {'type': 'repository', 'value': 'npm/pypi'}
                ],
                affected_industries=['technology', 'financial'],
                affected_regions=['global'],
                mitigation_advice=[
                    'Audit software dependencies',
                    'Implement package verification',
                    'Use private repositories'
                ],
                references=['https://example-threat-intel.com/report/124'],
                first_seen=datetime.utcnow() - timedelta(days=1),
                last_updated=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=45),
                is_active=True
            )
        ]

        return custom_threats

    def _map_severity(self, description: str) -> ThreatSeverity:
        """Map threat description to severity level"""

        description_lower = description.lower()

        if any(
            word in description_lower for word in [
                'critical',
                'remote code execution',
                'zero-day']):
            return ThreatSeverity.CRITICAL
        elif any(word in description_lower for word in ['high', 'privilege escalation', 'authentication bypass']):
            return ThreatSeverity.HIGH
        elif any(word in description_lower for word in ['medium', 'information disclosure', 'denial of service']):
            return ThreatSeverity.MEDIUM
        else:
            return ThreatSeverity.LOW

    def _cvss_to_severity(self, cvss_score: float) -> ThreatSeverity:
        """Convert CVSS score to threat severity"""

        if cvss_score >= 9.0:
            return ThreatSeverity.CRITICAL
        elif cvss_score >= 7.0:
            return ThreatSeverity.HIGH
        elif cvss_score >= 4.0:
            return ThreatSeverity.MEDIUM
        else:
            return ThreatSeverity.LOW

    async def _store_threat_intelligence(
            self, threats: List[ThreatIntelligenceItem]):
        """Store threat intelligence in database"""

        try:
            async with get_db_connection() as conn:
                for threat in threats:
                    query = """
                        INSERT INTO threat_intelligence
                        (threat_id, title, description, category, severity, confidence,
                         source, indicators, affected_industries, affected_regions,
                         mitigation_advice, references, first_seen, last_updated,
                         expires_at, is_active)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                        ON CONFLICT (threat_id) DO UPDATE SET
                        title = $2, description = $3, last_updated = $14,
                        is_active = $16
                    """

                    await conn.execute(
                        query,
                        threat.threat_id, threat.title, threat.description,
                        threat.category.value, threat.severity.value, threat.confidence,
                        threat.source, json.dumps(threat.indicators),
                        json.dumps(threat.affected_industries),
                        json.dumps(threat.affected_regions),
                        json.dumps(threat.mitigation_advice),
                        json.dumps(threat.references),
                        threat.first_seen, threat.last_updated,
                        threat.expires_at, threat.is_active
                    )

        except Exception as e:
            logger.error(f"Error storing threat intelligence: {e}")

    async def get_organization_threat_assessment(
            self, organization_id: int) -> ThreatAssessment:
        """Generate threat assessment for specific organization"""

        try:
            # Get organization profile
            org_profile = await self._get_organization_profile(organization_id)

            # Get relevant threats
            industry_threats = await self._get_threats_by_industry(org_profile.get('industry', 'technology'))
            geographic_threats = await self._get_threats_by_region(org_profile.get('region', 'global'))
            technology_threats = await self._get_threats_by_technology(org_profile.get('technology_stack', []))

            # Calculate threat levels
            all_relevant_threats = industry_threats + \
                geographic_threats + technology_threats
            critical_threats = len(
                [t for t in all_relevant_threats if t.severity == ThreatSeverity.CRITICAL])

            # Determine overall threat level
            if critical_threats > 5:
                overall_level = "CRITICAL"
            elif critical_threats > 2:
                overall_level = "HIGH"
            elif len(all_relevant_threats) > 10:
                overall_level = "MEDIUM"
            else:
                overall_level = "LOW"

            # Calculate risk score impact
            risk_impact = min(
                critical_threats *
                0.5 +
                len(all_relevant_threats) *
                0.1,
                3.0)

            # Generate recommendations
            recommendations = self._generate_threat_recommendations(
                all_relevant_threats, org_profile
            )

            return ThreatAssessment(
                organization_id=organization_id,
                assessment_date=datetime.utcnow(),
                overall_threat_level=overall_level,
                active_threats=len(all_relevant_threats),
                critical_threats=critical_threats,
                industry_specific_threats=industry_threats[:10],
                geographic_threats=geographic_threats[:5],
                technology_threats=technology_threats[:5],
                risk_score_impact=risk_impact,
                recommended_actions=recommendations
            )

        except Exception as e:
            logger.error(f"Error generating threat assessment: {e}")
            return ThreatAssessment(
                organization_id=organization_id,
                assessment_date=datetime.utcnow(),
                overall_threat_level="MEDIUM",
                active_threats=0,
                critical_threats=0,
                industry_specific_threats=[],
                geographic_threats=[],
                technology_threats=[],
                risk_score_impact=0.0,
                recommended_actions=["Regular threat monitoring recommended"]
            )

    async def _get_organization_profile(
            self, organization_id: int) -> Dict[str, Any]:
        """Get organization profile for threat assessment"""

        try:
            async with get_db_connection() as conn:
                query = """
                    SELECT name, industry, size, region, technology_stack
                    FROM organizations
                    WHERE id = $1
                """

                result = await conn.fetchrow(query, organization_id)

                if result:
                    return {
                        'name': result['name'],
                        'industry': result['industry'] or 'technology',
                        'size': result['size'] or 'medium',
                        'region': result['region'] or 'global',
                        'technology_stack': json.loads(
                            result['technology_stack'] or '[]')}

        except Exception as e:
            logger.error(f"Error getting organization profile: {e}")

        return {
            'industry': 'technology',
            'region': 'global',
            'technology_stack': []}

    async def _get_threats_by_industry(
            self, industry: str) -> List[ThreatIntelligenceItem]:
        """Get threats relevant to specific industry"""

        try:
            async with get_db_connection() as conn:
                query = """
                    SELECT * FROM threat_intelligence
                    WHERE (affected_industries::text LIKE $1 OR affected_industries::text LIKE '%all%')
                    AND is_active = true
                    AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY severity DESC, last_updated DESC
                    LIMIT 20
                """

                results = await conn.fetch(query, f'%{industry}%')

                threats = []
                for row in results:
                    threat = ThreatIntelligenceItem(
                        threat_id=row['threat_id'],
                        title=row['title'],
                        description=row['description'],
                        category=ThreatCategory(row['category']),
                        severity=ThreatSeverity(row['severity']),
                        confidence=row['confidence'],
                        source=row['source'],
                        indicators=json.loads(row['indicators']),
                        affected_industries=json.loads(row['affected_industries']),
                        affected_regions=json.loads(row['affected_regions']),
                        mitigation_advice=json.loads(row['mitigation_advice']),
                        references=json.loads(row['references']),
                        first_seen=row['first_seen'],
                        last_updated=row['last_updated'],
                        expires_at=row['expires_at'],
                        is_active=row['is_active']
                    )
                    threats.append(threat)

                return threats

        except Exception as e:
            logger.error(f"Error getting industry threats: {e}")
            return []

    async def _get_threats_by_region(
            self, region: str) -> List[ThreatIntelligenceItem]:
        """Get threats relevant to specific geographic region"""

        try:
            async with get_db_connection() as conn:
                query = """
                    SELECT * FROM threat_intelligence
                    WHERE (affected_regions::text LIKE $1 OR affected_regions::text LIKE '%global%')
                    AND is_active = true
                    AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY severity DESC, last_updated DESC
                    LIMIT 10
                """

                results = await conn.fetch(query, f'%{region}%')
                return await self._convert_db_results_to_threats(results)

        except Exception as e:
            logger.error(f"Error getting regional threats: {e}")
            return []

    async def _get_threats_by_technology(
            self, tech_stack: List[str]) -> List[ThreatIntelligenceItem]:
        """Get threats relevant to specific technology stack"""

        # For demonstration, return general technology threats
        # In production, this would match against specific technologies

        try:
            async with get_db_connection() as conn:
                query = """
                    SELECT * FROM threat_intelligence
                    WHERE (category = 'vulnerability' OR category = 'supply_chain')
                    AND is_active = true
                    AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY severity DESC, last_updated DESC
                    LIMIT 10
                """

                results = await conn.fetch(query)
                return await self._convert_db_results_to_threats(results)

        except Exception as e:
            logger.error(f"Error getting technology threats: {e}")
            return []

    async def _convert_db_results_to_threats(
            self, results) -> List[ThreatIntelligenceItem]:
        """Convert database results to ThreatIntelligenceItem objects"""

        threats = []
        for row in results:
            try:
                threat = ThreatIntelligenceItem(
                    threat_id=row['threat_id'],
                    title=row['title'],
                    description=row['description'],
                    category=ThreatCategory(row['category']),
                    severity=ThreatSeverity(row['severity']),
                    confidence=row['confidence'],
                    source=row['source'],
                    indicators=json.loads(row['indicators']),
                    affected_industries=json.loads(row['affected_industries']),
                    affected_regions=json.loads(row['affected_regions']),
                    mitigation_advice=json.loads(row['mitigation_advice']),
                    references=json.loads(row['references']),
                    first_seen=row['first_seen'],
                    last_updated=row['last_updated'],
                    expires_at=row['expires_at'],
                    is_active=row['is_active']
                )
                threats.append(threat)
            except Exception as e:
                logger.error(f"Error converting threat data: {e}")
                continue

        return threats

    def _generate_threat_recommendations(self,
                                         threats: List[ThreatIntelligenceItem],
                                         org_profile: Dict[str,
                                                           Any]) -> List[str]:
        """Generate threat-specific recommendations"""

        recommendations = []

        # Analyze threat categories
        threat_categories = [t.category for t in threats]

        if ThreatCategory.RANSOMWARE in threat_categories:
            recommendations.extend([
                "Implement comprehensive backup strategy with offline copies",
                "Deploy endpoint detection and response (EDR) solutions",
                "Conduct regular ransomware response drills"
            ])

        if ThreatCategory.PHISHING in threat_categories:
            recommendations.extend([
                "Enhance email security with advanced threat protection",
                "Conduct targeted phishing awareness training",
                "Implement multi-factor authentication"
            ])

        if ThreatCategory.VULNERABILITY in threat_categories:
            recommendations.extend([
                "Establish vulnerability management program",
                "Implement automated patch management",
                "Regular security assessments and penetration testing"
            ])

        if ThreatCategory.SUPPLY_CHAIN in threat_categories:
            recommendations.extend([
                "Audit third-party vendors and suppliers",
                "Implement supply chain risk assessment",
                "Monitor software dependencies for vulnerabilities"
            ])

        # Add industry-specific recommendations
        industry = org_profile.get('industry', 'technology')
        if industry == 'healthcare':
            recommendations.append(
                "Ensure HIPAA compliance and patient data protection")
        elif industry == 'financial':
            recommendations.append(
                "Implement financial industry cybersecurity frameworks")

        return list(set(recommendations))  # Remove duplicates

    async def perform_vulnerability_scan(
            self,
            organization_id: int,
            target_assets: List[str]) -> VulnerabilityReport:
        """Perform vulnerability scan on organization assets"""

        scan_id = f"scan_{organization_id}_{
            int(
                datetime.utcnow().timestamp())}"
        scan_started = datetime.utcnow()

        # Simulated vulnerability scan results
        # In production, this would integrate with actual vulnerability
        # scanners

        findings = [{'vulnerability_id': 'CVE-2024-0001',
                     'title': 'Remote Code Execution in Web Server',
                     'severity': 'critical',
                     'cvss_score': 9.8,
                     'affected_asset': target_assets[0] if target_assets else 'server-01',
                     'description': 'Unauthenticated remote code execution vulnerability',
                     'recommendation': 'Apply security patch immediately'},
                    {'vulnerability_id': 'CVE-2024-0002',
                     'title': 'SQL Injection in Application',
                     'severity': 'high',
                     'cvss_score': 8.1,
                     'affected_asset': target_assets[1] if len(target_assets) > 1 else 'app-server',
                     'description': 'SQL injection vulnerability in user input validation',
                     'recommendation': 'Implement input sanitization and parameterized queries'}]

        # Count vulnerabilities by severity
        critical_count = len(
            [f for f in findings if f['severity'] == 'critical'])
        high_count = len([f for f in findings if f['severity'] == 'high'])
        medium_count = len([f for f in findings if f['severity'] == 'medium'])
        low_count = len([f for f in findings if f['severity'] == 'low'])

        recommendations = [
            "Prioritize patching critical and high severity vulnerabilities",
            "Implement vulnerability management program",
            "Schedule regular security assessments",
            "Monitor for new vulnerabilities in identified assets"
        ]

        scan_completed = datetime.utcnow()

        report = VulnerabilityReport(
            scan_id=scan_id,
            organization_id=organization_id,
            scan_type='comprehensive',
            target_assets=target_assets,
            vulnerabilities_found=len(findings),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            scan_started=scan_started,
            scan_completed=scan_completed,
            findings=findings,
            recommendations=recommendations
        )

        # Store scan report
        await self._store_vulnerability_report(report)

        return report

    async def _store_vulnerability_report(self, report: VulnerabilityReport):
        """Store vulnerability scan report in database"""

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
                    report.scan_id, report.organization_id, report.scan_type,
                    json.dumps(report.target_assets), report.vulnerabilities_found,
                    report.critical_count, report.high_count, report.medium_count,
                    report.low_count, report.scan_started, report.scan_completed,
                    json.dumps(report.findings), json.dumps(report.recommendations)
                )

        except Exception as e:
            logger.error(f"Error storing vulnerability report: {e}")


# Global threat intelligence engine instance
threat_intelligence_engine = ThreatIntelligenceEngine()


def get_threat_intelligence_engine() -> ThreatIntelligenceEngine:
    """Get the global threat intelligence engine instance"""
    return threat_intelligence_engine


async def initialize_threat_intelligence():
    """Initialize threat intelligence collection"""
    try:
        await threat_intelligence_engine.collect_threat_intelligence()
        logger.info("Threat intelligence initialization complete")
    except Exception as e:
        logger.error(f"Failed to initialize threat intelligence: {e}")
        raise
