"""REST API application for TD Lead Engine."""

import json
import logging
import os
from datetime import datetime
from typing import Optional

from flask import Flask, jsonify, request, g
from flask_cors import CORS

from .auth import require_api_key, rate_limit, generate_api_key, get_key_manager

logger = logging.getLogger(__name__)


def create_app(config: Optional[dict] = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    app.config["SECRET_KEY"] = os.environ.get("TD_ENGINE_SECRET_KEY", "dev-secret-key")
    app.config["DATABASE_PATH"] = os.environ.get("TD_ENGINE_DB_PATH", "~/.td-lead-engine/leads.db")

    if config:
        app.config.update(config)

    # Enable CORS
    CORS(app, origins=["*"], supports_credentials=True)

    # Initialize components lazily
    _db = None
    _scoring_engine = None
    _roi_tracker = None
    _pipeline = None
    _router = None

    def get_db():
        nonlocal _db
        if _db is None:
            from ..storage import Database
            _db = Database(os.path.expanduser(app.config["DATABASE_PATH"]))
        return _db

    def get_scoring_engine():
        nonlocal _scoring_engine
        if _scoring_engine is None:
            from ..core import ScoringEngine
            _scoring_engine = ScoringEngine()
        return _scoring_engine

    def get_roi_tracker():
        nonlocal _roi_tracker
        if _roi_tracker is None:
            from ..analytics import ROITracker
            _roi_tracker = ROITracker()
        return _roi_tracker

    def get_pipeline():
        nonlocal _pipeline
        if _pipeline is None:
            from ..analytics import PipelineAnalytics
            _pipeline = PipelineAnalytics()
        return _pipeline

    def get_router():
        nonlocal _router
        if _router is None:
            from ..routing import LeadRouter
            _router = LeadRouter()
        return _router

    # ==================== Health & Info ====================

    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "version": "2.0.0",
            "timestamp": datetime.now().isoformat()
        })

    @app.route("/api/info", methods=["GET"])
    def api_info():
        """API information."""
        return jsonify({
            "name": "TD Lead Engine API",
            "version": "2.0.0",
            "description": "Social media lead scoring and management for real estate",
            "documentation": "/api/docs",
            "endpoints": {
                "leads": "/api/leads",
                "scoring": "/api/score",
                "analytics": "/api/analytics",
                "pipeline": "/api/pipeline",
                "routing": "/api/routing"
            }
        })

    # ==================== Leads ====================

    @app.route("/api/leads", methods=["GET"])
    @require_api_key(scopes=["read", "leads"])
    @rate_limit()
    def list_leads():
        """List leads with filtering and pagination."""
        db = get_db()

        # Pagination
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 50, type=int), 100)
        offset = (page - 1) * per_page

        # Filters
        tier = request.args.get("tier")
        source = request.args.get("source")
        status = request.args.get("status")
        search = request.args.get("q")
        min_score = request.args.get("min_score", type=int)

        # Build query
        leads = db.search_leads(
            query=search,
            tier=tier,
            source=source,
            limit=per_page,
            offset=offset
        )

        # Filter by min score if specified
        if min_score:
            leads = [l for l in leads if l.score >= min_score]

        # Convert to dict
        leads_data = [
            {
                "id": l.id,
                "name": l.name,
                "email": l.email,
                "phone": l.phone,
                "source": l.source,
                "score": l.score,
                "tier": l.tier,
                "status": l.status,
                "tags": l.tags.split(",") if l.tags else [],
                "created_at": l.created_at,
                "updated_at": l.updated_at
            }
            for l in leads
        ]

        return jsonify({
            "leads": leads_data,
            "page": page,
            "per_page": per_page,
            "total": len(leads_data)  # Would need count query for actual total
        })

    @app.route("/api/leads/<int:lead_id>", methods=["GET"])
    @require_api_key(scopes=["read", "leads"])
    @rate_limit()
    def get_lead(lead_id: int):
        """Get a single lead by ID."""
        db = get_db()
        lead = db.get_lead(lead_id)

        if not lead:
            return jsonify({"error": "Lead not found"}), 404

        return jsonify({
            "id": lead.id,
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "username": lead.username,
            "bio": lead.bio,
            "source": lead.source,
            "source_id": lead.source_id,
            "score": lead.score,
            "tier": lead.tier,
            "status": lead.status,
            "tags": lead.tags.split(",") if lead.tags else [],
            "notes": lead.notes,
            "followers": lead.followers,
            "score_breakdown": json.loads(lead.score_breakdown) if lead.score_breakdown else None,
            "created_at": lead.created_at,
            "updated_at": lead.updated_at
        })

    @app.route("/api/leads", methods=["POST"])
    @require_api_key(scopes=["write", "leads"])
    @rate_limit()
    def create_lead():
        """Create a new lead."""
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body required"}), 400

        required_fields = ["name"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({"error": f"Missing required fields: {missing}"}), 400

        db = get_db()
        scoring_engine = get_scoring_engine()

        # Create lead object
        from ..storage.models import Lead
        lead = Lead(
            name=data["name"],
            email=data.get("email"),
            phone=data.get("phone"),
            username=data.get("username"),
            bio=data.get("bio"),
            source=data.get("source", "api"),
            source_id=data.get("source_id"),
            followers=data.get("followers", 0)
        )

        # Score the lead
        if lead.bio:
            score_result = scoring_engine.score(lead.bio)
            lead.score = score_result["score"]
            lead.tier = score_result["tier"]
            lead.score_breakdown = json.dumps(score_result)

        # Save to database
        lead_id = db.add_lead(lead)

        return jsonify({
            "id": lead_id,
            "message": "Lead created successfully",
            "score": lead.score,
            "tier": lead.tier
        }), 201

    @app.route("/api/leads/<int:lead_id>", methods=["PUT", "PATCH"])
    @require_api_key(scopes=["write", "leads"])
    @rate_limit()
    def update_lead(lead_id: int):
        """Update a lead."""
        db = get_db()
        lead = db.get_lead(lead_id)

        if not lead:
            return jsonify({"error": "Lead not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400

        # Update fields
        updatable_fields = ["name", "email", "phone", "bio", "status", "tags", "notes"]
        for field in updatable_fields:
            if field in data:
                setattr(lead, field, data[field])

        # Re-score if bio changed
        if "bio" in data and data["bio"]:
            scoring_engine = get_scoring_engine()
            score_result = scoring_engine.score(data["bio"])
            lead.score = score_result["score"]
            lead.tier = score_result["tier"]
            lead.score_breakdown = json.dumps(score_result)

        db.update_lead(lead)

        return jsonify({
            "id": lead_id,
            "message": "Lead updated successfully",
            "score": lead.score,
            "tier": lead.tier
        })

    @app.route("/api/leads/<int:lead_id>", methods=["DELETE"])
    @require_api_key(scopes=["admin"])
    @rate_limit()
    def delete_lead(lead_id: int):
        """Delete a lead."""
        db = get_db()

        if not db.get_lead(lead_id):
            return jsonify({"error": "Lead not found"}), 404

        db.delete_lead(lead_id)

        return jsonify({
            "message": "Lead deleted successfully"
        })

    # ==================== Scoring ====================

    @app.route("/api/score", methods=["POST"])
    @require_api_key(scopes=["read", "scoring"])
    @rate_limit()
    def score_text():
        """Score text for real estate intent signals."""
        data = request.get_json()

        if not data or "text" not in data:
            return jsonify({"error": "text field required"}), 400

        scoring_engine = get_scoring_engine()
        result = scoring_engine.score(data["text"])

        return jsonify({
            "score": result["score"],
            "tier": result["tier"],
            "matches": result.get("matches", []),
            "categories": result.get("categories", {})
        })

    @app.route("/api/leads/<int:lead_id>/rescore", methods=["POST"])
    @require_api_key(scopes=["write", "scoring"])
    @rate_limit()
    def rescore_lead(lead_id: int):
        """Re-score a lead."""
        db = get_db()
        lead = db.get_lead(lead_id)

        if not lead:
            return jsonify({"error": "Lead not found"}), 404

        if not lead.bio:
            return jsonify({"error": "Lead has no bio to score"}), 400

        scoring_engine = get_scoring_engine()
        result = scoring_engine.score(lead.bio)

        lead.score = result["score"]
        lead.tier = result["tier"]
        lead.score_breakdown = json.dumps(result)
        db.update_lead(lead)

        return jsonify({
            "id": lead_id,
            "score": result["score"],
            "tier": result["tier"],
            "matches": result.get("matches", [])
        })

    # ==================== Analytics ====================

    @app.route("/api/analytics/summary", methods=["GET"])
    @require_api_key(scopes=["read", "analytics"])
    @rate_limit()
    def analytics_summary():
        """Get analytics summary."""
        db = get_db()
        stats = db.get_stats()

        roi_tracker = get_roi_tracker()
        roi_summary = roi_tracker.get_summary(period_days=30)

        return jsonify({
            "leads": {
                "total": stats.get("total_leads", 0),
                "by_tier": stats.get("by_tier", {}),
                "by_source": stats.get("by_source", {}),
                "recent_7_days": stats.get("recent_7_days", 0)
            },
            "roi": {
                "total_cost": roi_summary.get("total_cost", 0),
                "total_revenue": roi_summary.get("total_revenue", 0),
                "roi_percent": roi_summary.get("roi_percent", 0),
                "conversion_rate": roi_summary.get("conversion_rate", 0)
            }
        })

    @app.route("/api/analytics/roi", methods=["GET"])
    @require_api_key(scopes=["read", "analytics"])
    @rate_limit()
    def roi_analytics():
        """Get ROI analytics by source."""
        roi_tracker = get_roi_tracker()

        days = request.args.get("days", 365, type=int)
        start_date = datetime.now() - __import__("datetime").timedelta(days=days)

        roi_by_source = roi_tracker.get_roi_by_source(start_date=start_date)

        return jsonify({
            "period_days": days,
            "by_source": roi_by_source,
            "summary": roi_tracker.get_summary(period_days=days)
        })

    @app.route("/api/analytics/roi/record", methods=["POST"])
    @require_api_key(scopes=["write", "analytics"])
    @rate_limit()
    def record_cost():
        """Record advertising cost."""
        data = request.get_json()

        required = ["source", "campaign", "cost"]
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {missing}"}), 400

        roi_tracker = get_roi_tracker()
        cost = roi_tracker.record_cost(
            source=data["source"],
            campaign=data["campaign"],
            cost=data["cost"],
            impressions=data.get("impressions", 0),
            clicks=data.get("clicks", 0),
            leads_generated=data.get("leads_generated", 1)
        )

        return jsonify({
            "message": "Cost recorded",
            "cost_per_lead": cost.cost_per_lead
        }), 201

    @app.route("/api/analytics/conversion", methods=["POST"])
    @require_api_key(scopes=["write", "analytics"])
    @rate_limit()
    def record_conversion():
        """Record a conversion event."""
        data = request.get_json()

        required = ["lead_id", "transaction_value"]
        missing = [f for f in required if f not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {missing}"}), 400

        roi_tracker = get_roi_tracker()
        conversion = roi_tracker.record_conversion(
            lead_id=data["lead_id"],
            lead_source=data.get("lead_source", "unknown"),
            event_type=data.get("event_type", "closed"),
            transaction_value=data["transaction_value"],
            commission_rate=data.get("commission_rate", 0.03),
            split_rate=data.get("split_rate", 0.7),
            campaign=data.get("campaign", "")
        )

        return jsonify({
            "message": "Conversion recorded",
            "conversion_id": conversion.id,
            "gross_commission": conversion.gross_commission,
            "net_commission": conversion.net_commission
        }), 201

    # ==================== Pipeline ====================

    @app.route("/api/pipeline", methods=["GET"])
    @require_api_key(scopes=["read", "pipeline"])
    @rate_limit()
    def pipeline_snapshot():
        """Get pipeline snapshot."""
        pipeline = get_pipeline()

        return jsonify({
            "stages": pipeline.get_pipeline_snapshot(),
            "value": pipeline.get_pipeline_value()
        })

    @app.route("/api/pipeline/<int:lead_id>", methods=["PUT"])
    @require_api_key(scopes=["write", "pipeline"])
    @rate_limit()
    def update_pipeline_stage(lead_id: int):
        """Update lead's pipeline stage."""
        data = request.get_json()

        if not data or "stage" not in data:
            return jsonify({"error": "stage field required"}), 400

        pipeline = get_pipeline()

        from ..analytics.pipeline import PipelineStage
        try:
            stage = PipelineStage(data["stage"])
        except ValueError:
            valid_stages = [s.value for s in PipelineStage]
            return jsonify({
                "error": f"Invalid stage. Must be one of: {valid_stages}"
            }), 400

        change = pipeline.move_lead(
            lead_id=str(lead_id),
            to_stage=stage,
            changed_by=data.get("changed_by", "api"),
            notes=data.get("notes", "")
        )

        return jsonify({
            "lead_id": lead_id,
            "previous_stage": change.from_stage.value if change.from_stage else None,
            "new_stage": change.to_stage.value,
            "changed_at": change.changed_at.isoformat()
        })

    # ==================== Routing ====================

    @app.route("/api/routing/agents", methods=["GET"])
    @require_api_key(scopes=["read", "routing"])
    @rate_limit()
    def list_agents():
        """List all agents."""
        router = get_router()

        agents = [
            {
                "id": a.id,
                "name": a.name,
                "email": a.email,
                "status": a.status.value,
                "current_lead_count": a.current_lead_count,
                "max_leads_per_day": a.max_leads_per_day,
                "specialties": a.specialties,
                "areas": a.areas
            }
            for a in router.agents.values()
        ]

        return jsonify({
            "agents": agents,
            "summary": router.get_routing_summary()
        })

    @app.route("/api/routing/route", methods=["POST"])
    @require_api_key(scopes=["write", "routing"])
    @rate_limit()
    def route_lead():
        """Route a lead to an agent."""
        data = request.get_json()

        if not data or "lead_id" not in data:
            return jsonify({"error": "lead_id required"}), 400

        router = get_router()

        # Get lead data for routing
        db = get_db()
        lead = db.get_lead(data["lead_id"])

        lead_data = {
            "id": data["lead_id"],
            "area": data.get("area"),
            "price_range": data.get("price_range"),
            "type": data.get("type", "buyer")
        }

        if lead:
            lead_data["area"] = lead.notes  # Would need proper area field

        assignment = router.route_lead(lead_data)

        if not assignment:
            return jsonify({
                "error": "No agents available",
                "message": "All agents are at capacity or unavailable"
            }), 503

        return jsonify({
            "assignment_id": assignment.id,
            "lead_id": assignment.lead_id,
            "agent_id": assignment.agent_id,
            "agent_name": assignment.agent_name,
            "routing_method": assignment.routing_method.value,
            "assigned_at": assignment.assigned_at.isoformat()
        })

    # ==================== Webhooks ====================

    @app.route("/api/webhooks/lead", methods=["POST"])
    def webhook_lead():
        """Receive lead from external webhook (forms, etc.)."""
        data = request.get_json() or request.form.to_dict()

        if not data:
            return jsonify({"error": "No data received"}), 400

        # Map common field names
        name = (
            data.get("name") or
            f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or
            data.get("full_name")
        )
        email = data.get("email") or data.get("email_address")
        phone = data.get("phone") or data.get("phone_number")

        if not name and not email:
            return jsonify({"error": "name or email required"}), 400

        db = get_db()
        scoring_engine = get_scoring_engine()

        # Create lead
        from ..storage.models import Lead
        lead = Lead(
            name=name or "Unknown",
            email=email,
            phone=phone,
            bio=data.get("message") or data.get("notes") or "",
            source=data.get("source", "webhook"),
            source_id=data.get("source_id")
        )

        # Score
        if lead.bio:
            result = scoring_engine.score(lead.bio)
            lead.score = result["score"]
            lead.tier = result["tier"]
            lead.score_breakdown = json.dumps(result)

        lead_id = db.add_lead(lead)

        return jsonify({
            "success": True,
            "lead_id": lead_id,
            "score": lead.score,
            "tier": lead.tier
        }), 201

    # ==================== API Keys ====================

    @app.route("/api/keys", methods=["GET"])
    @require_api_key(scopes=["admin"])
    @rate_limit()
    def list_api_keys():
        """List all API keys."""
        keys = get_key_manager().list_keys()
        return jsonify({"keys": keys})

    @app.route("/api/keys", methods=["POST"])
    @require_api_key(scopes=["admin"])
    @rate_limit()
    def create_api_key():
        """Create a new API key."""
        data = request.get_json()

        if not data or "name" not in data:
            return jsonify({"error": "name required"}), 400

        key_data = generate_api_key(
            name=data["name"],
            scopes=data.get("scopes", ["read"]),
            expires_days=data.get("expires_days")
        )

        return jsonify({
            "message": "API key created",
            "key": key_data["full_key"],
            "key_id": key_data["key_id"],
            "name": key_data["name"],
            "scopes": key_data["scopes"],
            "warning": "Store this key securely - it will not be shown again"
        }), 201

    @app.route("/api/keys/<key_id>", methods=["DELETE"])
    @require_api_key(scopes=["admin"])
    @rate_limit()
    def revoke_api_key(key_id: str):
        """Revoke an API key."""
        success = get_key_manager().revoke_key(key_id)

        if not success:
            return jsonify({"error": "Key not found"}), 404

        return jsonify({"message": "API key revoked"})

    # ==================== Error Handlers ====================

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "message": str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        return jsonify({"error": "Internal server error"}), 500

    return app


def run_api_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Run the API server."""
    app = create_app()
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_api_server(debug=True)
