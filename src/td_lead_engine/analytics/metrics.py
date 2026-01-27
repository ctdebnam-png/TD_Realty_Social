"""Metrics collection for lead engine analytics."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DailyMetrics:
    """Metrics for a single day."""

    date: str  # YYYY-MM-DD
    leads_imported: int = 0
    leads_scored: int = 0
    hot_leads_found: int = 0
    warm_leads_found: int = 0
    imports_by_source: Dict[str, int] = field(default_factory=dict)
    avg_score: float = 0.0


class MetricsCollector:
    """Collect and store lead engine metrics over time."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize metrics collector."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "metrics.json"
        self.daily_metrics: Dict[str, DailyMetrics] = {}
        self._load_data()

    def _load_data(self):
        """Load historical metrics."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    for date_str, metrics_data in data.get("daily", {}).items():
                        self.daily_metrics[date_str] = DailyMetrics(
                            date=date_str,
                            leads_imported=metrics_data.get("leads_imported", 0),
                            leads_scored=metrics_data.get("leads_scored", 0),
                            hot_leads_found=metrics_data.get("hot_leads_found", 0),
                            warm_leads_found=metrics_data.get("warm_leads_found", 0),
                            imports_by_source=metrics_data.get("imports_by_source", {}),
                            avg_score=metrics_data.get("avg_score", 0.0),
                        )
            except Exception as e:
                logger.error(f"Error loading metrics: {e}")

    def _save_data(self):
        """Save metrics to file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "daily": {
                date: {
                    "leads_imported": m.leads_imported,
                    "leads_scored": m.leads_scored,
                    "hot_leads_found": m.hot_leads_found,
                    "warm_leads_found": m.warm_leads_found,
                    "imports_by_source": m.imports_by_source,
                    "avg_score": m.avg_score,
                }
                for date, m in self.daily_metrics.items()
            }
        }
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _get_today(self) -> str:
        """Get today's date string."""
        return datetime.now().strftime("%Y-%m-%d")

    def _get_or_create_today(self) -> DailyMetrics:
        """Get or create today's metrics."""
        today = self._get_today()
        if today not in self.daily_metrics:
            self.daily_metrics[today] = DailyMetrics(date=today)
        return self.daily_metrics[today]

    def record_import(self, source: str, count: int):
        """Record leads imported."""
        metrics = self._get_or_create_today()
        metrics.leads_imported += count
        if source not in metrics.imports_by_source:
            metrics.imports_by_source[source] = 0
        metrics.imports_by_source[source] += count
        self._save_data()

    def record_scoring(self, count: int, hot: int, warm: int, avg_score: float):
        """Record scoring results."""
        metrics = self._get_or_create_today()
        metrics.leads_scored += count
        metrics.hot_leads_found += hot
        metrics.warm_leads_found += warm
        metrics.avg_score = avg_score
        self._save_data()

    def get_metrics_for_period(self, days: int = 30) -> List[DailyMetrics]:
        """Get metrics for the last N days."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        result = []
        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            if date_str in self.daily_metrics:
                result.append(self.daily_metrics[date_str])
            else:
                result.append(DailyMetrics(date=date_str))
            current += timedelta(days=1)

        return result

    def get_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get summary metrics for a period."""
        metrics = self.get_metrics_for_period(days)

        total_imported = sum(m.leads_imported for m in metrics)
        total_scored = sum(m.leads_scored for m in metrics)
        total_hot = sum(m.hot_leads_found for m in metrics)
        total_warm = sum(m.warm_leads_found for m in metrics)

        # Imports by source
        source_totals: Dict[str, int] = {}
        for m in metrics:
            for source, count in m.imports_by_source.items():
                source_totals[source] = source_totals.get(source, 0) + count

        # Average score (weighted)
        total_avg = 0.0
        count_with_avg = 0
        for m in metrics:
            if m.avg_score > 0:
                total_avg += m.avg_score
                count_with_avg += 1

        avg_score = total_avg / count_with_avg if count_with_avg > 0 else 0.0

        return {
            "period_days": days,
            "total_imported": total_imported,
            "total_scored": total_scored,
            "total_hot_leads": total_hot,
            "total_warm_leads": total_warm,
            "avg_daily_imports": total_imported / days if days > 0 else 0,
            "avg_score": round(avg_score, 1),
            "imports_by_source": source_totals,
        }

    def get_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get trend data for visualization."""
        metrics = self.get_metrics_for_period(days)

        return {
            "dates": [m.date for m in metrics],
            "imports": [m.leads_imported for m in metrics],
            "hot_leads": [m.hot_leads_found for m in metrics],
            "warm_leads": [m.warm_leads_found for m in metrics],
            "avg_scores": [m.avg_score for m in metrics],
        }
