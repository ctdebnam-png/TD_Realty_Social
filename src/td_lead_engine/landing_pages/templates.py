"""Pre-built landing page templates."""

from typing import Dict, List
from .page_builder import LandingPageBuilder, PageSection, SectionType
from .form_builder import FormBuilder
import uuid


class LandingPageTemplates:
    """Collection of pre-built landing page templates."""
    
    def __init__(self, page_builder: LandingPageBuilder = None, form_builder: FormBuilder = None):
        self.page_builder = page_builder or LandingPageBuilder()
        self.form_builder = form_builder or FormBuilder()
    
    def create_neighborhood_guide(self, neighborhood: str, data: Dict) -> str:
        """Create a neighborhood guide landing page."""
        page = self.page_builder.create_page(
            name=f"{neighborhood} Neighborhood Guide",
            slug=f"neighborhoods/{neighborhood.lower().replace(' ', '-')}",
            title=f"Living in {neighborhood} | Homes for Sale & Community Guide"
        )
        page.meta_description = f"Discover {neighborhood} - schools, amenities, home values, and available properties. Your complete guide to living in {neighborhood}."
        
        sections = [
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.HERO,
                content={
                    'headline': f"Discover {neighborhood}",
                    'subheadline': data.get('tagline', f"Your guide to living in {neighborhood}"),
                    'cta_text': "View Homes for Sale",
                    'cta_link': "#available-homes",
                    'background_image': data.get('hero_image', '')
                },
                styles={'text_color': 'text-white'},
                order=1
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.TEXT,
                content={
                    'headline': f"About {neighborhood}",
                    'body': data.get('description', '')
                },
                order=2
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.STATS,
                content={
                    'headline': 'Neighborhood at a Glance',
                    'stats': [
                        {'value': data.get('median_price', '$0'), 'label': 'Median Home Price'},
                        {'value': data.get('school_rating', 'N/A'), 'label': 'School Rating'},
                        {'value': data.get('walk_score', 'N/A'), 'label': 'Walk Score'},
                        {'value': data.get('population', 'N/A'), 'label': 'Population'}
                    ]
                },
                styles={'background': 'bg-primary', 'text_color': 'text-white'},
                order=3
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FEATURES,
                content={
                    'headline': "What Makes It Great",
                    'features': data.get('highlights', [
                        {'icon': 'bi-tree', 'title': 'Parks & Recreation', 'description': 'Beautiful parks and outdoor spaces'},
                        {'icon': 'bi-mortarboard', 'title': 'Top Schools', 'description': 'Award-winning school district'},
                        {'icon': 'bi-shop', 'title': 'Shopping & Dining', 'description': 'Convenient access to restaurants and shops'}
                    ])
                },
                styles={'background': 'bg-light'},
                order=4
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.GALLERY,
                content={
                    'headline': f"Life in {neighborhood}",
                    'images': data.get('gallery_images', [])
                },
                order=5
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FORM,
                content={
                    'headline': f"Get {neighborhood} Listings Alerts",
                    'form_html': self._create_alerts_form()
                },
                order=6
            )
        ]
        
        for section in sections:
            self.page_builder.add_section(page.id, section)
        
        return page.id
    
    def create_coming_soon_listing(self, property_data: Dict) -> str:
        """Create a coming soon listing page."""
        address = property_data.get('address', 'Coming Soon')
        page = self.page_builder.create_page(
            name=f"Coming Soon - {address}",
            slug=f"coming-soon/{str(uuid.uuid4())[:8]}",
            title=f"Coming Soon: {address} | Pre-Market Listing"
        )
        
        sections = [
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.HERO,
                content={
                    'headline': "Coming Soon",
                    'subheadline': f"{property_data.get('beds', 0)} Bed | {property_data.get('baths', 0)} Bath | {property_data.get('sqft', 0):,} Sq Ft",
                    'cta_text': "Get Notified When Listed",
                    'cta_link': "#notify-form",
                    'background_image': property_data.get('main_image', '')
                },
                styles={'text_color': 'text-white'},
                order=1
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.TEXT,
                content={
                    'headline': "About This Home",
                    'body': property_data.get('description', 'Details coming soon...')
                },
                order=2
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FEATURES,
                content={
                    'headline': "Home Highlights",
                    'features': [
                        {'icon': 'bi-house-door', 'title': property_data.get('property_type', 'Single Family'), 'description': 'Property Type'},
                        {'icon': 'bi-calendar', 'title': property_data.get('year_built', 'N/A'), 'description': 'Year Built'},
                        {'icon': 'bi-rulers', 'title': f"{property_data.get('lot_size', 'N/A')}", 'description': 'Lot Size'}
                    ]
                },
                order=3
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FORM,
                content={
                    'headline': "Be the First to Know",
                    'form_html': self._create_coming_soon_form(property_data.get('id', ''))
                },
                styles={'background': 'bg-primary', 'text_color': 'text-white'},
                order=4
            )
        ]
        
        for section in sections:
            self.page_builder.add_section(page.id, section)
        
        return page.id
    
    def create_agent_landing_page(self, agent_data: Dict) -> str:
        """Create an agent-focused landing page."""
        name = agent_data.get('name', 'Agent')
        page = self.page_builder.create_page(
            name=f"Agent - {name}",
            slug=f"agents/{name.lower().replace(' ', '-')}",
            title=f"{name} - Real Estate Agent | Central Ohio"
        )
        page.meta_description = f"Work with {name}, your trusted Central Ohio real estate agent. {agent_data.get('specialties', 'Buyer and seller representation.')}"
        
        sections = [
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.AGENT_BIO,
                content={
                    'name': name,
                    'title': agent_data.get('title', 'Real Estate Agent'),
                    'photo': agent_data.get('photo', ''),
                    'bio': agent_data.get('bio', ''),
                    'phone': agent_data.get('phone', ''),
                    'email': agent_data.get('email', '')
                },
                order=1
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.STATS,
                content={
                    'headline': 'Track Record',
                    'stats': [
                        {'value': agent_data.get('years_experience', '10+'), 'label': 'Years Experience'},
                        {'value': agent_data.get('homes_sold', '100+'), 'label': 'Homes Sold'},
                        {'value': agent_data.get('avg_sale_price', '$350K'), 'label': 'Avg Sale Price'},
                        {'value': agent_data.get('client_rating', '5.0'), 'label': 'Client Rating'}
                    ]
                },
                styles={'background': 'bg-light'},
                order=2
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.TESTIMONIALS,
                content={
                    'headline': 'Client Reviews',
                    'testimonials': agent_data.get('testimonials', [])
                },
                order=3
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FORM,
                content={
                    'headline': f"Work With {name.split()[0]}",
                    'form_html': self._create_contact_agent_form(agent_data.get('id', ''))
                },
                order=4
            )
        ]
        
        for section in sections:
            self.page_builder.add_section(page.id, section)
        
        return page.id
    
    def create_open_house_page(self, event_data: Dict) -> str:
        """Create an open house event page."""
        address = event_data.get('address', '')
        date = event_data.get('date', '')
        
        page = self.page_builder.create_page(
            name=f"Open House - {address}",
            slug=f"open-house/{str(uuid.uuid4())[:8]}",
            title=f"Open House: {address} | {date}"
        )
        
        sections = [
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.HERO,
                content={
                    'headline': "Open House",
                    'subheadline': f"{date} | {event_data.get('time', '')}",
                    'cta_text': "Register Now",
                    'cta_link': "#register",
                    'background_image': event_data.get('main_image', '')
                },
                styles={'text_color': 'text-white'},
                order=1
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.PROPERTY_SHOWCASE,
                content={
                    'address': address,
                    'price': event_data.get('price', ''),
                    'beds': event_data.get('beds', 0),
                    'baths': event_data.get('baths', 0),
                    'sqft': event_data.get('sqft', 0),
                    'description': event_data.get('description', ''),
                    'images': event_data.get('images', [])
                },
                order=2
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FORM,
                content={
                    'headline': "Register for Open House",
                    'form_html': self._create_open_house_form(event_data.get('property_id', ''))
                },
                styles={'background': 'bg-light'},
                order=3
            )
        ]
        
        for section in sections:
            self.page_builder.add_section(page.id, section)
        
        return page.id
    
    def create_investor_landing_page(self) -> str:
        """Create an investor-focused landing page."""
        page = self.page_builder.create_page(
            name="Investor Resources",
            slug="investors",
            title="Real Estate Investing in Central Ohio | Investment Properties"
        )
        page.meta_description = "Find investment properties in Central Ohio. Access cap rates, cash flow analysis, and expert investor guidance."
        
        sections = [
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.HERO,
                content={
                    'headline': "Build Wealth Through Real Estate",
                    'subheadline': "Access exclusive investment opportunities in Central Ohio's growing market.",
                    'cta_text': "View Investment Properties",
                    'cta_link': "#investor-form"
                },
                styles={'background': 'bg-dark', 'text_color': 'text-white'},
                order=1
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.STATS,
                content={
                    'headline': 'Why Invest in Central Ohio?',
                    'stats': [
                        {'value': '7.2%', 'label': 'Avg Cap Rate'},
                        {'value': '$1,450', 'label': 'Avg Rent'},
                        {'value': '5.2%', 'label': 'Annual Appreciation'},
                        {'value': '2.1%', 'label': 'Vacancy Rate'}
                    ]
                },
                styles={'background': 'bg-primary', 'text_color': 'text-white'},
                order=2
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FEATURES,
                content={
                    'headline': "Investor Services",
                    'features': [
                        {'icon': 'bi-calculator', 'title': 'Deal Analysis', 'description': 'Full cash flow and ROI analysis on every property'},
                        {'icon': 'bi-search', 'title': 'Off-Market Deals', 'description': 'Access to pocket listings and distressed properties'},
                        {'icon': 'bi-people', 'title': 'Property Management', 'description': 'Connections to trusted property managers'},
                        {'icon': 'bi-bank', 'title': 'Financing Contacts', 'description': 'Investor-friendly lenders and hard money options'},
                        {'icon': 'bi-tools', 'title': 'Contractor Network', 'description': 'Reliable contractors for rehab projects'},
                        {'icon': 'bi-graph-up', 'title': 'Market Reports', 'description': 'Monthly market analysis and investment trends'}
                    ]
                },
                styles={'background': 'bg-light'},
                order=3
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.CALCULATOR,
                content={
                    'headline': 'Analyze Your Investment',
                    'calculator_type': 'investment'
                },
                order=4
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FORM,
                content={
                    'headline': "Get Investment Opportunities",
                    'form_html': self._create_investor_form()
                },
                order=5
            )
        ]
        
        for section in sections:
            self.page_builder.add_section(page.id, section)
        
        return page.id
    
    def create_relocation_page(self) -> str:
        """Create a relocation assistance landing page."""
        page = self.page_builder.create_page(
            name="Relocation Guide",
            slug="relocating-to-columbus",
            title="Relocating to Columbus, Ohio | Moving Guide & Home Search"
        )
        page.meta_description = "Moving to Columbus? Get your complete relocation guide with neighborhood info, schools, employers, and personalized home search assistance."
        
        sections = [
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.HERO,
                content={
                    'headline': "Moving to Columbus?",
                    'subheadline': "Your personal guide to finding the perfect home in Central Ohio.",
                    'cta_text': "Start Your Search",
                    'cta_link': "#relocation-form"
                },
                order=1
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.TEXT,
                content={
                    'headline': "Welcome to Columbus",
                    'body': """<p>Columbus, Ohio is one of the fastest-growing cities in the Midwest, offering a perfect 
                    blend of big-city amenities and small-town charm. With a diverse economy, excellent schools, and 
                    affordable cost of living, it's no wonder so many people are choosing to call Columbus home.</p>
                    <p>Whether you're relocating for work, family, or simply seeking a change of scenery, we're here 
                    to make your transition as smooth as possible.</p>"""
                },
                order=2
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FEATURES,
                content={
                    'headline': "What We Offer Relocating Families",
                    'features': [
                        {'icon': 'bi-compass', 'title': 'Neighborhood Tours', 'description': 'Personalized tours of areas matching your lifestyle'},
                        {'icon': 'bi-mortarboard', 'title': 'School Information', 'description': 'Detailed reports on school districts and ratings'},
                        {'icon': 'bi-briefcase', 'title': 'Employer Proximity', 'description': 'Commute analysis to major employers'},
                        {'icon': 'bi-house-door', 'title': 'Home Search', 'description': 'Curated listings based on your criteria'},
                        {'icon': 'bi-calendar-check', 'title': 'Moving Coordination', 'description': 'Timeline management and vendor referrals'},
                        {'icon': 'bi-people', 'title': 'Community Connections', 'description': 'Introductions to local groups and activities'}
                    ]
                },
                styles={'background': 'bg-light'},
                order=3
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.VIDEO,
                content={
                    'headline': 'Discover Columbus',
                    'video_url': 'https://www.youtube.com/watch?v=XXXXX'
                },
                order=4
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FORM,
                content={
                    'headline': "Get Your Free Relocation Guide",
                    'form_html': self._create_relocation_form()
                },
                order=5
            )
        ]
        
        for section in sections:
            self.page_builder.add_section(page.id, section)
        
        return page.id
    
    def _create_alerts_form(self) -> str:
        """Create listing alerts form HTML."""
        return '''
        <form class="lead-capture-form" action="/api/leads/capture" method="POST">
            <input type="hidden" name="lead_source" value="listing_alerts">
            <div class="mb-3">
                <input type="text" class="form-control" name="name" placeholder="Your Name" required>
            </div>
            <div class="mb-3">
                <input type="email" class="form-control" name="email" placeholder="Email Address" required>
            </div>
            <div class="mb-3">
                <select class="form-select" name="price_range">
                    <option value="">Price Range</option>
                    <option value="0-300000">Under $300,000</option>
                    <option value="300000-500000">$300,000 - $500,000</option>
                    <option value="500000+">$500,000+</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary w-100">Get Listing Alerts</button>
        </form>
        '''
    
    def _create_coming_soon_form(self, property_id: str) -> str:
        """Create coming soon notification form."""
        return f'''
        <form class="lead-capture-form" action="/api/leads/capture" method="POST">
            <input type="hidden" name="lead_source" value="coming_soon">
            <input type="hidden" name="property_id" value="{property_id}">
            <div class="mb-3">
                <input type="text" class="form-control" name="name" placeholder="Your Name" required>
            </div>
            <div class="mb-3">
                <input type="email" class="form-control" name="email" placeholder="Email Address" required>
            </div>
            <div class="mb-3">
                <input type="tel" class="form-control" name="phone" placeholder="Phone Number">
            </div>
            <button type="submit" class="btn btn-light w-100 text-primary">Notify Me When Listed</button>
        </form>
        '''
    
    def _create_contact_agent_form(self, agent_id: str) -> str:
        """Create agent contact form."""
        return f'''
        <form class="lead-capture-form" action="/api/leads/capture" method="POST">
            <input type="hidden" name="lead_source" value="agent_contact">
            <input type="hidden" name="agent_id" value="{agent_id}">
            <div class="row">
                <div class="col-md-6 mb-3">
                    <input type="text" class="form-control" name="first_name" placeholder="First Name" required>
                </div>
                <div class="col-md-6 mb-3">
                    <input type="text" class="form-control" name="last_name" placeholder="Last Name" required>
                </div>
            </div>
            <div class="mb-3">
                <input type="email" class="form-control" name="email" placeholder="Email Address" required>
            </div>
            <div class="mb-3">
                <input type="tel" class="form-control" name="phone" placeholder="Phone Number">
            </div>
            <div class="mb-3">
                <select class="form-select" name="interest">
                    <option value="">How can I help?</option>
                    <option value="buying">Buying a home</option>
                    <option value="selling">Selling my home</option>
                    <option value="both">Both buying and selling</option>
                    <option value="question">I have a question</option>
                </select>
            </div>
            <div class="mb-3">
                <textarea class="form-control" name="message" rows="3" placeholder="Message (optional)"></textarea>
            </div>
            <button type="submit" class="btn btn-primary w-100">Contact Agent</button>
        </form>
        '''
    
    def _create_open_house_form(self, property_id: str) -> str:
        """Create open house registration form."""
        return f'''
        <form class="lead-capture-form" action="/api/leads/capture" method="POST">
            <input type="hidden" name="lead_source" value="open_house">
            <input type="hidden" name="property_id" value="{property_id}">
            <div class="row">
                <div class="col-md-6 mb-3">
                    <input type="text" class="form-control" name="first_name" placeholder="First Name" required>
                </div>
                <div class="col-md-6 mb-3">
                    <input type="text" class="form-control" name="last_name" placeholder="Last Name" required>
                </div>
            </div>
            <div class="mb-3">
                <input type="email" class="form-control" name="email" placeholder="Email Address" required>
            </div>
            <div class="mb-3">
                <input type="tel" class="form-control" name="phone" placeholder="Phone Number" required>
            </div>
            <div class="mb-3">
                <select class="form-select" name="working_with_agent">
                    <option value="">Working with an agent?</option>
                    <option value="no">No</option>
                    <option value="yes">Yes</option>
                </select>
            </div>
            <div class="mb-3">
                <select class="form-select" name="preapproved">
                    <option value="">Pre-approved for mortgage?</option>
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                    <option value="cash">Cash buyer</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary w-100">Register for Open House</button>
        </form>
        '''
    
    def _create_investor_form(self) -> str:
        """Create investor inquiry form."""
        return '''
        <form class="lead-capture-form" action="/api/leads/capture" method="POST">
            <input type="hidden" name="lead_source" value="investor">
            <div class="row">
                <div class="col-md-6 mb-3">
                    <input type="text" class="form-control" name="first_name" placeholder="First Name" required>
                </div>
                <div class="col-md-6 mb-3">
                    <input type="text" class="form-control" name="last_name" placeholder="Last Name" required>
                </div>
            </div>
            <div class="mb-3">
                <input type="email" class="form-control" name="email" placeholder="Email Address" required>
            </div>
            <div class="mb-3">
                <input type="tel" class="form-control" name="phone" placeholder="Phone Number">
            </div>
            <div class="mb-3">
                <select class="form-select" name="investment_type">
                    <option value="">Investment Type</option>
                    <option value="rental">Buy & Hold Rental</option>
                    <option value="flip">Fix & Flip</option>
                    <option value="wholesale">Wholesale</option>
                    <option value="multi">Multi-Family</option>
                    <option value="commercial">Commercial</option>
                </select>
            </div>
            <div class="mb-3">
                <select class="form-select" name="budget">
                    <option value="">Investment Budget</option>
                    <option value="0-100000">Under $100,000</option>
                    <option value="100000-250000">$100,000 - $250,000</option>
                    <option value="250000-500000">$250,000 - $500,000</option>
                    <option value="500000+">$500,000+</option>
                </select>
            </div>
            <div class="mb-3">
                <select class="form-select" name="experience">
                    <option value="">Investment Experience</option>
                    <option value="first">First-time investor</option>
                    <option value="1-5">Own 1-5 properties</option>
                    <option value="5+">Own 5+ properties</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary w-100">Get Investment Opportunities</button>
        </form>
        '''
    
    def _create_relocation_form(self) -> str:
        """Create relocation inquiry form."""
        return '''
        <form class="lead-capture-form" action="/api/leads/capture" method="POST">
            <input type="hidden" name="lead_source" value="relocation">
            <div class="row">
                <div class="col-md-6 mb-3">
                    <input type="text" class="form-control" name="first_name" placeholder="First Name" required>
                </div>
                <div class="col-md-6 mb-3">
                    <input type="text" class="form-control" name="last_name" placeholder="Last Name" required>
                </div>
            </div>
            <div class="mb-3">
                <input type="email" class="form-control" name="email" placeholder="Email Address" required>
            </div>
            <div class="mb-3">
                <input type="tel" class="form-control" name="phone" placeholder="Phone Number">
            </div>
            <div class="mb-3">
                <input type="text" class="form-control" name="relocating_from" placeholder="Relocating From (City, State)">
            </div>
            <div class="mb-3">
                <select class="form-select" name="move_date">
                    <option value="">When are you moving?</option>
                    <option value="0-1month">Within 1 month</option>
                    <option value="1-3months">1-3 months</option>
                    <option value="3-6months">3-6 months</option>
                    <option value="6+months">6+ months</option>
                </select>
            </div>
            <div class="mb-3">
                <select class="form-select" name="reason">
                    <option value="">Reason for relocating</option>
                    <option value="job">New job/Transfer</option>
                    <option value="family">Family reasons</option>
                    <option value="retirement">Retirement</option>
                    <option value="other">Other</option>
                </select>
            </div>
            <div class="mb-3">
                <input type="text" class="form-control" name="employer" placeholder="Employer (if applicable)">
            </div>
            <button type="submit" class="btn btn-primary w-100">Get My Free Relocation Guide</button>
        </form>
        '''
