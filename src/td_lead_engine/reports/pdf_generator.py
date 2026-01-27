"""PDF report generation system."""

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from enum import Enum


class ReportType(Enum):
    """Types of PDF reports."""
    CMA = "cma"
    MARKET_ANALYSIS = "market_analysis"
    BUYER_ACTIVITY = "buyer_activity"
    SELLER_ACTIVITY = "seller_activity"
    TRANSACTION_SUMMARY = "transaction_summary"
    LEAD_PIPELINE = "lead_pipeline"
    AGENT_PERFORMANCE = "agent_performance"
    PROPERTY_FLYER = "property_flyer"


@dataclass
class ReportSection:
    """A section of a report."""
    title: str
    content_type: str  # text, table, chart, image, list
    data: Any
    style: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedReport:
    """A generated report."""
    id: str
    report_type: ReportType
    title: str
    filename: str
    file_path: str
    generated_at: datetime
    generated_by: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_size: int = 0


class PDFReportGenerator:
    """Generates PDF reports using HTML to PDF conversion."""

    def __init__(self, output_dir: str = "data/reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.generated_reports: List[GeneratedReport] = []

    def generate_cma_report(
        self,
        property_address: str,
        property_data: Dict,
        comparable_sales: List[Dict],
        market_data: Dict,
        agent_name: str,
        client_name: str
    ) -> GeneratedReport:
        """Generate a Comparative Market Analysis report."""
        sections = []

        # Cover page
        sections.append(ReportSection(
            title="cover",
            content_type="cover",
            data={
                'title': "Comparative Market Analysis",
                'subtitle': property_address,
                'prepared_for': client_name,
                'prepared_by': agent_name,
                'date': datetime.now().strftime("%B %d, %Y"),
                'company': "TD Realty"
            }
        ))

        # Executive summary
        estimated_value = self._calculate_estimated_value(property_data, comparable_sales)
        sections.append(ReportSection(
            title="Executive Summary",
            content_type="text",
            data={
                'estimated_value': estimated_value,
                'value_range': (estimated_value * 0.95, estimated_value * 1.05),
                'confidence': "High" if len(comparable_sales) >= 5 else "Medium",
                'market_trend': market_data.get('trend', 'Stable')
            }
        ))

        # Subject property details
        sections.append(ReportSection(
            title="Subject Property",
            content_type="property_details",
            data=property_data
        ))

        # Comparable sales
        sections.append(ReportSection(
            title="Comparable Sales",
            content_type="comparables",
            data=comparable_sales
        ))

        # Market overview
        sections.append(ReportSection(
            title="Market Overview",
            content_type="market_data",
            data=market_data
        ))

        # Generate HTML
        html_content = self._render_cma_html(sections, property_address)

        # Save and return
        return self._save_report(
            report_type=ReportType.CMA,
            title=f"CMA - {property_address}",
            html_content=html_content,
            generated_by=agent_name,
            metadata={'property': property_address, 'client': client_name}
        )

    def generate_buyer_activity_report(
        self,
        client_name: str,
        client_email: str,
        searches: List[Dict],
        saved_properties: List[Dict],
        showings: List[Dict],
        offers: List[Dict],
        agent_name: str
    ) -> GeneratedReport:
        """Generate a buyer activity report."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                {self._get_report_styles()}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Buyer Activity Report</h1>
                <h2>{client_name}</h2>
                <p>Generated: {datetime.now().strftime("%B %d, %Y")}</p>
            </div>

            <div class="section">
                <h3>Search Summary</h3>
                <p>Active searches: {len(searches)}</p>
                <p>Properties saved: {len(saved_properties)}</p>
                <p>Showings attended: {len([s for s in showings if s.get('status') == 'completed'])}</p>
                <p>Offers submitted: {len(offers)}</p>
            </div>

            <div class="section">
                <h3>Search Criteria</h3>
                <table>
                    <tr><th>Search Name</th><th>Locations</th><th>Price Range</th><th>Beds</th></tr>
                    {''.join(f"<tr><td>{s.get('name', 'Unnamed')}</td><td>{', '.join(s.get('locations', []))}</td><td>${s.get('min_price', 0):,} - ${s.get('max_price', 0):,}</td><td>{s.get('min_beds', 'Any')}+</td></tr>" for s in searches)}
                </table>
            </div>

            <div class="section">
                <h3>Saved Properties</h3>
                <table>
                    <tr><th>Address</th><th>Price</th><th>Beds/Baths</th><th>Status</th></tr>
                    {''.join(f"<tr><td>{p.get('address', '')}</td><td>${p.get('price', 0):,}</td><td>{p.get('beds', '-')}/{p.get('baths', '-')}</td><td>{p.get('status', 'Active')}</td></tr>" for p in saved_properties[:10])}
                </table>
            </div>

            <div class="section">
                <h3>Recent Showings</h3>
                <table>
                    <tr><th>Date</th><th>Property</th><th>Rating</th><th>Feedback</th></tr>
                    {''.join(f"<tr><td>{s.get('date', '')}</td><td>{s.get('property', '')}</td><td>{'★' * s.get('rating', 0)}{'☆' * (5 - s.get('rating', 0))}</td><td>{s.get('feedback', '-')[:50]}...</td></tr>" for s in showings[:10])}
                </table>
            </div>

            <div class="footer">
                <p>Prepared by: {agent_name} | TD Realty</p>
                <p>This report is confidential and intended for the named recipient only.</p>
            </div>
        </body>
        </html>
        """

        return self._save_report(
            report_type=ReportType.BUYER_ACTIVITY,
            title=f"Buyer Activity - {client_name}",
            html_content=html_content,
            generated_by=agent_name,
            metadata={'client': client_name, 'email': client_email}
        )

    def generate_seller_activity_report(
        self,
        client_name: str,
        listing_data: Dict,
        showings: List[Dict],
        offers: List[Dict],
        feedback_summary: Dict,
        market_data: Dict,
        agent_name: str
    ) -> GeneratedReport:
        """Generate a seller activity report."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                {self._get_report_styles()}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Seller Activity Report</h1>
                <h2>{listing_data.get('address', 'Property')}</h2>
                <p>Generated: {datetime.now().strftime("%B %d, %Y")}</p>
            </div>

            <div class="section">
                <h3>Listing Summary</h3>
                <div class="stats-grid">
                    <div class="stat">
                        <span class="stat-value">{listing_data.get('days_on_market', 0)}</span>
                        <span class="stat-label">Days on Market</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">{listing_data.get('total_views', 0)}</span>
                        <span class="stat-label">Total Views</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">{len(showings)}</span>
                        <span class="stat-label">Total Showings</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">{len(offers)}</span>
                        <span class="stat-label">Offers Received</span>
                    </div>
                </div>
            </div>

            <div class="section">
                <h3>Current Listing</h3>
                <table>
                    <tr><td>List Price</td><td>${listing_data.get('price', 0):,}</td></tr>
                    <tr><td>Original Price</td><td>${listing_data.get('original_price', listing_data.get('price', 0)):,}</td></tr>
                    <tr><td>Status</td><td>{listing_data.get('status', 'Active')}</td></tr>
                    <tr><td>Listed Date</td><td>{listing_data.get('list_date', '-')}</td></tr>
                </table>
            </div>

            <div class="section">
                <h3>Showing Feedback Summary</h3>
                <p>Average Rating: {'★' * int(feedback_summary.get('average_rating', 0))}{'☆' * (5 - int(feedback_summary.get('average_rating', 0)))} ({feedback_summary.get('average_rating', 0):.1f}/5)</p>
                <h4>Common Positives:</h4>
                <ul>
                    {''.join(f"<li>{p}</li>" for p in feedback_summary.get('positives', ['No feedback yet']))}
                </ul>
                <h4>Common Concerns:</h4>
                <ul>
                    {''.join(f"<li>{c}</li>" for c in feedback_summary.get('concerns', ['No concerns noted']))}
                </ul>
            </div>

            <div class="section">
                <h3>Market Comparison</h3>
                <table>
                    <tr><td>Your Price</td><td>${listing_data.get('price', 0):,}</td></tr>
                    <tr><td>Avg. Area Price</td><td>${market_data.get('avg_price', 0):,}</td></tr>
                    <tr><td>Price/Sq Ft</td><td>${listing_data.get('price_per_sqft', 0):,.0f}</td></tr>
                    <tr><td>Avg. Area $/Sq Ft</td><td>${market_data.get('avg_price_sqft', 0):,.0f}</td></tr>
                    <tr><td>Avg. Days on Market</td><td>{market_data.get('avg_dom', 0)} days</td></tr>
                </table>
            </div>

            <div class="footer">
                <p>Prepared by: {agent_name} | TD Realty</p>
            </div>
        </body>
        </html>
        """

        return self._save_report(
            report_type=ReportType.SELLER_ACTIVITY,
            title=f"Seller Activity - {listing_data.get('address', 'Property')}",
            html_content=html_content,
            generated_by=agent_name,
            metadata={'client': client_name, 'property': listing_data.get('address')}
        )

    def generate_lead_pipeline_report(
        self,
        pipeline_data: Dict,
        leads_by_stage: Dict[str, List[Dict]],
        conversion_data: Dict,
        agent_name: str
    ) -> GeneratedReport:
        """Generate a lead pipeline report."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                {self._get_report_styles()}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Lead Pipeline Report</h1>
                <p>Generated: {datetime.now().strftime("%B %d, %Y")}</p>
            </div>

            <div class="section">
                <h3>Pipeline Overview</h3>
                <div class="stats-grid">
                    <div class="stat">
                        <span class="stat-value">{pipeline_data.get('total_leads', 0)}</span>
                        <span class="stat-label">Total Leads</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">{pipeline_data.get('hot_leads', 0)}</span>
                        <span class="stat-label">Hot Leads</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">${pipeline_data.get('pipeline_value', 0):,.0f}</span>
                        <span class="stat-label">Pipeline Value</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">{conversion_data.get('conversion_rate', 0):.1f}%</span>
                        <span class="stat-label">Conversion Rate</span>
                    </div>
                </div>
            </div>

            <div class="section">
                <h3>Leads by Stage</h3>
                <table>
                    <tr><th>Stage</th><th>Count</th><th>Avg Score</th><th>Value</th></tr>
                    {''.join(f"<tr><td>{stage}</td><td>{len(leads)}</td><td>{sum(l.get('score', 0) for l in leads) / len(leads) if leads else 0:.0f}</td><td>${sum(l.get('estimated_value', 0) for l in leads):,.0f}</td></tr>" for stage, leads in leads_by_stage.items())}
                </table>
            </div>

            <div class="section">
                <h3>Top Hot Leads</h3>
                <table>
                    <tr><th>Name</th><th>Score</th><th>Source</th><th>Days in Pipeline</th></tr>
                    {''.join(f"<tr><td>{l.get('name', 'Unknown')}</td><td>{l.get('score', 0)}</td><td>{l.get('source', '-')}</td><td>{l.get('days_in_pipeline', 0)}</td></tr>" for l in sorted([lead for leads in leads_by_stage.values() for lead in leads], key=lambda x: x.get('score', 0), reverse=True)[:10])}
                </table>
            </div>

            <div class="footer">
                <p>Prepared by: {agent_name} | TD Realty</p>
            </div>
        </body>
        </html>
        """

        return self._save_report(
            report_type=ReportType.LEAD_PIPELINE,
            title="Lead Pipeline Report",
            html_content=html_content,
            generated_by=agent_name,
            metadata={'total_leads': pipeline_data.get('total_leads', 0)}
        )

    def generate_property_flyer(
        self,
        property_data: Dict,
        agent_name: str,
        agent_phone: str,
        agent_email: str,
        photos: List[str] = None
    ) -> GeneratedReport:
        """Generate a property marketing flyer."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Georgia', serif; margin: 0; padding: 0; }}
                .flyer {{ max-width: 8.5in; margin: 0 auto; }}
                .hero {{ background: #1e40af; color: white; padding: 40px; text-align: center; }}
                .hero h1 {{ font-size: 42px; margin: 0 0 10px 0; }}
                .hero .price {{ font-size: 48px; font-weight: bold; }}
                .photos {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 20px; }}
                .photos img {{ width: 100%; height: 200px; object-fit: cover; }}
                .details {{ padding: 30px; background: #f8fafc; }}
                .details-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; text-align: center; }}
                .detail {{ padding: 15px; background: white; border-radius: 8px; }}
                .detail .value {{ font-size: 24px; font-weight: bold; color: #1e40af; }}
                .detail .label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                .description {{ padding: 30px; line-height: 1.8; }}
                .agent {{ background: #1e40af; color: white; padding: 30px; display: flex; align-items: center; justify-content: space-between; }}
                .agent-info h3 {{ margin: 0 0 5px 0; }}
                .agent-contact {{ text-align: right; }}
            </style>
        </head>
        <body>
            <div class="flyer">
                <div class="hero">
                    <h1>{property_data.get('address', 'Beautiful Home')}</h1>
                    <p>{property_data.get('city', '')}, {property_data.get('state', 'OH')} {property_data.get('zip', '')}</p>
                    <div class="price">${property_data.get('price', 0):,}</div>
                </div>

                <div class="details">
                    <div class="details-grid">
                        <div class="detail">
                            <div class="value">{property_data.get('beds', 0)}</div>
                            <div class="label">Bedrooms</div>
                        </div>
                        <div class="detail">
                            <div class="value">{property_data.get('baths', 0)}</div>
                            <div class="label">Bathrooms</div>
                        </div>
                        <div class="detail">
                            <div class="value">{property_data.get('sqft', 0):,}</div>
                            <div class="label">Sq Ft</div>
                        </div>
                        <div class="detail">
                            <div class="value">{property_data.get('year_built', '-')}</div>
                            <div class="label">Year Built</div>
                        </div>
                    </div>
                </div>

                <div class="description">
                    <h3>Property Description</h3>
                    <p>{property_data.get('description', 'Contact agent for more details about this beautiful property.')}</p>

                    <h3>Features</h3>
                    <ul>
                        {''.join(f"<li>{feature}</li>" for feature in property_data.get('features', ['Contact for details']))}
                    </ul>
                </div>

                <div class="agent">
                    <div class="agent-info">
                        <h3>{agent_name}</h3>
                        <p>TD Realty</p>
                    </div>
                    <div class="agent-contact">
                        <p>{agent_phone}</p>
                        <p>{agent_email}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return self._save_report(
            report_type=ReportType.PROPERTY_FLYER,
            title=f"Flyer - {property_data.get('address', 'Property')}",
            html_content=html_content,
            generated_by=agent_name,
            metadata={'property': property_data.get('address')}
        )

    def _calculate_estimated_value(
        self,
        property_data: Dict,
        comparables: List[Dict]
    ) -> float:
        """Calculate estimated property value from comparables."""
        if not comparables:
            return property_data.get('price', 0)

        # Simple average of comparable prices adjusted by sqft
        subject_sqft = property_data.get('sqft', 1)
        adjusted_values = []

        for comp in comparables:
            comp_sqft = comp.get('sqft', 1)
            comp_price = comp.get('sale_price', comp.get('price', 0))
            price_per_sqft = comp_price / comp_sqft if comp_sqft else 0
            adjusted_value = price_per_sqft * subject_sqft
            adjusted_values.append(adjusted_value)

        return sum(adjusted_values) / len(adjusted_values) if adjusted_values else 0

    def _get_report_styles(self) -> str:
        """Get common CSS styles for reports."""
        return """
            body {
                font-family: 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 8.5in;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
                color: white;
                padding: 40px;
                margin: -20px -20px 30px -20px;
                text-align: center;
            }
            .header h1 { margin: 0; font-size: 28px; }
            .header h2 { margin: 10px 0 0 0; font-weight: normal; opacity: 0.9; }
            .header p { margin: 10px 0 0 0; opacity: 0.8; }
            .section {
                margin-bottom: 30px;
                page-break-inside: avoid;
            }
            .section h3 {
                color: #1e40af;
                border-bottom: 2px solid #e2e8f0;
                padding-bottom: 10px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #e2e8f0;
            }
            th {
                background: #f8fafc;
                font-weight: 600;
                color: #1e40af;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin: 20px 0;
            }
            .stat {
                background: #f8fafc;
                padding: 20px;
                text-align: center;
                border-radius: 8px;
            }
            .stat-value {
                display: block;
                font-size: 28px;
                font-weight: bold;
                color: #1e40af;
            }
            .stat-label {
                display: block;
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
                margin-top: 5px;
            }
            .footer {
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #e2e8f0;
                text-align: center;
                color: #666;
                font-size: 12px;
            }
            @media print {
                body { margin: 0; padding: 0.5in; }
                .header { margin: -0.5in -0.5in 30px -0.5in; }
            }
        """

    def _render_cma_html(self, sections: List[ReportSection], property_address: str) -> str:
        """Render CMA report HTML."""
        html_parts = [f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                {self._get_report_styles()}
                .cover {{
                    height: 100vh;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    text-align: center;
                    page-break-after: always;
                }}
                .cover h1 {{ font-size: 36px; margin-bottom: 20px; }}
                .cover h2 {{ font-size: 24px; font-weight: normal; margin-bottom: 40px; }}
                .value-box {{
                    background: linear-gradient(135deg, #059669 0%, #10b981 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 12px;
                    text-align: center;
                    margin: 20px 0;
                }}
                .value-box .big {{ font-size: 42px; font-weight: bold; }}
                .comparable {{
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
        """]

        for section in sections:
            if section.content_type == "cover":
                html_parts.append(f"""
                <div class="cover">
                    <h1>{section.data['title']}</h1>
                    <h2>{section.data['subtitle']}</h2>
                    <p>Prepared for: {section.data['prepared_for']}</p>
                    <p>Prepared by: {section.data['prepared_by']}</p>
                    <p>{section.data['date']}</p>
                    <p><strong>{section.data['company']}</strong></p>
                </div>
                """)
            elif section.content_type == "text" and section.title == "Executive Summary":
                html_parts.append(f"""
                <div class="section">
                    <h3>{section.title}</h3>
                    <div class="value-box">
                        <div>Estimated Market Value</div>
                        <div class="big">${section.data['estimated_value']:,.0f}</div>
                        <div>Range: ${section.data['value_range'][0]:,.0f} - ${section.data['value_range'][1]:,.0f}</div>
                    </div>
                    <p><strong>Confidence Level:</strong> {section.data['confidence']}</p>
                    <p><strong>Market Trend:</strong> {section.data['market_trend']}</p>
                </div>
                """)
            elif section.content_type == "property_details":
                data = section.data
                html_parts.append(f"""
                <div class="section">
                    <h3>{section.title}</h3>
                    <div class="stats-grid">
                        <div class="stat">
                            <span class="stat-value">{data.get('beds', '-')}</span>
                            <span class="stat-label">Bedrooms</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">{data.get('baths', '-')}</span>
                            <span class="stat-label">Bathrooms</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">{data.get('sqft', '-'):,}</span>
                            <span class="stat-label">Sq Ft</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">{data.get('year_built', '-')}</span>
                            <span class="stat-label">Year Built</span>
                        </div>
                    </div>
                    <table>
                        <tr><td>Address</td><td>{data.get('address', '-')}</td></tr>
                        <tr><td>Lot Size</td><td>{data.get('lot_size', '-')}</td></tr>
                        <tr><td>Property Type</td><td>{data.get('property_type', '-')}</td></tr>
                        <tr><td>Garage</td><td>{data.get('garage', '-')}</td></tr>
                    </table>
                </div>
                """)
            elif section.content_type == "comparables":
                html_parts.append(f"""
                <div class="section">
                    <h3>{section.title}</h3>
                    <table>
                        <tr>
                            <th>Address</th>
                            <th>Sale Price</th>
                            <th>Beds/Baths</th>
                            <th>Sq Ft</th>
                            <th>$/Sq Ft</th>
                            <th>Sale Date</th>
                        </tr>
                """)
                for comp in section.data:
                    price = comp.get('sale_price', comp.get('price', 0))
                    sqft = comp.get('sqft', 1)
                    html_parts.append(f"""
                        <tr>
                            <td>{comp.get('address', '-')}</td>
                            <td>${price:,.0f}</td>
                            <td>{comp.get('beds', '-')}/{comp.get('baths', '-')}</td>
                            <td>{sqft:,}</td>
                            <td>${price/sqft:,.0f}</td>
                            <td>{comp.get('sale_date', '-')}</td>
                        </tr>
                    """)
                html_parts.append("</table></div>")

        html_parts.append("""
            <div class="footer">
                <p>This Comparative Market Analysis is an estimate of value based on available data.</p>
                <p>TD Realty | Central Ohio's Trusted Real Estate Partner</p>
            </div>
        </body>
        </html>
        """)

        return "".join(html_parts)

    def _save_report(
        self,
        report_type: ReportType,
        title: str,
        html_content: str,
        generated_by: str,
        metadata: Dict = None
    ) -> GeneratedReport:
        """Save report to file."""
        report_id = str(uuid.uuid4())
        filename = f"{report_type.value}_{report_id[:8]}.html"
        file_path = os.path.join(self.output_dir, filename)

        with open(file_path, 'w') as f:
            f.write(html_content)

        report = GeneratedReport(
            id=report_id,
            report_type=report_type,
            title=title,
            filename=filename,
            file_path=file_path,
            generated_at=datetime.now(),
            generated_by=generated_by,
            metadata=metadata or {},
            file_size=os.path.getsize(file_path)
        )

        self.generated_reports.append(report)
        return report

    def get_recent_reports(self, limit: int = 20) -> List[GeneratedReport]:
        """Get recently generated reports."""
        return sorted(
            self.generated_reports,
            key=lambda r: r.generated_at,
            reverse=True
        )[:limit]
