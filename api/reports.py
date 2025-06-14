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
    print(f"Warning: WeasyPrint not available: {e}. PDF generation will be limited.")

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
    
    async def generate_simulation_report(self, run_id: str, user_info: Dict[str, Any]) -> bytes:
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
        template_data = self._prepare_simulation_template_data(simulation_data, user_info)
        
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
            'organization': user_info.get('org_name', 'Your Organization'),
            'generated_date': datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC'),
            'total_cost': self._format_currency(
                optimization_data.get('results', {}).get('total_additional_cost', 0)
            ),
            'recommendations': optimization_data.get('results', {}).get('recommendations', [])
        }
        
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
        
        logger.info(f"Generated optimization report for {optimization_data.get('optimization_id')}")
        return pdf_bytes
    
    def _format_currency(self, amount: float) -> str:
        """Format currency for display."""
        return f"£{amount:,.2f}"


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


async def generate_simulation_pdf(run_id: str, user_info: Dict[str, Any]) -> bytes:
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