"""Landing page builder for lead generation."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import json
import uuid


class SectionType(Enum):
    """Types of page sections."""
    HERO = "hero"
    FORM = "form"
    FEATURES = "features"
    TESTIMONIALS = "testimonials"
    CTA = "cta"
    GALLERY = "gallery"
    VIDEO = "video"
    TEXT = "text"
    STATS = "stats"
    FAQ = "faq"
    CONTACT_INFO = "contact_info"
    PROPERTY_SHOWCASE = "property_showcase"
    AGENT_BIO = "agent_bio"
    MARKET_STATS = "market_stats"
    CALCULATOR = "calculator"
    SOCIAL_PROOF = "social_proof"


@dataclass
class PageSection:
    """A section of a landing page."""
    id: str
    section_type: SectionType
    title: str = ""
    subtitle: str = ""
    content: Dict = field(default_factory=dict)
    styles: Dict = field(default_factory=dict)
    order: int = 0
    visible: bool = True
    
    def to_html(self) -> str:
        """Generate HTML for this section."""
        bg_class = self.styles.get('background', 'bg-white')
        text_class = self.styles.get('text_color', 'text-dark')
        padding = self.styles.get('padding', 'py-5')
        
        section_html = f'<section id="{self.id}" class="{bg_class} {text_class} {padding}">'
        section_html += '<div class="container">'
        
        if self.section_type == SectionType.HERO:
            section_html += self._render_hero()
        elif self.section_type == SectionType.FORM:
            section_html += self._render_form()
        elif self.section_type == SectionType.FEATURES:
            section_html += self._render_features()
        elif self.section_type == SectionType.TESTIMONIALS:
            section_html += self._render_testimonials()
        elif self.section_type == SectionType.CTA:
            section_html += self._render_cta()
        elif self.section_type == SectionType.GALLERY:
            section_html += self._render_gallery()
        elif self.section_type == SectionType.VIDEO:
            section_html += self._render_video()
        elif self.section_type == SectionType.TEXT:
            section_html += self._render_text()
        elif self.section_type == SectionType.STATS:
            section_html += self._render_stats()
        elif self.section_type == SectionType.FAQ:
            section_html += self._render_faq()
        elif self.section_type == SectionType.CONTACT_INFO:
            section_html += self._render_contact()
        elif self.section_type == SectionType.PROPERTY_SHOWCASE:
            section_html += self._render_property()
        elif self.section_type == SectionType.AGENT_BIO:
            section_html += self._render_agent_bio()
        elif self.section_type == SectionType.MARKET_STATS:
            section_html += self._render_market_stats()
        elif self.section_type == SectionType.CALCULATOR:
            section_html += self._render_calculator()
        elif self.section_type == SectionType.SOCIAL_PROOF:
            section_html += self._render_social_proof()
        
        section_html += '</div></section>'
        return section_html
    
    def _render_hero(self) -> str:
        """Render hero section."""
        bg_image = self.content.get('background_image', '')
        headline = self.content.get('headline', self.title)
        subheadline = self.content.get('subheadline', self.subtitle)
        cta_text = self.content.get('cta_text', 'Get Started')
        cta_link = self.content.get('cta_link', '#form')
        overlay = self.content.get('overlay', 'rgba(0,0,0,0.5)')
        
        style = f'background-image: linear-gradient({overlay}, {overlay}), url("{bg_image}"); background-size: cover; background-position: center;' if bg_image else ''
        
        return f'''
        <div class="row min-vh-75 align-items-center text-center py-5" style="{style}">
            <div class="col-lg-8 mx-auto">
                <h1 class="display-3 fw-bold mb-4">{headline}</h1>
                <p class="lead mb-4">{subheadline}</p>
                <a href="{cta_link}" class="btn btn-primary btn-lg px-5">{cta_text}</a>
            </div>
        </div>
        '''
    
    def _render_form(self) -> str:
        """Render form section."""
        form_html = self.content.get('form_html', '')
        headline = self.content.get('headline', self.title)
        
        return f'''
        <div class="row justify-content-center">
            <div class="col-lg-6">
                <div class="card shadow-lg border-0">
                    <div class="card-body p-4 p-lg-5">
                        <h2 class="text-center mb-4">{headline}</h2>
                        {form_html}
                    </div>
                </div>
            </div>
        </div>
        '''
    
    def _render_features(self) -> str:
        """Render features section."""
        headline = self.content.get('headline', self.title)
        features = self.content.get('features', [])
        
        features_html = '<div class="row g-4">'
        for feat in features:
            icon = feat.get('icon', 'bi-check-circle')
            title = feat.get('title', '')
            description = feat.get('description', '')
            features_html += f'''
            <div class="col-md-4">
                <div class="text-center p-4">
                    <i class="bi {icon} display-4 text-primary mb-3"></i>
                    <h4>{title}</h4>
                    <p class="text-muted">{description}</p>
                </div>
            </div>
            '''
        features_html += '</div>'
        
        return f'''
        <h2 class="text-center mb-5">{headline}</h2>
        {features_html}
        '''
    
    def _render_testimonials(self) -> str:
        """Render testimonials section."""
        headline = self.content.get('headline', 'What Our Clients Say')
        testimonials = self.content.get('testimonials', [])
        
        items_html = ''
        for i, test in enumerate(testimonials):
            active = 'active' if i == 0 else ''
            items_html += f'''
            <div class="carousel-item {active}">
                <div class="row justify-content-center">
                    <div class="col-lg-8 text-center">
                        <i class="bi bi-quote display-4 text-primary mb-3"></i>
                        <p class="lead fst-italic mb-4">"{test.get('quote', '')}"</p>
                        <div>
                            <strong>{test.get('name', '')}</strong>
                            <span class="text-muted"> - {test.get('location', '')}</span>
                        </div>
                    </div>
                </div>
            </div>
            '''
        
        return f'''
        <h2 class="text-center mb-5">{headline}</h2>
        <div id="testimonialCarousel" class="carousel slide" data-bs-ride="carousel">
            <div class="carousel-inner">
                {items_html}
            </div>
            <button class="carousel-control-prev" type="button" data-bs-target="#testimonialCarousel" data-bs-slide="prev">
                <span class="carousel-control-prev-icon"></span>
            </button>
            <button class="carousel-control-next" type="button" data-bs-target="#testimonialCarousel" data-bs-slide="next">
                <span class="carousel-control-next-icon"></span>
            </button>
        </div>
        '''
    
    def _render_cta(self) -> str:
        """Render CTA section."""
        headline = self.content.get('headline', self.title)
        description = self.content.get('description', '')
        button_text = self.content.get('button_text', 'Get Started')
        button_link = self.content.get('button_link', '#')
        
        return f'''
        <div class="row justify-content-center text-center">
            <div class="col-lg-8">
                <h2 class="mb-4">{headline}</h2>
                <p class="lead mb-4">{description}</p>
                <a href="{button_link}" class="btn btn-primary btn-lg px-5">{button_text}</a>
            </div>
        </div>
        '''
    
    def _render_gallery(self) -> str:
        """Render image gallery section."""
        headline = self.content.get('headline', self.title)
        images = self.content.get('images', [])
        
        images_html = '<div class="row g-3">'
        for img in images:
            images_html += f'''
            <div class="col-md-4">
                <img src="{img.get('url', '')}" alt="{img.get('alt', '')}" class="img-fluid rounded shadow-sm">
                {f'<p class="text-center mt-2">{img.get("caption", "")}</p>' if img.get('caption') else ''}
            </div>
            '''
        images_html += '</div>'
        
        return f'''
        <h2 class="text-center mb-5">{headline}</h2>
        {images_html}
        '''
    
    def _render_video(self) -> str:
        """Render video section."""
        headline = self.content.get('headline', self.title)
        video_url = self.content.get('video_url', '')
        
        # Handle YouTube URLs
        if 'youtube.com' in video_url or 'youtu.be' in video_url:
            video_id = video_url.split('/')[-1].split('?v=')[-1]
            embed = f'<iframe width="100%" height="450" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe>'
        else:
            embed = f'<video class="w-100" controls><source src="{video_url}" type="video/mp4"></video>'
        
        return f'''
        <h2 class="text-center mb-5">{headline}</h2>
        <div class="row justify-content-center">
            <div class="col-lg-10">
                <div class="ratio ratio-16x9">
                    {embed}
                </div>
            </div>
        </div>
        '''
    
    def _render_text(self) -> str:
        """Render text content section."""
        headline = self.content.get('headline', self.title)
        body = self.content.get('body', '')
        
        return f'''
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <h2 class="mb-4">{headline}</h2>
                <div class="prose">{body}</div>
            </div>
        </div>
        '''
    
    def _render_stats(self) -> str:
        """Render stats/numbers section."""
        headline = self.content.get('headline', self.title)
        stats = self.content.get('stats', [])
        
        stats_html = '<div class="row g-4 text-center">'
        for stat in stats:
            stats_html += f'''
            <div class="col-md-3">
                <div class="display-4 fw-bold text-primary">{stat.get('value', '')}</div>
                <p class="text-muted mb-0">{stat.get('label', '')}</p>
            </div>
            '''
        stats_html += '</div>'
        
        return f'''
        <h2 class="text-center mb-5">{headline}</h2>
        {stats_html}
        '''
    
    def _render_faq(self) -> str:
        """Render FAQ section."""
        headline = self.content.get('headline', 'Frequently Asked Questions')
        faqs = self.content.get('faqs', [])
        
        accordion_html = '<div class="accordion" id="faqAccordion">'
        for i, faq in enumerate(faqs):
            collapsed = '' if i == 0 else 'collapsed'
            show = 'show' if i == 0 else ''
            accordion_html += f'''
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button {collapsed}" type="button" data-bs-toggle="collapse" data-bs-target="#faq{i}">
                        {faq.get('question', '')}
                    </button>
                </h2>
                <div id="faq{i}" class="accordion-collapse collapse {show}" data-bs-parent="#faqAccordion">
                    <div class="accordion-body">{faq.get('answer', '')}</div>
                </div>
            </div>
            '''
        accordion_html += '</div>'
        
        return f'''
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <h2 class="text-center mb-5">{headline}</h2>
                {accordion_html}
            </div>
        </div>
        '''
    
    def _render_contact(self) -> str:
        """Render contact info section."""
        agent_name = self.content.get('agent_name', '')
        phone = self.content.get('phone', '')
        email = self.content.get('email', '')
        address = self.content.get('address', '')
        
        return f'''
        <div class="row justify-content-center text-center">
            <div class="col-lg-6">
                <h2 class="mb-4">{self.title or 'Contact Us'}</h2>
                <p class="lead">{agent_name}</p>
                <p><i class="bi bi-telephone me-2"></i><a href="tel:{phone}">{phone}</a></p>
                <p><i class="bi bi-envelope me-2"></i><a href="mailto:{email}">{email}</a></p>
                <p><i class="bi bi-geo-alt me-2"></i>{address}</p>
            </div>
        </div>
        '''
    
    def _render_property(self) -> str:
        """Render property showcase section."""
        address = self.content.get('address', '')
        price = self.content.get('price', '')
        beds = self.content.get('beds', 0)
        baths = self.content.get('baths', 0)
        sqft = self.content.get('sqft', 0)
        description = self.content.get('description', '')
        images = self.content.get('images', [])
        
        images_html = ''
        for i, img in enumerate(images[:5]):
            active = 'active' if i == 0 else ''
            images_html += f'<div class="carousel-item {active}"><img src="{img}" class="d-block w-100" alt="Property"></div>'
        
        return f'''
        <div class="row g-4">
            <div class="col-lg-7">
                <div id="propertyCarousel" class="carousel slide" data-bs-ride="carousel">
                    <div class="carousel-inner rounded shadow">{images_html}</div>
                    <button class="carousel-control-prev" type="button" data-bs-target="#propertyCarousel" data-bs-slide="prev">
                        <span class="carousel-control-prev-icon"></span>
                    </button>
                    <button class="carousel-control-next" type="button" data-bs-target="#propertyCarousel" data-bs-slide="next">
                        <span class="carousel-control-next-icon"></span>
                    </button>
                </div>
            </div>
            <div class="col-lg-5">
                <h2 class="mb-3">{address}</h2>
                <h3 class="text-primary mb-4">{price}</h3>
                <div class="d-flex gap-4 mb-4">
                    <div><strong>{beds}</strong> Beds</div>
                    <div><strong>{baths}</strong> Baths</div>
                    <div><strong>{sqft:,}</strong> Sq Ft</div>
                </div>
                <p>{description}</p>
            </div>
        </div>
        '''
    
    def _render_agent_bio(self) -> str:
        """Render agent bio section."""
        name = self.content.get('name', '')
        title = self.content.get('title', 'Real Estate Agent')
        photo = self.content.get('photo', '')
        bio = self.content.get('bio', '')
        phone = self.content.get('phone', '')
        email = self.content.get('email', '')
        
        return f'''
        <div class="row align-items-center g-5">
            <div class="col-lg-4 text-center">
                <img src="{photo}" alt="{name}" class="rounded-circle shadow img-fluid" style="max-width: 250px;">
            </div>
            <div class="col-lg-8">
                <h2>{name}</h2>
                <p class="text-muted mb-3">{title}</p>
                <p class="mb-4">{bio}</p>
                <div class="d-flex gap-3">
                    <a href="tel:{phone}" class="btn btn-primary"><i class="bi bi-telephone me-2"></i>{phone}</a>
                    <a href="mailto:{email}" class="btn btn-outline-primary"><i class="bi bi-envelope me-2"></i>Email Me</a>
                </div>
            </div>
        </div>
        '''
    
    def _render_market_stats(self) -> str:
        """Render market statistics section."""
        headline = self.content.get('headline', 'Central Ohio Market Stats')
        stats = self.content.get('stats', {})
        
        return f'''
        <h2 class="text-center mb-5">{headline}</h2>
        <div class="row g-4 text-center">
            <div class="col-md-3">
                <div class="card h-100">
                    <div class="card-body">
                        <h4 class="text-primary">{stats.get('median_price', '$0')}</h4>
                        <small class="text-muted">Median Home Price</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card h-100">
                    <div class="card-body">
                        <h4 class="text-primary">{stats.get('days_on_market', 0)}</h4>
                        <small class="text-muted">Avg Days on Market</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card h-100">
                    <div class="card-body">
                        <h4 class="text-primary">{stats.get('price_change', '0%')}</h4>
                        <small class="text-muted">YoY Price Change</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card h-100">
                    <div class="card-body">
                        <h4 class="text-primary">{stats.get('inventory', 0)}</h4>
                        <small class="text-muted">Active Listings</small>
                    </div>
                </div>
            </div>
        </div>
        '''
    
    def _render_calculator(self) -> str:
        """Render calculator widget section."""
        calc_type = self.content.get('calculator_type', 'mortgage')
        headline = self.content.get('headline', 'Calculate Your Payment')
        
        return f'''
        <h2 class="text-center mb-5">{headline}</h2>
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="card shadow">
                    <div class="card-body p-4">
                        <div id="calculator-widget" data-type="{calc_type}">
                            <!-- Calculator widget loaded via JavaScript -->
                            <noscript>Please enable JavaScript to use the calculator.</noscript>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''
    
    def _render_social_proof(self) -> str:
        """Render social proof section."""
        headline = self.content.get('headline', 'Trusted by Thousands')
        logos = self.content.get('logos', [])
        badges = self.content.get('badges', [])
        
        logos_html = '<div class="d-flex justify-content-center align-items-center flex-wrap gap-4 mb-4">'
        for logo in logos:
            logos_html += f'<img src="{logo}" alt="Partner" class="img-fluid" style="max-height: 50px;">'
        logos_html += '</div>'
        
        badges_html = '<div class="d-flex justify-content-center gap-3">'
        for badge in badges:
            badges_html += f'<span class="badge bg-primary fs-6">{badge}</span>'
        badges_html += '</div>'
        
        return f'''
        <div class="text-center">
            <h2 class="mb-5">{headline}</h2>
            {logos_html}
            {badges_html}
        </div>
        '''


@dataclass
class LandingPage:
    """A complete landing page."""
    id: str
    name: str
    slug: str
    title: str
    meta_description: str = ""
    sections: List[PageSection] = field(default_factory=list)
    form_id: str = None
    custom_css: str = ""
    custom_js: str = ""
    tracking_pixels: List[str] = field(default_factory=list)
    published: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    views: int = 0
    conversions: int = 0
    
    def to_html(self) -> str:
        """Generate complete HTML page."""
        sections_html = ''
        sorted_sections = sorted(self.sections, key=lambda s: s.order)
        for section in sorted_sections:
            if section.visible:
                sections_html += section.to_html()
        
        tracking_html = '\n'.join(self.tracking_pixels)
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <meta name="description" content="{self.meta_description}">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        .min-vh-75 {{ min-height: 75vh; }}
        .prose {{ line-height: 1.7; }}
        .prose p {{ margin-bottom: 1rem; }}
        {self.custom_css}
    </style>
    {tracking_html}
</head>
<body>
    {sections_html}
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Form submission handling
        document.querySelectorAll('.lead-capture-form').forEach(form => {{
            form.addEventListener('submit', async (e) => {{
                e.preventDefault();
                const formData = new FormData(form);
                try {{
                    const response = await fetch(form.action, {{
                        method: 'POST',
                        body: formData
                    }});
                    if (response.ok) {{
                        form.style.display = 'none';
                        form.nextElementSibling.classList.remove('d-none');
                    }}
                }} catch (err) {{
                    console.error('Form submission error:', err);
                }}
            }});
        }});
    </script>
    {self.custom_js}
</body>
</html>'''


class LandingPageBuilder:
    """Builder for creating and managing landing pages."""
    
    def __init__(self, storage_path: str = "data/landing_pages"):
        self.storage_path = storage_path
        self.pages: Dict[str, LandingPage] = {}
        self._load_pages()
    
    def _load_pages(self):
        """Load pages from storage."""
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        
        pages_file = f"{self.storage_path}/pages.json"
        if os.path.exists(pages_file):
            with open(pages_file, 'r') as f:
                data = json.load(f)
                for page_data in data:
                    page = self._dict_to_page(page_data)
                    self.pages[page.id] = page
    
    def _save_pages(self):
        """Save pages to storage."""
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        
        pages_data = [self._page_to_dict(page) for page in self.pages.values()]
        with open(f"{self.storage_path}/pages.json", 'w') as f:
            json.dump(pages_data, f, indent=2, default=str)
    
    def _page_to_dict(self, page: LandingPage) -> Dict:
        """Convert page to dictionary."""
        return {
            'id': page.id,
            'name': page.name,
            'slug': page.slug,
            'title': page.title,
            'meta_description': page.meta_description,
            'sections': [
                {
                    'id': s.id,
                    'section_type': s.section_type.value,
                    'title': s.title,
                    'subtitle': s.subtitle,
                    'content': s.content,
                    'styles': s.styles,
                    'order': s.order,
                    'visible': s.visible
                }
                for s in page.sections
            ],
            'form_id': page.form_id,
            'custom_css': page.custom_css,
            'custom_js': page.custom_js,
            'tracking_pixels': page.tracking_pixels,
            'published': page.published,
            'created_at': str(page.created_at),
            'updated_at': str(page.updated_at),
            'views': page.views,
            'conversions': page.conversions
        }
    
    def _dict_to_page(self, data: Dict) -> LandingPage:
        """Convert dictionary to page."""
        sections = [
            PageSection(
                id=s['id'],
                section_type=SectionType(s['section_type']),
                title=s.get('title', ''),
                subtitle=s.get('subtitle', ''),
                content=s.get('content', {}),
                styles=s.get('styles', {}),
                order=s.get('order', 0),
                visible=s.get('visible', True)
            )
            for s in data.get('sections', [])
        ]
        
        return LandingPage(
            id=data['id'],
            name=data['name'],
            slug=data['slug'],
            title=data['title'],
            meta_description=data.get('meta_description', ''),
            sections=sections,
            form_id=data.get('form_id'),
            custom_css=data.get('custom_css', ''),
            custom_js=data.get('custom_js', ''),
            tracking_pixels=data.get('tracking_pixels', []),
            published=data.get('published', False),
            views=data.get('views', 0),
            conversions=data.get('conversions', 0)
        )
    
    def create_page(self, name: str, slug: str, title: str) -> LandingPage:
        """Create a new landing page."""
        page = LandingPage(
            id=str(uuid.uuid4())[:8],
            name=name,
            slug=slug,
            title=title
        )
        self.pages[page.id] = page
        self._save_pages()
        return page
    
    def add_section(self, page_id: str, section: PageSection) -> bool:
        """Add a section to a page."""
        if page_id not in self.pages:
            return False
        
        self.pages[page_id].sections.append(section)
        self.pages[page_id].updated_at = datetime.now()
        self._save_pages()
        return True
    
    def update_section(self, page_id: str, section_id: str, updates: Dict) -> bool:
        """Update a section."""
        if page_id not in self.pages:
            return False
        
        for section in self.pages[page_id].sections:
            if section.id == section_id:
                for key, value in updates.items():
                    if hasattr(section, key):
                        setattr(section, key, value)
                self.pages[page_id].updated_at = datetime.now()
                self._save_pages()
                return True
        return False
    
    def remove_section(self, page_id: str, section_id: str) -> bool:
        """Remove a section from a page."""
        if page_id not in self.pages:
            return False
        
        self.pages[page_id].sections = [
            s for s in self.pages[page_id].sections if s.id != section_id
        ]
        self._save_pages()
        return True
    
    def get_page(self, page_id: str) -> Optional[LandingPage]:
        """Get a page by ID."""
        return self.pages.get(page_id)
    
    def get_page_by_slug(self, slug: str) -> Optional[LandingPage]:
        """Get a page by slug."""
        for page in self.pages.values():
            if page.slug == slug and page.published:
                return page
        return None
    
    def list_pages(self) -> List[LandingPage]:
        """List all pages."""
        return list(self.pages.values())
    
    def publish_page(self, page_id: str) -> bool:
        """Publish a page."""
        if page_id in self.pages:
            self.pages[page_id].published = True
            self.pages[page_id].updated_at = datetime.now()
            self._save_pages()
            return True
        return False
    
    def unpublish_page(self, page_id: str) -> bool:
        """Unpublish a page."""
        if page_id in self.pages:
            self.pages[page_id].published = False
            self._save_pages()
            return True
        return False
    
    def delete_page(self, page_id: str) -> bool:
        """Delete a page."""
        if page_id in self.pages:
            del self.pages[page_id]
            self._save_pages()
            return True
        return False
    
    def clone_page(self, page_id: str, new_name: str, new_slug: str) -> Optional[LandingPage]:
        """Clone an existing page."""
        if page_id not in self.pages:
            return None
        
        original = self.pages[page_id]
        new_page = LandingPage(
            id=str(uuid.uuid4())[:8],
            name=new_name,
            slug=new_slug,
            title=original.title,
            meta_description=original.meta_description,
            sections=[
                PageSection(
                    id=str(uuid.uuid4())[:8],
                    section_type=s.section_type,
                    title=s.title,
                    subtitle=s.subtitle,
                    content=s.content.copy(),
                    styles=s.styles.copy(),
                    order=s.order,
                    visible=s.visible
                )
                for s in original.sections
            ],
            form_id=original.form_id,
            custom_css=original.custom_css,
            custom_js=original.custom_js,
            published=False
        )
        
        self.pages[new_page.id] = new_page
        self._save_pages()
        return new_page
    
    def record_view(self, page_id: str):
        """Record a page view."""
        if page_id in self.pages:
            self.pages[page_id].views += 1
            self._save_pages()
    
    def record_conversion(self, page_id: str):
        """Record a conversion."""
        if page_id in self.pages:
            self.pages[page_id].conversions += 1
            self._save_pages()
    
    def get_analytics(self, page_id: str) -> Dict:
        """Get page analytics."""
        if page_id not in self.pages:
            return {}
        
        page = self.pages[page_id]
        conversion_rate = (page.conversions / page.views * 100) if page.views > 0 else 0
        
        return {
            'views': page.views,
            'conversions': page.conversions,
            'conversion_rate': round(conversion_rate, 2)
        }
    
    # Pre-built page templates
    def create_home_valuation_page(self, form_html: str = "") -> LandingPage:
        """Create a home valuation landing page."""
        page = self.create_page(
            name="Home Valuation",
            slug="home-valuation",
            title="What's Your Home Worth? | Free Home Valuation"
        )
        page.meta_description = "Get a free, instant home valuation for your Central Ohio property. Find out what your home is worth today."
        
        sections = [
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.HERO,
                content={
                    'headline': "What's Your Home Worth?",
                    'subheadline': "Get a free, instant home valuation from Central Ohio's trusted real estate experts.",
                    'cta_text': "Get My Free Valuation",
                    'cta_link': "#valuation-form",
                    'background_image': '/static/images/columbus-skyline.jpg',
                    'overlay': 'rgba(0,0,0,0.6)'
                },
                styles={'text_color': 'text-white'},
                order=1
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FORM,
                content={
                    'headline': "Get Your Free Home Value Report",
                    'form_html': form_html
                },
                order=2
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FEATURES,
                content={
                    'headline': "Why Get a Home Valuation?",
                    'features': [
                        {
                            'icon': 'bi-graph-up-arrow',
                            'title': 'Know Your Equity',
                            'description': 'Understanding your home value helps you make informed financial decisions.'
                        },
                        {
                            'icon': 'bi-clock',
                            'title': 'Market Timing',
                            'description': 'Learn if now is the right time to sell based on current market conditions.'
                        },
                        {
                            'icon': 'bi-cash-stack',
                            'title': 'Maximize Returns',
                            'description': 'Price your home right to attract buyers and get top dollar.'
                        }
                    ]
                },
                styles={'background': 'bg-light'},
                order=3
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.MARKET_STATS,
                content={
                    'headline': 'Central Ohio Market Snapshot',
                    'stats': {
                        'median_price': '$325,000',
                        'days_on_market': 18,
                        'price_change': '+5.2%',
                        'inventory': 2847
                    }
                },
                order=4
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.TESTIMONIALS,
                content={
                    'headline': 'What Our Sellers Say',
                    'testimonials': [
                        {
                            'quote': 'TD Realty helped us sell our home for 15% over asking price in just one week!',
                            'name': 'Sarah & Mike Johnson',
                            'location': 'Dublin, OH'
                        },
                        {
                            'quote': 'Professional, knowledgeable, and always available. Highly recommend!',
                            'name': 'David Chen',
                            'location': 'Worthington, OH'
                        }
                    ]
                },
                order=5
            )
        ]
        
        for section in sections:
            self.add_section(page.id, section)
        
        return page
    
    def create_buyer_landing_page(self, form_html: str = "") -> LandingPage:
        """Create a buyer-focused landing page."""
        page = self.create_page(
            name="Home Buyer Guide",
            slug="buy-home-columbus",
            title="Find Your Dream Home in Central Ohio"
        )
        page.meta_description = "Search homes for sale in Columbus, Dublin, Worthington and Central Ohio. Expert guidance for first-time and move-up buyers."
        
        sections = [
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.HERO,
                content={
                    'headline': "Find Your Perfect Home",
                    'subheadline': "Expert guidance through every step of your home buying journey in Central Ohio.",
                    'cta_text': "Start Your Search",
                    'cta_link': "#buyer-form",
                    'background_image': '/static/images/family-home.jpg',
                    'overlay': 'rgba(0,0,0,0.5)'
                },
                styles={'text_color': 'text-white'},
                order=1
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FORM,
                content={
                    'headline': "Tell Us What You're Looking For",
                    'form_html': form_html
                },
                order=2
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FEATURES,
                content={
                    'headline': "Why Work With Us?",
                    'features': [
                        {
                            'icon': 'bi-search',
                            'title': 'Exclusive Listings',
                            'description': 'Access to listings before they hit the market, including pocket listings.'
                        },
                        {
                            'icon': 'bi-shield-check',
                            'title': 'Expert Negotiation',
                            'description': 'Our agents negotiate aggressively to get you the best deal.'
                        },
                        {
                            'icon': 'bi-headset',
                            'title': '24/7 Support',
                            'description': 'We are available whenever you need us throughout your home search.'
                        }
                    ]
                },
                styles={'background': 'bg-light'},
                order=3
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.CALCULATOR,
                content={
                    'headline': 'Calculate Your Monthly Payment',
                    'calculator_type': 'mortgage'
                },
                order=4
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FAQ,
                content={
                    'headline': 'Frequently Asked Questions',
                    'faqs': [
                        {
                            'question': 'How much do I need for a down payment?',
                            'answer': 'Down payments can range from 0% for VA loans to 20% for conventional loans. FHA loans require just 3.5% down.'
                        },
                        {
                            'question': 'Do I need to get pre-approved before looking at homes?',
                            'answer': 'Yes, we highly recommend getting pre-approved. It helps you understand your budget and makes your offers stronger.'
                        },
                        {
                            'question': 'How long does the home buying process take?',
                            'answer': 'Typically 30-45 days from accepted offer to closing, though this can vary based on financing and inspection timelines.'
                        }
                    ]
                },
                order=5
            )
        ]
        
        for section in sections:
            self.add_section(page.id, section)
        
        return page
    
    def create_property_landing_page(self, property_data: Dict, form_html: str = "") -> LandingPage:
        """Create a property-specific landing page."""
        address = property_data.get('address', 'Property')
        page = self.create_page(
            name=f"Property - {address}",
            slug=f"property-{property_data.get('mls_id', str(uuid.uuid4())[:8])}",
            title=f"{address} | {property_data.get('price', '')} | Central Ohio Home for Sale"
        )
        
        sections = [
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.PROPERTY_SHOWCASE,
                content=property_data,
                order=1
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.FORM,
                content={
                    'headline': "Schedule a Showing",
                    'form_html': form_html
                },
                order=2
            ),
            PageSection(
                id=str(uuid.uuid4())[:8],
                section_type=SectionType.CALCULATOR,
                content={
                    'headline': 'Estimate Your Monthly Payment',
                    'calculator_type': 'mortgage'
                },
                order=3
            )
        ]
        
        for section in sections:
            self.add_section(page.id, section)
        
        return page
