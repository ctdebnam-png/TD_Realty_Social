"""Flask API server for the dashboard."""

import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from td_lead_engine.storage.database import LeadDatabase
from td_lead_engine.storage.models import LeadStatus
from td_lead_engine.core.scorer import LeadScorer

app = Flask(__name__)
CORS(app)

db = LeadDatabase()
scorer = LeadScorer()


@app.route('/api/leads', methods=['GET'])
def get_leads():
    """Get all leads with optional filters."""
    tier = request.args.get('tier')
    limit = request.args.get('limit', 100, type=int)

    leads = db.get_all_leads(tier=tier, limit=limit)

    result = []
    for lead in leads:
        signals = []
        if lead.score_breakdown:
            try:
                breakdown = json.loads(lead.score_breakdown)
                signals = [m['phrase'] for m in breakdown.get('matches', [])[:5]]
            except Exception:
                pass

        result.append({
            'id': lead.id,
            'name': lead.name,
            'email': lead.email,
            'phone': lead.phone,
            'username': lead.username,
            'score': lead.score,
            'tier': lead.tier,
            'status': lead.status.value,
            'source': lead.source,
            'signals': signals,
            'profile_url': lead.profile_url,
        })

    return jsonify({'leads': result})


@app.route('/api/leads/<int:lead_id>', methods=['GET'])
def get_lead(lead_id):
    """Get a single lead by ID."""
    lead = db.get_lead(lead_id)
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404

    signals = []
    category_scores = {}
    if lead.score_breakdown:
        try:
            breakdown = json.loads(lead.score_breakdown)
            signals = [
                {'phrase': m['phrase'], 'weight': m['weight'], 'category': m['category']}
                for m in breakdown.get('matches', [])
            ]
            category_scores = breakdown.get('category_scores', {})
        except Exception:
            pass

    return jsonify({
        'lead': {
            'id': lead.id,
            'name': lead.name,
            'email': lead.email,
            'phone': lead.phone,
            'username': lead.username,
            'profile_url': lead.profile_url,
            'bio': lead.bio,
            'notes': lead.notes,
            'score': lead.score,
            'tier': lead.tier,
            'status': lead.status.value,
            'source': lead.source,
            'signals': signals,
            'category_scores': category_scores,
            'created_at': lead.created_at.isoformat() if lead.created_at else None,
            'updated_at': lead.updated_at.isoformat() if lead.updated_at else None,
        }
    })


@app.route('/api/leads/<int:lead_id>/status', methods=['PUT'])
def update_status(lead_id):
    """Update lead status."""
    lead = db.get_lead(lead_id)
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404

    data = request.json
    if 'status' not in data:
        return jsonify({'error': 'Status required'}), 400

    try:
        lead.status = LeadStatus(data['status'])
        db.update_lead(lead)
        return jsonify({'success': True, 'status': lead.status.value})
    except ValueError:
        return jsonify({'error': 'Invalid status'}), 400


@app.route('/api/leads/<int:lead_id>/note', methods=['POST'])
def add_note(lead_id):
    """Add a note to a lead."""
    lead = db.get_lead(lead_id)
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404

    data = request.json
    if 'note' not in data:
        return jsonify({'error': 'Note required'}), 400

    current_notes = lead.notes or ""
    lead.notes = f"{current_notes}\n[Note] {data['note']}".strip()
    db.update_lead(lead)

    return jsonify({'success': True})


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get database statistics."""
    return jsonify(db.get_stats())


@app.route('/api/search', methods=['GET'])
def search():
    """Search leads."""
    query = request.args.get('q', '')
    if not query:
        return jsonify({'leads': []})

    leads = db.search_leads(query, limit=50)

    result = []
    for lead in leads:
        result.append({
            'id': lead.id,
            'name': lead.name,
            'email': lead.email,
            'phone': lead.phone,
            'score': lead.score,
            'tier': lead.tier,
            'source': lead.source,
        })

    return jsonify({'leads': result})


@app.route('/api/test-score', methods=['POST'])
def test_score():
    """Test scoring on text."""
    data = request.json
    text = data.get('text', '')

    result = scorer.score_text(text)

    return jsonify({
        'score': result.total_score,
        'tier': result.tier,
        'matches': [
            {'phrase': m.signal.phrase, 'weight': m.signal.weight, 'category': m.signal.category.value}
            for m in result.matches
        ],
        'category_scores': {k.value: v for k, v in result.category_scores.items()}
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
