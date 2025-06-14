"""
Report Generation Module - PDF export functionality

This module provides PDF report generation using WeasyPrint and Jinja2 templates
for simulation results and compliance documentation.
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import tempfile
import json

try:
    from jinja2 import Environment, FileSystemLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as e:
    WEASYPRINT_AVAILABLE = False
    print(
        f"Warning: WeasyPrint not available: {e}. PDF generation will be limited.")

from .database import get_simulation_run

logger = logging.getLogger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"


class ReportGenerator:
    """PDF report generator using WeasyPrint and Jinja2."""

    def __init__(self):
        if not WEASYPRINT_AVAILABLE:
            raise ImportError(
                "WeasyPrint and Jinja2 are required for PDF generation. "
                "Install with: pip install weasyprint jinja2"
            )

        # Setup Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=True
        )

        # Font configuration for better PDF rendering
        self.font_config = FontConfiguration()

    async def generate_simulation_report(
            self, run_id: str, user_info: Dict[str, Any]) -> bytes:
        """
        Generate a PDF report for a simulation run.

        Args:
            run_id: Unique simulation run identifier
            user_info: User information for customization

        Returns:
            PDF bytes
        """
        # Get simulation data
        simulation_data = await get_simulation_run(run_id)
        if not simulation_data:
            raise ValueError(f"Simulation run {run_id} not found")

        # Prepare template data
        template_data = self._prepare_simulation_template_data(
            simulation_data, user_info)

        # Render HTML template
        template = self.jinja_env.get_template('simulation_report.html')
        html_content = template.render(**template_data)

        # Generate PDF
        pdf_bytes = await self._html_to_pdf(html_content)

        logger.info(f"Generated PDF report for simulation {run_id}")
        return pdf_bytes

    def _prepare_simulation_template_data(self, simulation_data: Dict[str, Any],
                                          user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for the simulation report template."""

        # Extract results from simulation data
        results = simulation_data.get('results', {})
        if isinstance(results, str):
            import json
            results = json.loads(results)

        # Get scenario name from request parameters
        request_params = simulation_data.get('parameters', {})
        if isinstance(request_params, str):
            import json
            request_params = json.loads(request_params)

        scenario_name = request_params.get('scenario_name', 'Risk Analysis')

        # Format data for template
        template_data = {
            'run_id': simulation_data['id'],
            'scenario_name': scenario_name,
            'organization': user_info.get('org_name', 'Your Organization'),
            'generated_date': datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC'),
            'iterations': request_params.get('iterations', 10000),
            'confidence_level': 'High' if request_params.get('iterations', 10000) >= 10000 else 'Medium',

            # Core metrics
            'ale_formatted': self._format_currency(results.get('ale', 0)),
            'risk_level': results.get('risk_assessment', {}).get('level', 'Unknown'),
            'risk_description': results.get('risk_assessment', {}).get('description', ''),
            'recommended_action': results.get('compliance_metrics', {}).get('recommended_action', ''),

            # Detailed metrics
            'mean_triangular': results.get('mean_triangular', 0),
            'median_triangular': results.get('median_triangular', 0),
            'mean_occurrences': results.get('mean_occurrences', 0),
            'variance_occurrences': results.get('variance_occurrences', 0),
            'prob1': results.get('prob1', 0),
            'prob2': results.get('prob2', 0),
            'prob3': results.get('prob3', 0),

            # Percentiles
            'asset_value_percentiles': results.get('asset_value_percentiles'),

            # Compliance metrics
            'compliance_metrics': results.get('compliance_metrics'),
        }

        return template_data

    async def _html_to_pdf(self, html_content: str) -> bytes:
        """Convert HTML content to PDF bytes."""

        # Run WeasyPrint in a thread to avoid blocking
        def _generate_pdf():
            html_doc = HTML(string=html_content)
            return html_doc.write_pdf(font_config=self.font_config)

        # Execute in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        pdf_bytes = await loop.run_in_executor(None, _generate_pdf)

        return pdf_bytes

    async def generate_optimization_report(self, optimization_data: Dict[str, Any],
                                           user_info: Dict[str, Any]) -> bytes:
        """
        Generate a PDF report for control optimization results.

        Args:
            optimization_data: Optimization results
            user_info: User information

        Returns:
            PDF bytes
        """
        # This would use a different template for optimization reports
        # For now, we'll implement a basic version

        template_data = {
            'optimization_id': optimization_data.get('optimization_id'),
            'organization': user_info.get(
                'org_name',
                'Your Organization'),
            'generated_date': datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC'),
            'total_cost': self._format_currency(
                optimization_data.get(
                    'results',
                    {}).get(
                    'total_additional_cost',
                    0)),
            'recommendations': optimization_data.get(
                'results',
                {}).get(
                'recommendations',
                [])}

        # For now, use a simple HTML template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Control Optimization Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 2cm; }}
                h1 {{ color: #1e40af; }}
                .metric {{ background: #f8fafc; padding: 15px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>Control Optimization Report</h1>
            <p>Generated: {template_data['generated_date']}</p>
            <p>Organization: {template_data['organization']}</p>
            
            <div class="metric">
                <h2>Total Additional Investment</h2>
                <p style="font-size: 24px; color: #dc2626;">{template_data['total_cost']}</p>
            </div>
            
            <h2>Recommendations</h2>
            {''.join([f"<p>• {rec.get('control_type', 'Unknown')}: Add {rec.get('recommended_additional', 0)} units</p>"
                     for rec in template_data['recommendations']])}
        </body>
        </html>
        """

        pdf_bytes = await self._html_to_pdf(html_content)

        logger.info(
            f"Generated optimization report for {
                optimization_data.get('optimization_id')}")
        return pdf_bytes

    def _format_currency(self, amount: float) -> str:
        """Format currency for display."""
        return f"£{amount:,.2f}"

    async def generate_csrd_report(self,
                                   simulation_data: Dict[str,
                                                         Any],
                                   user_info: Dict[str,
                                                   Any],
                                   materiality_data: Dict[str,
                                                          Any] = None) -> bytes:
        """
        Generate a CSRD compliance report for Corporate Sustainability Reporting Directive.

        Args:
            simulation_data: Simulation results data
            user_info: User and organization information
            materiality_data: Additional materiality assessment data

        Returns:
            PDF bytes
        """
        # Extract results from simulation data
        results = simulation_data.get('results', {})
        if isinstance(results, str):
            import json
            results = json.loads(results)

        # Get scenario parameters
        request_params = simulation_data.get('parameters', {})
        if isinstance(request_params, str):
            import json
            request_params = json.loads(request_params)

        # Calculate materiality percentage (assuming annual revenue provided)
        annual_revenue = materiality_data.get(
            'annual_revenue') if materiality_data else None
        ale = results.get('ale', 0)
        materiality_percentage = None
        if annual_revenue and annual_revenue > 0:
            materiality_percentage = (ale / annual_revenue) * 100

        # Prepare template data
        template_data = {
            'run_id': simulation_data['id'],
            'scenario_name': request_params.get('scenario_name', 'Cyber Risk Assessment'),
            'organization': user_info.get('org_name', 'Your Organization'),
            'generated_date': datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC'),
            'assessment_period': materiality_data.get('assessment_period', '12 months') if materiality_data else '12 months',

            # Core metrics
            'ale_formatted': self._format_currency(ale),
            'risk_level': results.get('risk_assessment', {}).get('level', 'Medium'),
            'confidence_level': 'High' if request_params.get('iterations', 10000) >= 10000 else 'Medium',
            'iterations': request_params.get('iterations', 10000),

            # Materiality assessment
            'materiality_percentage': round(materiality_percentage, 2) if materiality_percentage else None,
            'annual_revenue': self._format_currency(annual_revenue) if annual_revenue else None,

            # Risk metrics
            'median_loss': results.get('median_triangular', 0),
            'var_95': results.get('asset_value_percentiles', {}).get('95', 0) if results.get('asset_value_percentiles') else 0,
            'max_loss': results.get('asset_value_percentiles', {}).get('99.9', 0) if results.get('asset_value_percentiles') else 0,

            # Control investments (example data - would come from optimization
            # results)
            'technical_investment': materiality_data.get('technical_investment', '250,000') if materiality_data else '250,000',
            'procedural_investment': materiality_data.get('procedural_investment', '150,000') if materiality_data else '150,000',
            'training_investment': materiality_data.get('training_investment', '75,000') if materiality_data else '75,000',
            'total_control_investment': materiality_data.get('total_control_investment', '£475,000') if materiality_data else '£475,000',

            # Risk management
            'risk_reduction_percentage': materiality_data.get('risk_reduction_percentage', '75') if materiality_data else '75',
            'risk_tolerance': materiality_data.get('risk_tolerance', '1.0') if materiality_data else '1.0',

            # Scenario details
            'threat_vector': request_params.get('threat_vector', 'Multi-vector cyber attack'),
            'affected_assets': request_params.get('affected_assets', 'Critical business systems and data'),
        }

        # Render HTML template
        template = self.jinja_env.get_template('csrd_report.html')
        html_content = template.render(**template_data)

        # Generate PDF
        pdf_bytes = await self._html_to_pdf(html_content)

        logger.info(
            f"Generated CSRD compliance report for simulation {
                simulation_data['id']}")
        return pdf_bytes

    async def generate_nis2_report(self,
                                   simulation_data: Dict[str,
                                                         Any],
                                   user_info: Dict[str,
                                                   Any],
                                   compliance_data: Dict[str,
                                                         Any] = None) -> bytes:
        """
        Generate a NIS2 compliance report for Network and Information Systems Security Directive.

        Args:
            simulation_data: Simulation results data
            user_info: User and organization information
            compliance_data: Additional compliance assessment data

        Returns:
            PDF bytes
        """
        # Extract results from simulation data
        results = simulation_data.get('results', {})
        if isinstance(results, str):
            import json
            results = json.loads(results)

        # Get scenario parameters
        request_params = simulation_data.get('parameters', {})
        if isinstance(request_params, str):
            import json
            request_params = json.loads(request_params)

        ale = results.get('ale', 0)

        # Prepare template data
        template_data = {
            'run_id': simulation_data['id'],
            'scenario_name': request_params.get('scenario_name', 'Cyber Risk Assessment'),
            'organization': user_info.get('org_name', 'Your Organization'),
            'generated_date': datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC'),
            'assessment_period': compliance_data.get('assessment_period', '12 months') if compliance_data else '12 months',

            # Entity classification
            'entity_type': compliance_data.get('entity_type', 'Essential Entity') if compliance_data else 'Essential Entity',
            'sector': compliance_data.get('sector', 'Digital Infrastructure') if compliance_data else 'Digital Infrastructure',

            # Core metrics
            'ale_formatted': self._format_currency(ale),
            'risk_level': results.get('risk_assessment', {}).get('level', 'Medium'),
            'confidence_level': 'High' if request_params.get('iterations', 10000) >= 10000 else 'Medium',
            'iterations': request_params.get('iterations', 10000),
            'compliance_score': compliance_data.get('compliance_score', 'High') if compliance_data else 'High',

            # Risk metrics
            'var_95': results.get('asset_value_percentiles', {}).get('95', 0) if results.get('asset_value_percentiles') else 0,
            'max_loss': results.get('asset_value_percentiles', {}).get('99.9', 0) if results.get('asset_value_percentiles') else 0,
            'risk_reduction_percentage': compliance_data.get('risk_reduction_percentage', '78') if compliance_data else '78',

            # Operational metrics
            'detection_time': compliance_data.get('detection_time', '< 4 hours') if compliance_data else '< 4 hours',
            'assessment_time': compliance_data.get('assessment_time', '< 2 hours') if compliance_data else '< 2 hours',
            'containment_time': compliance_data.get('containment_time', '< 6 hours') if compliance_data else '< 6 hours',
            'recovery_cost': self._format_currency(compliance_data.get('recovery_cost', 50000)) if compliance_data else '£50,000',
            'impact_duration': compliance_data.get('impact_duration', '24-48 hours') if compliance_data else '24-48 hours',

            # Supply chain
            'supplier_count': compliance_data.get('supplier_count', '25') if compliance_data else '25',
            'supplier_compliance': compliance_data.get('supplier_compliance', '88%') if compliance_data else '88%',

            # Investment data
            'access_control_investment': compliance_data.get('access_control_investment', '85,000') if compliance_data else '85,000',
            'network_investment': compliance_data.get('network_investment', '150,000') if compliance_data else '150,000',
            'endpoint_investment': compliance_data.get('endpoint_investment', '95,000') if compliance_data else '95,000',
            'data_investment': compliance_data.get('data_investment', '120,000') if compliance_data else '120,000',
            'vuln_investment': compliance_data.get('vuln_investment', '65,000') if compliance_data else '65,000',
            'monitoring_investment': compliance_data.get('monitoring_investment', '180,000') if compliance_data else '180,000',
            'training_investment': compliance_data.get('training_investment', '45,000') if compliance_data else '45,000',
            'incident_investment': compliance_data.get('incident_investment', '75,000') if compliance_data else '75,000',

            # Scenario details
            'threat_vector': request_params.get('threat_vector', 'Multi-stage cyber attack'),
            'affected_assets': request_params.get('affected_assets', 'Critical business systems and customer data'),
        }

        # Render HTML template
        template = self.jinja_env.get_template('nis2_report.html')
        html_content = template.render(**template_data)

        # Generate PDF
        pdf_bytes = await self._html_to_pdf(html_content)

        logger.info(
            f"Generated NIS2 compliance report for simulation {
                simulation_data['id']}")
        return pdf_bytes

    async def generate_compliance_report(self,
                                         report_type: str,
                                         simulation_data: Dict[str,
                                                               Any],
                                         user_info: Dict[str,
                                                         Any],
                                         additional_data: Dict[str,
                                                               Any] = None) -> bytes:
        """
        Generate a compliance report of the specified type.

        Args:
            report_type: Type of compliance report ('CSRD', 'NIS2', 'CUSTOM')
            simulation_data: Simulation results data
            user_info: User and organization information
            additional_data: Additional compliance-specific data

        Returns:
            PDF bytes
        """
        if report_type.upper() == 'CSRD':
            return await self.generate_csrd_report(simulation_data, user_info, additional_data)
        elif report_type.upper() == 'NIS2':
            return await self.generate_nis2_report(simulation_data, user_info, additional_data)
        else:
            # Fall back to standard simulation report
            return await self.generate_simulation_report(simulation_data['id'], user_info)


# Global report generator instance
report_generator = None


def get_report_generator() -> ReportGenerator:
    """Get or create the global report generator instance."""
    global report_generator

    if report_generator is None:
        try:
            report_generator = ReportGenerator()
        except ImportError as e:
            logger.error(f"Failed to initialize report generator: {e}")
            raise

    return report_generator


async def generate_simulation_pdf(
        run_id: str, user_info: Dict[str, Any]) -> bytes:
    """
    Generate a PDF report for a simulation run.

    Args:
        run_id: Simulation run ID
        user_info: User information

    Returns:
        PDF bytes
    """
    generator = get_report_generator()
    return await generator.generate_simulation_report(run_id, user_info)


async def generate_optimization_pdf(optimization_data: Dict[str, Any],
                                    user_info: Dict[str, Any]) -> bytes:
    """
    Generate a PDF report for optimization results.

    Args:
        optimization_data: Optimization results
        user_info: User information

    Returns:
        PDF bytes
    """
    generator = get_report_generator()
    return await generator.generate_optimization_report(optimization_data, user_info)


async def generate_compliance_pdf(report_type: str,
                                  simulation_data: Dict[str,
                                                        Any],
                                  user_info: Dict[str,
                                                  Any],
                                  additional_data: Dict[str,
                                                        Any] = None) -> bytes:
    """
    Generate a compliance PDF report.

    Args:
        report_type: Type of compliance report ('CSRD', 'NIS2', 'CUSTOM')
        simulation_data: Simulation results data
        user_info: User information
        additional_data: Additional compliance-specific data

    Returns:
        PDF bytes
    """
    generator = get_report_generator()
    return await generator.generate_compliance_report(report_type, simulation_data, user_info, additional_data)


async def store_compliance_report(org_id: str,
                                  report_type: str,
                                  simulation_run_id: str,
                                  report_data: Dict[str,
                                                    Any]) -> str:
    """
    Store compliance report metadata in the database.

    Args:
        org_id: Organization ID
        report_type: Type of compliance report
        simulation_run_id: Associated simulation run ID
        report_data: Report metadata and content

    Returns:
        Report ID
    """
    from .database import get_db_connection
    import uuid

    report_id = str(uuid.uuid4())

    query = """
    INSERT INTO compliance_reports (id, org_id, report_type, simulation_run_id, report_data, generated_at)
    VALUES (%s, %s, %s, %s, %s, %s)
    """

    async with get_db_connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query, (
                report_id, org_id, report_type, simulation_run_id,
                json.dumps(report_data), datetime.utcnow()
            ))
            await conn.commit()

    return report_id
