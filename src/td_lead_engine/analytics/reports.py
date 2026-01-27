"""Report generation for lead analytics."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path


@dataclass
class LeadReport:
    """A generated lead report."""

    report_type: str  # "daily", "weekly", "monthly", "custom"
    period_start: datetime
    period_end: datetime

    # Summary stats
    total_leads: int = 0
    new_leads: int = 0
    scored_leads: int = 0

    # By tier
    tier_counts: Dict[str, int] = field(default_factory=dict)
    tier_changes: Dict[str, int] = field(default_factory=dict)  # Leads that moved up/down

    # By source
    source_counts: Dict[str, int] = field(default_factory=dict)
    source_quality: Dict[str, float] = field(default_factory=dict)  # Avg score by source

    # Top leads
    top_hot_leads: List[Dict[str, Any]] = field(default_factory=list)
    top_movers: List[Dict[str, Any]] = field(default_factory=list)  # Biggest score increases

    # Conversion tracking
    leads_contacted: int = 0
    leads_responded: int = 0
    leads_converted: int = 0

    # Signal analysis
    top_signals: List[Dict[str, Any]] = field(default_factory=list)

    generated_at: datetime = field(default_factory=datetime.now)


class ReportGenerator:
    """Generate analytics reports."""

    def __init__(self, db=None):
        """Initialize report generator."""
        self.db = db

    def generate_daily_report(self, date: Optional[datetime] = None) -> LeadReport:
        """Generate a daily report."""
        if date is None:
            date = datetime.now()

        period_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)

        return self._generate_report("daily", period_start, period_end)

    def generate_weekly_report(self, week_start: Optional[datetime] = None) -> LeadReport:
        """Generate a weekly report."""
        if week_start is None:
            today = datetime.now()
            # Get Monday of current week
            week_start = today - timedelta(days=today.weekday())

        period_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(weeks=1)

        return self._generate_report("weekly", period_start, period_end)

    def generate_monthly_report(self, month: Optional[int] = None, year: Optional[int] = None) -> LeadReport:
        """Generate a monthly report."""
        now = datetime.now()
        if month is None:
            month = now.month
        if year is None:
            year = now.year

        period_start = datetime(year, month, 1)
        if month == 12:
            period_end = datetime(year + 1, 1, 1)
        else:
            period_end = datetime(year, month + 1, 1)

        return self._generate_report("monthly", period_start, period_end)

    def _generate_report(
        self,
        report_type: str,
        period_start: datetime,
        period_end: datetime
    ) -> LeadReport:
        """Generate a report for a time period."""
        from ..storage.database import LeadDatabase

        db = self.db or LeadDatabase()
        stats = db.get_stats()

        report = LeadReport(
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            total_leads=stats.get("total_leads", 0),
            tier_counts=stats.get("by_tier", {}),
            source_counts=stats.get("by_source", {}),
        )

        # Get hot leads
        hot_leads = db.get_hot_leads(limit=10)
        report.top_hot_leads = [
            {
                "id": lead.id,
                "name": lead.display_name,
                "score": lead.score,
                "source": lead.source,
                "contact": lead.contact_info,
            }
            for lead in hot_leads
        ]

        # Calculate source quality (average score by source)
        all_leads = db.get_all_leads(limit=10000)
        source_scores: Dict[str, List[int]] = {}
        for lead in all_leads:
            if lead.source not in source_scores:
                source_scores[lead.source] = []
            source_scores[lead.source].append(lead.score)

        for source, scores in source_scores.items():
            if scores:
                report.source_quality[source] = sum(scores) / len(scores)

        # Analyze signals
        signal_counts: Dict[str, int] = {}
        for lead in all_leads:
            if lead.score_breakdown:
                try:
                    breakdown = json.loads(lead.score_breakdown)
                    for match in breakdown.get("matches", []):
                        phrase = match["phrase"]
                        signal_counts[phrase] = signal_counts.get(phrase, 0) + 1
                except Exception:
                    pass

        # Top 10 signals
        sorted_signals = sorted(signal_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        report.top_signals = [
            {"phrase": phrase, "count": count}
            for phrase, count in sorted_signals
        ]

        return report

    def format_report_text(self, report: LeadReport) -> str:
        """Format a report as plain text."""
        lines = [
            f"{'=' * 60}",
            f"LEAD REPORT - {report.report_type.upper()}",
            f"Period: {report.period_start.strftime('%Y-%m-%d')} to {report.period_end.strftime('%Y-%m-%d')}",
            f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M')}",
            f"{'=' * 60}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Leads: {report.total_leads}",
            "",
            "BY TIER",
            "-" * 40,
        ]

        for tier, count in sorted(report.tier_counts.items()):
            lines.append(f"  {tier.capitalize()}: {count}")

        lines.extend([
            "",
            "BY SOURCE",
            "-" * 40,
        ])

        for source, count in sorted(report.source_counts.items(), key=lambda x: x[1], reverse=True):
            avg_score = report.source_quality.get(source, 0)
            lines.append(f"  {source}: {count} leads (avg score: {avg_score:.1f})")

        if report.top_hot_leads:
            lines.extend([
                "",
                "TOP HOT LEADS",
                "-" * 40,
            ])
            for i, lead in enumerate(report.top_hot_leads[:5], 1):
                lines.append(f"  {i}. {lead['name']} (Score: {lead['score']}) - {lead['source']}")

        if report.top_signals:
            lines.extend([
                "",
                "TOP SIGNALS",
                "-" * 40,
            ])
            for signal in report.top_signals[:5]:
                lines.append(f"  \"{signal['phrase']}\": {signal['count']} occurrences")

        lines.append(f"\n{'=' * 60}")

        return "\n".join(lines)

    def format_report_html(self, report: LeadReport) -> str:
        """Format a report as HTML."""
        tier_rows = "\n".join(
            f"<tr><td>{tier.capitalize()}</td><td>{count}</td></tr>"
            for tier, count in sorted(report.tier_counts.items())
        )

        source_rows = "\n".join(
            f"<tr><td>{source}</td><td>{count}</td><td>{report.source_quality.get(source, 0):.1f}</td></tr>"
            for source, count in sorted(report.source_counts.items(), key=lambda x: x[1], reverse=True)
        )

        hot_lead_rows = "\n".join(
            f"<tr><td>{lead['name']}</td><td>{lead['score']}</td><td>{lead['source']}</td></tr>"
            for lead in report.top_hot_leads[:5]
        )

        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Lead Report - {report.report_type.capitalize()}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; }}
        h1 {{ color: #1e293b; }}
        h2 {{ color: #475569; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }}
        table {{ border-collapse: collapse; width: 100%; max-width: 600px; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #f1f5f9; }}
        .meta {{ color: #64748b; font-size: 14px; }}
    </style>
</head>
<body>
    <h1>Lead Report - {report.report_type.capitalize()}</h1>
    <p class="meta">
        Period: {report.period_start.strftime('%B %d, %Y')} - {report.period_end.strftime('%B %d, %Y')}<br>
        Generated: {report.generated_at.strftime('%B %d, %Y at %H:%M')}
    </p>

    <h2>Summary</h2>
    <p><strong>Total Leads:</strong> {report.total_leads}</p>

    <h2>Leads by Tier</h2>
    <table>
        <tr><th>Tier</th><th>Count</th></tr>
        {tier_rows}
    </table>

    <h2>Leads by Source</h2>
    <table>
        <tr><th>Source</th><th>Count</th><th>Avg Score</th></tr>
        {source_rows}
    </table>

    <h2>Top Hot Leads</h2>
    <table>
        <tr><th>Name</th><th>Score</th><th>Source</th></tr>
        {hot_lead_rows}
    </table>
</body>
</html>
"""

    def save_report(self, report: LeadReport, path: Path, format: str = "html"):
        """Save a report to file."""
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "html":
            content = self.format_report_html(report)
        elif format == "json":
            content = json.dumps({
                "report_type": report.report_type,
                "period_start": report.period_start.isoformat(),
                "period_end": report.period_end.isoformat(),
                "total_leads": report.total_leads,
                "tier_counts": report.tier_counts,
                "source_counts": report.source_counts,
                "source_quality": report.source_quality,
                "top_hot_leads": report.top_hot_leads,
                "top_signals": report.top_signals,
                "generated_at": report.generated_at.isoformat(),
            }, indent=2)
        else:
            content = self.format_report_text(report)

        with open(path, 'w') as f:
            f.write(content)
