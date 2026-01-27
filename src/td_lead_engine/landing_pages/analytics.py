"""Analytics for landing pages."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os


@dataclass
class PageView:
    """A single page view event."""
    page_id: str
    visitor_id: str
    timestamp: datetime
    referrer: str = ""
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    user_agent: str = ""
    ip_address: str = ""
    device_type: str = ""
    location: Dict = field(default_factory=dict)


@dataclass
class FormSubmission:
    """A form submission event."""
    page_id: str
    form_id: str
    visitor_id: str
    timestamp: datetime
    lead_id: str = ""
    form_data: Dict = field(default_factory=dict)


@dataclass  
class ABTestVariant:
    """A/B test variant."""
    id: str
    name: str
    page_id: str
    views: int = 0
    conversions: int = 0
    
    @property
    def conversion_rate(self) -> float:
        return (self.conversions / self.views * 100) if self.views > 0 else 0


@dataclass
class ABTest:
    """A/B test configuration."""
    id: str
    name: str
    variants: List[ABTestVariant]
    start_date: datetime
    end_date: Optional[datetime] = None
    winner_id: Optional[str] = None
    status: str = "running"  # running, completed, paused


class PageAnalytics:
    """Analytics tracking for landing pages."""
    
    def __init__(self, storage_path: str = "data/analytics"):
        self.storage_path = storage_path
        self.page_views: List[PageView] = []
        self.form_submissions: List[FormSubmission] = []
        self.ab_tests: Dict[str, ABTest] = {}
        self._load_data()
    
    def _load_data(self):
        """Load analytics data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load page views
        views_file = f"{self.storage_path}/page_views.json"
        if os.path.exists(views_file):
            with open(views_file, 'r') as f:
                data = json.load(f)
                self.page_views = [
                    PageView(
                        page_id=v['page_id'],
                        visitor_id=v['visitor_id'],
                        timestamp=datetime.fromisoformat(v['timestamp']),
                        referrer=v.get('referrer', ''),
                        utm_source=v.get('utm_source', ''),
                        utm_medium=v.get('utm_medium', ''),
                        utm_campaign=v.get('utm_campaign', ''),
                        user_agent=v.get('user_agent', ''),
                        ip_address=v.get('ip_address', ''),
                        device_type=v.get('device_type', ''),
                        location=v.get('location', {})
                    )
                    for v in data
                ]
        
        # Load form submissions
        submissions_file = f"{self.storage_path}/form_submissions.json"
        if os.path.exists(submissions_file):
            with open(submissions_file, 'r') as f:
                data = json.load(f)
                self.form_submissions = [
                    FormSubmission(
                        page_id=s['page_id'],
                        form_id=s['form_id'],
                        visitor_id=s['visitor_id'],
                        timestamp=datetime.fromisoformat(s['timestamp']),
                        lead_id=s.get('lead_id', ''),
                        form_data=s.get('form_data', {})
                    )
                    for s in data
                ]
        
        # Load A/B tests
        ab_file = f"{self.storage_path}/ab_tests.json"
        if os.path.exists(ab_file):
            with open(ab_file, 'r') as f:
                data = json.load(f)
                for test_data in data:
                    variants = [
                        ABTestVariant(
                            id=v['id'],
                            name=v['name'],
                            page_id=v['page_id'],
                            views=v.get('views', 0),
                            conversions=v.get('conversions', 0)
                        )
                        for v in test_data.get('variants', [])
                    ]
                    test = ABTest(
                        id=test_data['id'],
                        name=test_data['name'],
                        variants=variants,
                        start_date=datetime.fromisoformat(test_data['start_date']),
                        end_date=datetime.fromisoformat(test_data['end_date']) if test_data.get('end_date') else None,
                        winner_id=test_data.get('winner_id'),
                        status=test_data.get('status', 'running')
                    )
                    self.ab_tests[test.id] = test
    
    def _save_data(self):
        """Save analytics data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save page views (keep last 10000)
        views_data = [
            {
                'page_id': v.page_id,
                'visitor_id': v.visitor_id,
                'timestamp': v.timestamp.isoformat(),
                'referrer': v.referrer,
                'utm_source': v.utm_source,
                'utm_medium': v.utm_medium,
                'utm_campaign': v.utm_campaign,
                'user_agent': v.user_agent,
                'ip_address': v.ip_address,
                'device_type': v.device_type,
                'location': v.location
            }
            for v in self.page_views[-10000:]
        ]
        with open(f"{self.storage_path}/page_views.json", 'w') as f:
            json.dump(views_data, f, indent=2)
        
        # Save form submissions
        submissions_data = [
            {
                'page_id': s.page_id,
                'form_id': s.form_id,
                'visitor_id': s.visitor_id,
                'timestamp': s.timestamp.isoformat(),
                'lead_id': s.lead_id,
                'form_data': s.form_data
            }
            for s in self.form_submissions[-10000:]
        ]
        with open(f"{self.storage_path}/form_submissions.json", 'w') as f:
            json.dump(submissions_data, f, indent=2)
        
        # Save A/B tests
        ab_data = [
            {
                'id': test.id,
                'name': test.name,
                'variants': [
                    {
                        'id': v.id,
                        'name': v.name,
                        'page_id': v.page_id,
                        'views': v.views,
                        'conversions': v.conversions
                    }
                    for v in test.variants
                ],
                'start_date': test.start_date.isoformat(),
                'end_date': test.end_date.isoformat() if test.end_date else None,
                'winner_id': test.winner_id,
                'status': test.status
            }
            for test in self.ab_tests.values()
        ]
        with open(f"{self.storage_path}/ab_tests.json", 'w') as f:
            json.dump(ab_data, f, indent=2)
    
    def record_page_view(
        self,
        page_id: str,
        visitor_id: str,
        referrer: str = "",
        utm_source: str = "",
        utm_medium: str = "",
        utm_campaign: str = "",
        user_agent: str = "",
        ip_address: str = ""
    ):
        """Record a page view."""
        device_type = self._detect_device(user_agent)
        
        view = PageView(
            page_id=page_id,
            visitor_id=visitor_id,
            timestamp=datetime.now(),
            referrer=referrer,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            user_agent=user_agent,
            ip_address=ip_address,
            device_type=device_type
        )
        self.page_views.append(view)
        self._save_data()
    
    def record_form_submission(
        self,
        page_id: str,
        form_id: str,
        visitor_id: str,
        lead_id: str = "",
        form_data: Dict = None
    ):
        """Record a form submission."""
        submission = FormSubmission(
            page_id=page_id,
            form_id=form_id,
            visitor_id=visitor_id,
            timestamp=datetime.now(),
            lead_id=lead_id,
            form_data=form_data or {}
        )
        self.form_submissions.append(submission)
        self._save_data()
    
    def get_page_stats(
        self,
        page_id: str,
        days: int = 30
    ) -> Dict:
        """Get statistics for a specific page."""
        cutoff = datetime.now() - timedelta(days=days)
        
        views = [v for v in self.page_views if v.page_id == page_id and v.timestamp > cutoff]
        submissions = [s for s in self.form_submissions if s.page_id == page_id and s.timestamp > cutoff]
        
        unique_visitors = len(set(v.visitor_id for v in views))
        conversion_rate = (len(submissions) / len(views) * 100) if views else 0
        
        # Traffic sources
        sources = defaultdict(int)
        for v in views:
            source = v.utm_source or self._categorize_referrer(v.referrer)
            sources[source] += 1
        
        # Device breakdown
        devices = defaultdict(int)
        for v in views:
            devices[v.device_type or 'unknown'] += 1
        
        # Daily views
        daily_views = defaultdict(int)
        for v in views:
            day = v.timestamp.strftime('%Y-%m-%d')
            daily_views[day] += 1
        
        return {
            'total_views': len(views),
            'unique_visitors': unique_visitors,
            'total_conversions': len(submissions),
            'conversion_rate': round(conversion_rate, 2),
            'avg_daily_views': round(len(views) / days, 1),
            'traffic_sources': dict(sources),
            'device_breakdown': dict(devices),
            'daily_views': dict(sorted(daily_views.items())),
            'top_referrers': self._get_top_referrers(views, 5),
            'top_campaigns': self._get_top_campaigns(views, 5)
        }
    
    def get_overall_stats(self, days: int = 30) -> Dict:
        """Get overall analytics statistics."""
        cutoff = datetime.now() - timedelta(days=days)
        
        views = [v for v in self.page_views if v.timestamp > cutoff]
        submissions = [s for s in self.form_submissions if s.timestamp > cutoff]
        
        # Page performance
        page_stats = defaultdict(lambda: {'views': 0, 'conversions': 0})
        for v in views:
            page_stats[v.page_id]['views'] += 1
        for s in submissions:
            page_stats[s.page_id]['conversions'] += 1
        
        # Calculate conversion rates
        for page_id, stats in page_stats.items():
            stats['conversion_rate'] = (stats['conversions'] / stats['views'] * 100) if stats['views'] > 0 else 0
        
        # Sort by views
        top_pages = sorted(page_stats.items(), key=lambda x: x[1]['views'], reverse=True)[:10]
        
        return {
            'total_views': len(views),
            'total_conversions': len(submissions),
            'overall_conversion_rate': round((len(submissions) / len(views) * 100) if views else 0, 2),
            'unique_visitors': len(set(v.visitor_id for v in views)),
            'top_pages': [{'page_id': p[0], **p[1]} for p in top_pages],
            'traffic_by_source': self._aggregate_by_source(views),
            'conversions_by_day': self._aggregate_by_day(submissions)
        }
    
    def create_ab_test(
        self,
        name: str,
        variant_pages: List[Dict]
    ) -> ABTest:
        """Create a new A/B test."""
        import uuid
        
        test_id = str(uuid.uuid4())[:8]
        variants = [
            ABTestVariant(
                id=str(uuid.uuid4())[:8],
                name=v.get('name', f"Variant {i+1}"),
                page_id=v['page_id']
            )
            for i, v in enumerate(variant_pages)
        ]
        
        test = ABTest(
            id=test_id,
            name=name,
            variants=variants,
            start_date=datetime.now()
        )
        
        self.ab_tests[test_id] = test
        self._save_data()
        return test
    
    def get_ab_test_variant(self, test_id: str, visitor_id: str) -> Optional[ABTestVariant]:
        """Get a variant for a visitor (consistent assignment)."""
        if test_id not in self.ab_tests:
            return None
        
        test = self.ab_tests[test_id]
        if test.status != 'running':
            return None
        
        # Simple hash-based assignment for consistency
        hash_value = hash(f"{test_id}:{visitor_id}") % len(test.variants)
        return test.variants[hash_value]
    
    def record_ab_view(self, test_id: str, variant_id: str):
        """Record a view for an A/B test variant."""
        if test_id in self.ab_tests:
            for variant in self.ab_tests[test_id].variants:
                if variant.id == variant_id:
                    variant.views += 1
                    self._save_data()
                    break
    
    def record_ab_conversion(self, test_id: str, variant_id: str):
        """Record a conversion for an A/B test variant."""
        if test_id in self.ab_tests:
            for variant in self.ab_tests[test_id].variants:
                if variant.id == variant_id:
                    variant.conversions += 1
                    self._save_data()
                    break
    
    def get_ab_test_results(self, test_id: str) -> Optional[Dict]:
        """Get results of an A/B test."""
        if test_id not in self.ab_tests:
            return None
        
        test = self.ab_tests[test_id]
        
        results = {
            'test_id': test.id,
            'name': test.name,
            'status': test.status,
            'start_date': test.start_date.isoformat(),
            'end_date': test.end_date.isoformat() if test.end_date else None,
            'winner_id': test.winner_id,
            'variants': []
        }
        
        best_rate = 0
        best_variant = None
        
        for variant in test.variants:
            var_data = {
                'id': variant.id,
                'name': variant.name,
                'page_id': variant.page_id,
                'views': variant.views,
                'conversions': variant.conversions,
                'conversion_rate': round(variant.conversion_rate, 2)
            }
            results['variants'].append(var_data)
            
            if variant.conversion_rate > best_rate:
                best_rate = variant.conversion_rate
                best_variant = variant
        
        # Statistical significance (simplified)
        if best_variant and best_variant.views >= 100:
            results['leading_variant'] = best_variant.id
            results['confidence'] = self._calculate_confidence(test.variants)
        
        return results
    
    def end_ab_test(self, test_id: str, winner_id: str = None):
        """End an A/B test and declare a winner."""
        if test_id in self.ab_tests:
            test = self.ab_tests[test_id]
            test.status = 'completed'
            test.end_date = datetime.now()
            
            if winner_id:
                test.winner_id = winner_id
            else:
                # Auto-select winner based on conversion rate
                best_variant = max(test.variants, key=lambda v: v.conversion_rate)
                test.winner_id = best_variant.id
            
            self._save_data()
    
    def _detect_device(self, user_agent: str) -> str:
        """Detect device type from user agent."""
        user_agent = user_agent.lower()
        if 'mobile' in user_agent or 'android' in user_agent:
            return 'mobile'
        elif 'tablet' in user_agent or 'ipad' in user_agent:
            return 'tablet'
        return 'desktop'
    
    def _categorize_referrer(self, referrer: str) -> str:
        """Categorize traffic source from referrer."""
        if not referrer:
            return 'direct'
        
        referrer = referrer.lower()
        if 'google' in referrer:
            return 'google'
        elif 'facebook' in referrer or 'fb.com' in referrer:
            return 'facebook'
        elif 'instagram' in referrer:
            return 'instagram'
        elif 'zillow' in referrer:
            return 'zillow'
        elif 'realtor.com' in referrer:
            return 'realtor.com'
        elif 'bing' in referrer:
            return 'bing'
        elif 'yahoo' in referrer:
            return 'yahoo'
        return 'referral'
    
    def _get_top_referrers(self, views: List[PageView], limit: int) -> List[Dict]:
        """Get top referrers."""
        referrers = defaultdict(int)
        for v in views:
            if v.referrer:
                referrers[v.referrer] += 1
        
        sorted_refs = sorted(referrers.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{'referrer': r[0], 'count': r[1]} for r in sorted_refs]
    
    def _get_top_campaigns(self, views: List[PageView], limit: int) -> List[Dict]:
        """Get top campaigns."""
        campaigns = defaultdict(int)
        for v in views:
            if v.utm_campaign:
                campaigns[v.utm_campaign] += 1
        
        sorted_camps = sorted(campaigns.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{'campaign': c[0], 'count': c[1]} for c in sorted_camps]
    
    def _aggregate_by_source(self, views: List[PageView]) -> Dict:
        """Aggregate views by traffic source."""
        sources = defaultdict(int)
        for v in views:
            source = v.utm_source or self._categorize_referrer(v.referrer)
            sources[source] += 1
        return dict(sources)
    
    def _aggregate_by_day(self, submissions: List[FormSubmission]) -> Dict:
        """Aggregate submissions by day."""
        daily = defaultdict(int)
        for s in submissions:
            day = s.timestamp.strftime('%Y-%m-%d')
            daily[day] += 1
        return dict(sorted(daily.items()))
    
    def _calculate_confidence(self, variants: List[ABTestVariant]) -> float:
        """Calculate statistical confidence (simplified)."""
        if len(variants) < 2:
            return 0
        
        # Simple comparison - in production, use proper statistical tests
        sorted_variants = sorted(variants, key=lambda v: v.conversion_rate, reverse=True)
        
        if sorted_variants[0].views < 100 or sorted_variants[1].views < 100:
            return 0
        
        rate_diff = sorted_variants[0].conversion_rate - sorted_variants[1].conversion_rate
        
        if rate_diff > 5:
            return 95
        elif rate_diff > 3:
            return 85
        elif rate_diff > 1:
            return 70
        return 50
