"""Pipeline analytics and stage tracking."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline stages for lead progression."""

    # Initial stages
    NEW = "new"
    CONTACTED = "contacted"
    RESPONDED = "responded"

    # Qualification
    QUALIFIED = "qualified"
    NURTURING = "nurturing"

    # Active engagement
    APPOINTMENT_SET = "appointment_set"
    MET_IN_PERSON = "met_in_person"

    # Buyer stages
    SHOWING_HOMES = "showing_homes"
    OFFER_SUBMITTED = "offer_submitted"

    # Seller stages
    LISTING_PRESENTATION = "listing_presentation"
    LISTING_SIGNED = "listing_signed"
    ACTIVE_LISTING = "active_listing"

    # Closing stages
    UNDER_CONTRACT = "under_contract"
    PENDING = "pending"
    CLOSED = "closed"

    # End states
    LOST = "lost"
    UNQUALIFIED = "unqualified"
    REFERRED_OUT = "referred_out"


@dataclass
class StageChange:
    """Record of a stage change."""

    id: str
    lead_id: str
    from_stage: Optional[PipelineStage]
    to_stage: PipelineStage
    changed_at: datetime
    changed_by: str = "system"
    notes: str = ""


class PipelineAnalytics:
    """Analyze pipeline performance and progression."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize pipeline analytics."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "pipeline_data.json"
        self.stage_changes: List[StageChange] = []
        self.lead_stages: Dict[str, PipelineStage] = {}
        self._load_data()

        # Stage progression paths
        self.buyer_path = [
            PipelineStage.NEW, PipelineStage.CONTACTED, PipelineStage.RESPONDED,
            PipelineStage.QUALIFIED, PipelineStage.APPOINTMENT_SET, PipelineStage.MET_IN_PERSON,
            PipelineStage.SHOWING_HOMES, PipelineStage.OFFER_SUBMITTED,
            PipelineStage.UNDER_CONTRACT, PipelineStage.PENDING, PipelineStage.CLOSED
        ]

        self.seller_path = [
            PipelineStage.NEW, PipelineStage.CONTACTED, PipelineStage.RESPONDED,
            PipelineStage.QUALIFIED, PipelineStage.LISTING_PRESENTATION,
            PipelineStage.LISTING_SIGNED, PipelineStage.ACTIVE_LISTING,
            PipelineStage.UNDER_CONTRACT, PipelineStage.PENDING, PipelineStage.CLOSED
        ]

    def _load_data(self):
        """Load pipeline data from file."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for change_data in data.get("stage_changes", []):
                        self.stage_changes.append(StageChange(
                            id=change_data["id"],
                            lead_id=change_data["lead_id"],
                            from_stage=PipelineStage(change_data["from_stage"]) if change_data.get("from_stage") else None,
                            to_stage=PipelineStage(change_data["to_stage"]),
                            changed_at=datetime.fromisoformat(change_data["changed_at"]),
                            changed_by=change_data.get("changed_by", "system"),
                            notes=change_data.get("notes", "")
                        ))

                    for lead_id, stage in data.get("lead_stages", {}).items():
                        self.lead_stages[lead_id] = PipelineStage(stage)

            except Exception as e:
                logger.error(f"Error loading pipeline data: {e}")

    def _save_data(self):
        """Save pipeline data to file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "stage_changes": [
                {
                    "id": sc.id,
                    "lead_id": sc.lead_id,
                    "from_stage": sc.from_stage.value if sc.from_stage else None,
                    "to_stage": sc.to_stage.value,
                    "changed_at": sc.changed_at.isoformat(),
                    "changed_by": sc.changed_by,
                    "notes": sc.notes
                }
                for sc in self.stage_changes
            ],
            "lead_stages": {
                lead_id: stage.value
                for lead_id, stage in self.lead_stages.items()
            },
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def move_lead(
        self,
        lead_id: str,
        to_stage: PipelineStage,
        changed_by: str = "system",
        notes: str = ""
    ) -> StageChange:
        """Move a lead to a new stage."""
        from_stage = self.lead_stages.get(lead_id)

        change = StageChange(
            id=str(uuid.uuid4())[:8],
            lead_id=lead_id,
            from_stage=from_stage,
            to_stage=to_stage,
            changed_at=datetime.now(),
            changed_by=changed_by,
            notes=notes
        )

        self.stage_changes.append(change)
        self.lead_stages[lead_id] = to_stage
        self._save_data()

        return change

    def get_lead_stage(self, lead_id: str) -> Optional[PipelineStage]:
        """Get current stage for a lead."""
        return self.lead_stages.get(lead_id)

    def get_lead_history(self, lead_id: str) -> List[StageChange]:
        """Get stage change history for a lead."""
        return [
            sc for sc in self.stage_changes
            if sc.lead_id == lead_id
        ]

    def get_pipeline_snapshot(self) -> Dict[str, int]:
        """Get current count of leads in each stage."""
        snapshot = {stage.value: 0 for stage in PipelineStage}

        for stage in self.lead_stages.values():
            snapshot[stage.value] += 1

        return snapshot

    def get_pipeline_value(
        self,
        avg_transaction_value: float = 350000,
        commission_rate: float = 0.03
    ) -> Dict[str, Any]:
        """Estimate pipeline value based on stage probabilities."""
        # Probability of closing by stage
        stage_probabilities = {
            PipelineStage.NEW: 0.02,
            PipelineStage.CONTACTED: 0.03,
            PipelineStage.RESPONDED: 0.05,
            PipelineStage.QUALIFIED: 0.10,
            PipelineStage.NURTURING: 0.05,
            PipelineStage.APPOINTMENT_SET: 0.15,
            PipelineStage.MET_IN_PERSON: 0.25,
            PipelineStage.SHOWING_HOMES: 0.35,
            PipelineStage.OFFER_SUBMITTED: 0.50,
            PipelineStage.LISTING_PRESENTATION: 0.30,
            PipelineStage.LISTING_SIGNED: 0.70,
            PipelineStage.ACTIVE_LISTING: 0.75,
            PipelineStage.UNDER_CONTRACT: 0.90,
            PipelineStage.PENDING: 0.95,
            PipelineStage.CLOSED: 1.0,
            PipelineStage.LOST: 0,
            PipelineStage.UNQUALIFIED: 0,
            PipelineStage.REFERRED_OUT: 0
        }

        snapshot = self.get_pipeline_snapshot()
        commission_per_deal = avg_transaction_value * commission_rate

        stage_values = {}
        total_weighted = 0
        total_possible = 0

        for stage, count in snapshot.items():
            if count == 0:
                continue

            stage_enum = PipelineStage(stage)
            probability = stage_probabilities.get(stage_enum, 0)
            possible_value = count * commission_per_deal
            weighted_value = possible_value * probability

            stage_values[stage] = {
                "count": count,
                "probability": probability,
                "possible_value": possible_value,
                "weighted_value": weighted_value
            }

            total_weighted += weighted_value
            total_possible += possible_value

        return {
            "by_stage": stage_values,
            "total_leads_in_pipeline": sum(snapshot.values()),
            "total_possible_value": total_possible,
            "total_weighted_value": total_weighted,
            "avg_probability": total_weighted / total_possible if total_possible > 0 else 0
        }

    def get_conversion_rates(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """Calculate conversion rates between stages."""
        if not start_date:
            start_date = datetime.now() - timedelta(days=365)
        if not end_date:
            end_date = datetime.now()

        # Filter changes in date range
        changes = [
            sc for sc in self.stage_changes
            if start_date <= sc.changed_at <= end_date
        ]

        # Count transitions
        transitions: Dict[str, Dict[str, int]] = {}

        for change in changes:
            if not change.from_stage:
                continue

            from_key = change.from_stage.value
            to_key = change.to_stage.value

            if from_key not in transitions:
                transitions[from_key] = {}

            transitions[from_key][to_key] = transitions[from_key].get(to_key, 0) + 1

        # Calculate rates
        rates = {}

        for from_stage, to_stages in transitions.items():
            total_exits = sum(to_stages.values())
            rates[from_stage] = {
                to_stage: round(count / total_exits * 100, 1)
                for to_stage, count in to_stages.items()
            }
            rates[from_stage]["_total"] = total_exits

        return rates

    def get_stage_velocity(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """Calculate average time spent in each stage."""
        if not start_date:
            start_date = datetime.now() - timedelta(days=365)
        if not end_date:
            end_date = datetime.now()

        # Group changes by lead
        lead_changes: Dict[str, List[StageChange]] = {}

        for change in self.stage_changes:
            if change.changed_at < start_date or change.changed_at > end_date:
                continue

            if change.lead_id not in lead_changes:
                lead_changes[change.lead_id] = []
            lead_changes[change.lead_id].append(change)

        # Calculate time in each stage
        stage_times: Dict[str, List[float]] = {stage.value: [] for stage in PipelineStage}

        for lead_id, changes in lead_changes.items():
            changes.sort(key=lambda x: x.changed_at)

            for i, change in enumerate(changes):
                if i == 0:
                    continue

                prev_change = changes[i - 1]
                days_in_stage = (change.changed_at - prev_change.changed_at).total_seconds() / 86400

                if prev_change.to_stage:
                    stage_times[prev_change.to_stage.value].append(days_in_stage)

        # Calculate averages
        velocities = {}

        for stage, times in stage_times.items():
            if times:
                velocities[stage] = {
                    "avg_days": round(sum(times) / len(times), 1),
                    "min_days": round(min(times), 1),
                    "max_days": round(max(times), 1),
                    "sample_size": len(times)
                }

        return velocities

    def get_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identify pipeline bottlenecks."""
        velocity = self.get_stage_velocity()
        conversion_rates = self.get_conversion_rates()
        snapshot = self.get_pipeline_snapshot()

        bottlenecks = []

        for stage_value, data in velocity.items():
            stage = PipelineStage(stage_value)

            # Skip end states
            if stage in [PipelineStage.CLOSED, PipelineStage.LOST, PipelineStage.UNQUALIFIED]:
                continue

            issues = []

            # Check if too many leads stuck
            count = snapshot.get(stage_value, 0)
            if count > 10:
                issues.append(f"High volume: {count} leads")

            # Check if slow progression
            if data.get("avg_days", 0) > 30:
                issues.append(f"Slow progression: {data['avg_days']} avg days")

            # Check if low conversion out
            if stage_value in conversion_rates:
                total_exits = conversion_rates[stage_value].get("_total", 0)
                if total_exits < 5:
                    issues.append("Low exit volume")

            if issues:
                bottlenecks.append({
                    "stage": stage_value,
                    "issues": issues,
                    "leads_count": count,
                    "avg_days": data.get("avg_days", 0),
                    "recommendation": self._get_bottleneck_recommendation(stage, issues)
                })

        return sorted(bottlenecks, key=lambda x: len(x["issues"]), reverse=True)

    def _get_bottleneck_recommendation(self, stage: PipelineStage, issues: List[str]) -> str:
        """Get recommendation for addressing a bottleneck."""
        recommendations = {
            PipelineStage.NEW: "Set up automated initial outreach within 5 minutes of lead creation",
            PipelineStage.CONTACTED: "Increase follow-up frequency or try different contact methods",
            PipelineStage.RESPONDED: "Schedule qualifying calls more quickly",
            PipelineStage.QUALIFIED: "Speed up appointment setting with online scheduling",
            PipelineStage.APPOINTMENT_SET: "Send reminders and reduce no-shows",
            PipelineStage.SHOWING_HOMES: "Increase showing frequency or expand search criteria",
            PipelineStage.OFFER_SUBMITTED: "Improve offer competitiveness or expand options",
            PipelineStage.LISTING_PRESENTATION: "Refine presentation and follow up faster",
            PipelineStage.ACTIVE_LISTING: "Review pricing strategy and marketing",
        }

        return recommendations.get(stage, "Review stage process and follow-up sequence")

    def get_lead_score_correlation(self, leads_with_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze correlation between lead scores and pipeline progression."""
        # Group leads by tier
        tier_progression = {
            "hot": {"closed": 0, "lost": 0, "active": 0},
            "warm": {"closed": 0, "lost": 0, "active": 0},
            "lukewarm": {"closed": 0, "lost": 0, "active": 0},
            "cold": {"closed": 0, "lost": 0, "active": 0}
        }

        for lead in leads_with_scores:
            lead_id = lead.get("id")
            tier = lead.get("tier", "cold").lower()
            stage = self.lead_stages.get(str(lead_id))

            if not stage:
                continue

            if tier not in tier_progression:
                tier = "cold"

            if stage == PipelineStage.CLOSED:
                tier_progression[tier]["closed"] += 1
            elif stage in [PipelineStage.LOST, PipelineStage.UNQUALIFIED]:
                tier_progression[tier]["lost"] += 1
            else:
                tier_progression[tier]["active"] += 1

        # Calculate conversion rates by tier
        tier_rates = {}
        for tier, counts in tier_progression.items():
            total = sum(counts.values())
            if total > 0:
                tier_rates[tier] = {
                    "total": total,
                    "closed": counts["closed"],
                    "conversion_rate": round(counts["closed"] / total * 100, 1),
                    "loss_rate": round(counts["lost"] / total * 100, 1)
                }

        return {
            "by_tier": tier_rates,
            "scoring_effectiveness": self._evaluate_scoring_effectiveness(tier_rates)
        }

    def _evaluate_scoring_effectiveness(self, tier_rates: Dict[str, Dict]) -> str:
        """Evaluate if the scoring system is working."""
        if not tier_rates:
            return "Insufficient data"

        hot_rate = tier_rates.get("hot", {}).get("conversion_rate", 0)
        warm_rate = tier_rates.get("warm", {}).get("conversion_rate", 0)
        cold_rate = tier_rates.get("cold", {}).get("conversion_rate", 0)

        if hot_rate > warm_rate > cold_rate and hot_rate > cold_rate * 2:
            return "Excellent - scoring is highly predictive"
        elif hot_rate > cold_rate:
            return "Good - scoring shows correlation with outcomes"
        else:
            return "Needs calibration - scores not correlating with conversions"
