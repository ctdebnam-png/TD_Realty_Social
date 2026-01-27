"""Client-facing portal for buyers and sellers."""

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps

from ..portal import ClientPortal, BuyerPortal, SellerPortal

# Create blueprint
client_bp = Blueprint('client', __name__, url_prefix='/portal')

# Initialize portals
client_portal = ClientPortal()
buyer_portal = BuyerPortal()
seller_portal = SellerPortal()


def client_login_required(f):
    """Require client login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'client_id' not in session:
            return redirect(url_for('client.login'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== AUTH ====================

@client_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Client login page."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        portal_session = client_portal.authenticate(email, password)

        if portal_session:
            session['client_id'] = portal_session.client_id
            session['client_email'] = email

            # Get account info
            account = client_portal.get_account(portal_session.client_id)
            if account:
                session['client_name'] = account.name
                session['client_type'] = account.client_type

            flash('Welcome back!', 'success')
            return redirect(url_for('client.dashboard'))

        flash('Invalid email or password', 'error')

    return render_template('client/login.html')


@client_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Client registration."""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        client_type = request.form.get('client_type', 'buyer')

        # Check if exists
        existing = client_portal.get_account_by_email(email)
        if existing:
            flash('An account with this email already exists', 'error')
            return redirect(url_for('client.register'))

        # Create account
        account = client_portal.create_account(
            client_id=email,  # Use email as ID
            email=email,
            name=name,
            phone=phone,
            password=password,
            client_type=client_type
        )

        if account:
            session['client_id'] = account.client_id
            session['client_email'] = email
            session['client_name'] = name
            session['client_type'] = client_type

            flash('Account created! Welcome to TD Realty.', 'success')
            return redirect(url_for('client.dashboard'))

        flash('Error creating account', 'error')

    return render_template('client/register.html')


@client_bp.route('/logout')
def logout():
    """Client logout."""
    session.pop('client_id', None)
    session.pop('client_email', None)
    session.pop('client_name', None)
    session.pop('client_type', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('client.login'))


# ==================== DASHBOARD ====================

@client_bp.route('/')
@client_bp.route('/dashboard')
@client_login_required
def dashboard():
    """Client dashboard."""
    client_id = session['client_id']
    client_type = session.get('client_type', 'buyer')

    if client_type == 'buyer':
        summary = buyer_portal.get_buyer_summary(client_id)
        return render_template('client/buyer_dashboard.html', summary=summary)
    else:
        summary = seller_portal.get_seller_summary(client_id)
        return render_template('client/seller_dashboard.html', summary=summary)


# ==================== BUYER FEATURES ====================

@client_bp.route('/saved-searches')
@client_login_required
def saved_searches():
    """View saved searches."""
    client_id = session['client_id']
    searches = buyer_portal.get_saved_searches(client_id)
    return render_template('client/saved_searches.html', searches=searches)


@client_bp.route('/saved-searches/new', methods=['GET', 'POST'])
@client_login_required
def new_saved_search():
    """Create new saved search."""
    if request.method == 'POST':
        client_id = session['client_id']

        search = buyer_portal.create_saved_search(
            client_id=client_id,
            name=request.form.get('name'),
            locations=request.form.get('locations', '').split(','),
            min_price=int(request.form.get('min_price', 0)),
            max_price=int(request.form.get('max_price', 10000000)),
            min_beds=int(request.form.get('min_beds', 0)),
            min_baths=float(request.form.get('min_baths', 0)),
            property_types=request.form.getlist('property_types'),
            alert_frequency=request.form.get('alert_frequency', 'daily')
        )

        flash('Search saved! You\'ll receive alerts for matching properties.', 'success')
        return redirect(url_for('client.saved_searches'))

    return render_template('client/new_search.html')


@client_bp.route('/saved-properties')
@client_login_required
def saved_properties():
    """View saved/favorited properties."""
    client_id = session['client_id']
    properties = buyer_portal.get_saved_properties(client_id)
    favorites = buyer_portal.get_favorites(client_id)
    toured = buyer_portal.get_toured_properties(client_id)

    return render_template('client/saved_properties.html',
                         properties=properties,
                         favorites=favorites,
                         toured=toured)


@client_bp.route('/properties/<property_id>/save', methods=['POST'])
@client_login_required
def save_property(property_id):
    """Save a property."""
    client_id = session['client_id']

    buyer_portal.save_property(
        client_id=client_id,
        property_id=property_id,
        address=request.form.get('address', ''),
        city=request.form.get('city', ''),
        price=int(request.form.get('price', 0)),
        beds=int(request.form.get('beds', 0)),
        baths=float(request.form.get('baths', 0)),
        sqft=int(request.form.get('sqft', 0)),
        photo_url=request.form.get('photo_url', '')
    )

    flash('Property saved!', 'success')
    return redirect(request.referrer or url_for('client.saved_properties'))


@client_bp.route('/properties/<property_id>/unsave', methods=['POST'])
@client_login_required
def unsave_property(property_id):
    """Remove a saved property."""
    client_id = session['client_id']
    buyer_portal.unsave_property(client_id, property_id)
    flash('Property removed from saved list', 'info')
    return redirect(url_for('client.saved_properties'))


@client_bp.route('/properties/<property_id>/rate', methods=['POST'])
@client_login_required
def rate_property(property_id):
    """Rate a property."""
    client_id = session['client_id']
    rating = int(request.form.get('rating', 0))
    buyer_portal.rate_property(client_id, property_id, rating)
    return jsonify({'success': True, 'rating': rating})


@client_bp.route('/properties/<property_id>/request-showing', methods=['POST'])
@client_login_required
def request_showing(property_id):
    """Request a showing for a property."""
    client_id = session['client_id']
    client_name = session.get('client_name', '')

    # Would integrate with showing scheduler
    flash('Showing request sent! Your agent will contact you shortly.', 'success')
    return redirect(url_for('client.saved_properties'))


# ==================== SELLER FEATURES ====================

@client_bp.route('/my-listings')
@client_login_required
def my_listings():
    """View seller's listings."""
    client_id = session['client_id']
    listings = seller_portal.get_seller_listings(client_id)
    return render_template('client/my_listings.html', listings=listings)


@client_bp.route('/listings/<listing_id>')
@client_login_required
def listing_detail(listing_id):
    """View listing details."""
    client_id = session['client_id']

    # Get listing
    listings = seller_portal.get_seller_listings(client_id)
    listing = next((l for l in listings if l.id == listing_id), None)

    if not listing:
        flash('Listing not found', 'error')
        return redirect(url_for('client.my_listings'))

    # Get related data
    showings = seller_portal.get_listing_showings(listing_id)
    upcoming_showings = seller_portal.get_upcoming_showings(listing_id)
    offers = seller_portal.get_listing_offers(listing_id)
    pending_offers = seller_portal.get_pending_offers(listing_id)
    feedback = seller_portal.get_showing_feedback_summary(listing_id)

    return render_template('client/listing_detail.html',
                         listing=listing,
                         showings=showings,
                         upcoming_showings=upcoming_showings,
                         offers=offers,
                         pending_offers=pending_offers,
                         feedback=feedback)


@client_bp.route('/listings/<listing_id>/showings')
@client_login_required
def listing_showings(listing_id):
    """View showings for a listing."""
    showings = seller_portal.get_listing_showings(listing_id)
    upcoming = seller_portal.get_upcoming_showings(listing_id)
    return render_template('client/listing_showings.html',
                         listing_id=listing_id,
                         showings=showings,
                         upcoming=upcoming)


@client_bp.route('/listings/<listing_id>/showings/<showing_id>/confirm', methods=['POST'])
@client_login_required
def confirm_listing_showing(listing_id, showing_id):
    """Confirm a showing request."""
    seller_portal.confirm_showing(listing_id, showing_id)
    flash('Showing confirmed!', 'success')
    return redirect(url_for('client.listing_showings', listing_id=listing_id))


@client_bp.route('/listings/<listing_id>/offers')
@client_login_required
def listing_offers(listing_id):
    """View offers on a listing."""
    offers = seller_portal.get_listing_offers(listing_id)
    comparison = seller_portal.get_offer_comparison(listing_id)
    return render_template('client/listing_offers.html',
                         listing_id=listing_id,
                         offers=offers,
                         comparison=comparison)


@client_bp.route('/listings/<listing_id>/offers/<offer_id>/respond', methods=['POST'])
@client_login_required
def respond_to_offer(listing_id, offer_id):
    """Respond to an offer."""
    response = request.form.get('response')  # accept, reject, counter
    counter_amount = int(request.form.get('counter_amount', 0))
    counter_terms = request.form.get('counter_terms', '')

    seller_portal.respond_to_offer(
        listing_id=listing_id,
        offer_id=offer_id,
        response=response,
        counter_amount=counter_amount,
        counter_terms=counter_terms
    )

    if response == 'accept':
        flash('Offer accepted! Your agent will be in touch with next steps.', 'success')
    elif response == 'counter':
        flash('Counter offer sent!', 'success')
    else:
        flash('Offer declined', 'info')

    return redirect(url_for('client.listing_offers', listing_id=listing_id))


# ==================== SHARED FEATURES ====================

@client_bp.route('/messages')
@client_login_required
def messages():
    """View messages."""
    # Would integrate with messaging system
    return render_template('client/messages.html', messages=[])


@client_bp.route('/documents')
@client_login_required
def documents():
    """View documents."""
    # Would integrate with document management
    return render_template('client/documents.html', documents=[])


@client_bp.route('/profile', methods=['GET', 'POST'])
@client_login_required
def profile():
    """View/edit profile."""
    client_id = session['client_id']
    account = client_portal.get_account(client_id)

    if request.method == 'POST':
        # Update profile
        if account:
            account.name = request.form.get('name', account.name)
            account.phone = request.form.get('phone', account.phone)
            client_portal._save_data()

            session['client_name'] = account.name
            flash('Profile updated!', 'success')

    return render_template('client/profile.html', account=account)
