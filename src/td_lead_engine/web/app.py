"""Flask web application for TD Lead Engine dashboard."""

import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps

# Import engine components
from ..storage import LeadStorage
from ..scorer import LeadScorer
from ..analytics.pipeline import PipelineAnalytics, PipelineStage
from ..transactions.tracker import TransactionTracker
from ..scheduling.showing_scheduler import ShowingScheduler
from ..reviews.collector import ReviewCollector

# Import blueprints
from .client_portal import client_bp


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # Configuration
    app.secret_key = os.environ.get('SECRET_KEY', 'td-realty-dev-key-change-in-production')
    app.config['SESSION_TYPE'] = 'filesystem'

    if config:
        app.config.update(config)

    # Initialize components
    storage = LeadStorage()
    scorer = LeadScorer()
    pipeline = PipelineAnalytics()
    transactions = TransactionTracker()
    showings = ShowingScheduler()
    reviews = ReviewCollector()

    # Register blueprints
    app.register_blueprint(client_bp)

    # Auth decorator
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    # ==================== AUTH ROUTES ====================

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            # Simple auth (in production, use proper authentication)
            if email and password:
                session['user_id'] = email
                session['user_name'] = email.split('@')[0].title()
                flash('Welcome back!', 'success')
                return redirect(url_for('dashboard'))

            flash('Invalid credentials', 'error')

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('You have been logged out', 'info')
        return redirect(url_for('login'))

    # ==================== DASHBOARD ====================

    @app.route('/')
    @login_required
    def dashboard():
        # Get summary stats
        all_leads = storage.get_all_leads()
        pipeline_summary = pipeline.get_pipeline_summary()

        # Recent leads
        recent_leads = sorted(all_leads, key=lambda x: x.get('created_at', ''), reverse=True)[:10]

        # Upcoming showings
        upcoming = showings.get_upcoming_showings(days=7)[:5]

        # Today's tasks
        today_showings = showings.get_todays_showings()

        # Stats
        stats = {
            'total_leads': len(all_leads),
            'hot_leads': len([l for l in all_leads if l.get('score', 0) >= 80]),
            'new_this_week': len([l for l in all_leads
                                  if l.get('created_at', '') >= (datetime.now() - timedelta(days=7)).isoformat()]),
            'active_transactions': len([t for t in transactions.transactions.values()
                                       if t.status.value not in ['closed', 'cancelled']]),
        }

        return render_template('dashboard.html',
                             stats=stats,
                             recent_leads=recent_leads,
                             upcoming_showings=upcoming,
                             today_showings=today_showings,
                             pipeline=pipeline_summary)

    # ==================== LEADS ====================

    @app.route('/leads')
    @login_required
    def leads():
        all_leads = storage.get_all_leads()

        # Filters
        stage = request.args.get('stage')
        source = request.args.get('source')
        search = request.args.get('search', '').lower()

        if stage:
            all_leads = [l for l in all_leads if l.get('stage') == stage]
        if source:
            all_leads = [l for l in all_leads if l.get('source') == source]
        if search:
            all_leads = [l for l in all_leads
                        if search in l.get('name', '').lower()
                        or search in l.get('email', '').lower()
                        or search in l.get('phone', '').lower()]

        # Sort by score
        all_leads = sorted(all_leads, key=lambda x: x.get('score', 0), reverse=True)

        # Get unique sources and stages for filters
        sources = list(set(l.get('source', 'unknown') for l in storage.get_all_leads()))
        stages = [s.value for s in PipelineStage]

        return render_template('leads.html',
                             leads=all_leads,
                             sources=sources,
                             stages=stages,
                             current_stage=stage,
                             current_source=source,
                             search=search)

    @app.route('/leads/<lead_id>')
    @login_required
    def lead_detail(lead_id):
        lead = storage.get_lead(lead_id)
        if not lead:
            flash('Lead not found', 'error')
            return redirect(url_for('leads'))

        # Get lead history/activities
        activities = []  # Would come from activity tracking

        return render_template('lead_detail.html', lead=lead, activities=activities)

    @app.route('/leads/<lead_id>/update', methods=['POST'])
    @login_required
    def update_lead(lead_id):
        lead = storage.get_lead(lead_id)
        if not lead:
            return jsonify({'error': 'Lead not found'}), 404

        # Update fields
        if 'stage' in request.form:
            pipeline.move_lead(lead_id, PipelineStage(request.form['stage']))

        if 'notes' in request.form:
            lead['notes'] = request.form['notes']
            storage.update_lead(lead_id, lead)

        flash('Lead updated', 'success')
        return redirect(url_for('lead_detail', lead_id=lead_id))

    @app.route('/leads/add', methods=['GET', 'POST'])
    @login_required
    def add_lead():
        if request.method == 'POST':
            lead_data = {
                'name': request.form.get('name'),
                'email': request.form.get('email'),
                'phone': request.form.get('phone'),
                'source': request.form.get('source', 'manual'),
                'lead_type': request.form.get('lead_type', 'buyer'),
                'notes': request.form.get('notes', ''),
                'created_at': datetime.now().isoformat()
            }

            # Score the lead
            score_result = scorer.score_lead(lead_data)
            lead_data['score'] = score_result['score']
            lead_data['score_breakdown'] = score_result

            # Store
            lead_id = storage.store_lead(lead_data)

            flash(f'Lead added with score {lead_data["score"]}', 'success')
            return redirect(url_for('lead_detail', lead_id=lead_id))

        return render_template('add_lead.html')

    # ==================== PIPELINE ====================

    @app.route('/pipeline')
    @login_required
    def pipeline_view():
        summary = pipeline.get_pipeline_summary()
        all_leads = storage.get_all_leads()

        # Group leads by stage
        leads_by_stage = {stage.value: [] for stage in PipelineStage}
        for lead in all_leads:
            stage = lead.get('stage', 'new')
            if stage in leads_by_stage:
                leads_by_stage[stage].append(lead)

        return render_template('pipeline.html',
                             summary=summary,
                             leads_by_stage=leads_by_stage,
                             stages=PipelineStage)

    @app.route('/pipeline/move', methods=['POST'])
    @login_required
    def move_lead_stage():
        lead_id = request.form.get('lead_id')
        new_stage = request.form.get('stage')

        if lead_id and new_stage:
            pipeline.move_lead(lead_id, PipelineStage(new_stage))
            return jsonify({'success': True})

        return jsonify({'error': 'Missing parameters'}), 400

    # ==================== CALENDAR/SHOWINGS ====================

    @app.route('/calendar')
    @login_required
    def calendar():
        # Get showings for the month
        upcoming = showings.get_upcoming_showings(days=30)

        # Format for calendar
        events = []
        for showing in upcoming:
            if showing.confirmed_date:
                events.append({
                    'id': showing.id,
                    'title': f'{showing.property_address} - {showing.buyer_name}',
                    'start': showing.confirmed_date.isoformat() if hasattr(showing.confirmed_date, 'isoformat') else str(showing.confirmed_date),
                    'type': showing.showing_type.value
                })

        return render_template('calendar.html', events=events, upcoming=upcoming[:10])

    @app.route('/showings')
    @login_required
    def showings_list():
        pending = showings.get_pending_approvals()
        today = showings.get_todays_showings()
        upcoming = showings.get_upcoming_showings(days=14)

        return render_template('showings.html',
                             pending=pending,
                             today=today,
                             upcoming=upcoming)

    @app.route('/showings/<showing_id>/confirm', methods=['POST'])
    @login_required
    def confirm_showing(showing_id):
        confirmed_time = request.form.get('confirmed_time')
        lockbox_code = request.form.get('lockbox_code', '')

        if confirmed_time:
            showings.confirm_showing(
                showing_id,
                datetime.fromisoformat(confirmed_time),
                lockbox_code
            )
            flash('Showing confirmed', 'success')

        return redirect(url_for('showings_list'))

    # ==================== TRANSACTIONS ====================

    @app.route('/transactions')
    @login_required
    def transactions_list():
        all_txns = list(transactions.transactions.values())

        # Filter by status
        status = request.args.get('status')
        if status:
            all_txns = [t for t in all_txns if t.status.value == status]

        # Sort by date
        all_txns = sorted(all_txns, key=lambda x: x.created_at, reverse=True)

        summary = transactions.get_ytd_summary()

        return render_template('transactions.html',
                             transactions=all_txns,
                             summary=summary)

    @app.route('/transactions/<txn_id>')
    @login_required
    def transaction_detail(txn_id):
        txn = transactions.get_transaction(txn_id)
        if not txn:
            flash('Transaction not found', 'error')
            return redirect(url_for('transactions_list'))

        return render_template('transaction_detail.html', transaction=txn)

    # ==================== REVIEWS ====================

    @app.route('/reviews')
    @login_required
    def reviews_list():
        stats = reviews.get_review_statistics()
        published = reviews.get_published_reviews()
        pending = reviews.get_reviews_for_approval()
        pending_requests = reviews.get_pending_requests()

        return render_template('reviews.html',
                             stats=stats,
                             published=published,
                             pending=pending,
                             pending_requests=pending_requests)

    @app.route('/reviews/<review_id>/approve', methods=['POST'])
    @login_required
    def approve_review(review_id):
        reviews.approve_review(review_id)
        flash('Review approved', 'success')
        return redirect(url_for('reviews_list'))

    @app.route('/reviews/request', methods=['POST'])
    @login_required
    def request_review():
        client_name = request.form.get('client_name')
        client_email = request.form.get('client_email')
        transaction_type = request.form.get('transaction_type', 'buyer')

        if client_name and client_email:
            reviews.request_review(
                client_id=client_email,
                client_name=client_name,
                client_email=client_email,
                transaction_type=transaction_type
            )
            flash(f'Review request sent to {client_name}', 'success')

        return redirect(url_for('reviews_list'))

    # ==================== API ENDPOINTS ====================

    @app.route('/api/stats')
    @login_required
    def api_stats():
        all_leads = storage.get_all_leads()
        return jsonify({
            'total_leads': len(all_leads),
            'hot_leads': len([l for l in all_leads if l.get('score', 0) >= 80]),
            'pipeline': pipeline.get_pipeline_summary()
        })

    @app.route('/api/leads/search')
    @login_required
    def api_search_leads():
        query = request.args.get('q', '').lower()
        all_leads = storage.get_all_leads()

        results = [l for l in all_leads
                   if query in l.get('name', '').lower()
                   or query in l.get('email', '').lower()]

        return jsonify(results[:20])

    # ==================== ERROR HANDLERS ====================

    @app.errorhandler(404)
    def not_found(e):
        return render_template('error.html', error='Page not found', code=404), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', error='Server error', code=500), 500

    return app


# Run directly
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
