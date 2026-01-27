"""Content generation for social media posts."""

import random
from datetime import datetime
from typing import List, Dict, Any, Optional


class ContentGenerator:
    """Generate social media content for real estate."""

    def __init__(self):
        """Initialize content generator."""
        self.emojis = {
            "house": ["🏠", "🏡", "🏘️", "🏚️"],
            "celebration": ["🎉", "🎊", "🥳", "✨"],
            "money": ["💰", "💵", "💲", "🤑"],
            "keys": ["🔑", "🗝️"],
            "location": ["📍", "📌"],
            "calendar": ["📅", "🗓️"],
            "time": ["⏰", "🕐"],
            "heart": ["❤️", "💕", "💖", "🏠💕"],
            "check": ["✅", "☑️", "✔️"],
            "star": ["⭐", "🌟", "✨"],
            "phone": ["📱", "☎️", "📞"],
            "camera": ["📸", "📷"],
            "sun": ["☀️", "🌞"],
            "arrow": ["👉", "➡️", "▶️"]
        }

        self.hashtag_sets = {
            "general": ["RealEstate", "Realtor", "HomeForSale", "DreamHome", "HouseHunting"],
            "columbus": ["ColumbusOH", "ColumbusRealEstate", "OhioRealtor", "CentralOhio", "614"],
            "buyer": ["FirstTimeHomeBuyer", "HomeBuyer", "HouseHunters", "FindingHome"],
            "seller": ["Selling", "HomeValue", "ListingAgent", "SellYourHome"],
            "market": ["RealEstateMarket", "HousingMarket", "MarketUpdate", "RealEstateNews"],
            "lifestyle": ["HomeOwner", "HomeSweetHome", "HomeLife", "MoveInReady"]
        }

    def generate_new_listing_content(
        self,
        address: str,
        price: int,
        beds: int,
        baths: float,
        sqft: int,
        features: List[str] = None,
        neighborhood: str = ""
    ) -> Dict[str, str]:
        """Generate content for new listing announcement."""
        price_str = f"${price:,}"

        # Different styles
        styles = {
            "excited": f"""
{random.choice(self.emojis['celebration'])} NEW LISTING ALERT {random.choice(self.emojis['celebration'])}

{random.choice(self.emojis['location'])} {address}
{random.choice(self.emojis['money'])} {price_str}

{random.choice(self.emojis['check'])} {beds} Bedrooms
{random.choice(self.emojis['check'])} {baths} Bathrooms
{random.choice(self.emojis['check'])} {sqft:,} Square Feet
{self._format_features(features) if features else ""}
This one won't last long! Contact us today to schedule a showing {random.choice(self.emojis['phone'])}
""",

            "elegant": f"""
Introducing {address}

{price_str} | {beds} BD | {baths} BA | {sqft:,} SF

{self._generate_feature_paragraph(features) if features else "A stunning property awaits."}

Schedule your private tour today.
""",

            "casual": f"""
Hey Columbus! {random.choice(self.emojis['house'])}

Check out this beauty that just hit the market!

{address}
{price_str}
{beds} beds • {baths} baths • {sqft:,} sqft

Who wants a tour? Drop a {random.choice(self.emojis['house'])} in the comments!
""",

            "professional": f"""
Just Listed in {neighborhood or 'Columbus'}

{address}

Offered at {price_str}

Property Highlights:
• {beds} Bedrooms, {baths} Bathrooms
• {sqft:,} Square Feet
{self._bullet_features(features) if features else ""}
Contact us for more information or to schedule a showing.
"""
        }

        # Generate hashtags
        hashtags = (
            self.hashtag_sets["general"][:3] +
            self.hashtag_sets["columbus"][:2] +
            ["NewListing", "JustListed", "ForSale"]
        )

        return {
            "excited": styles["excited"].strip(),
            "elegant": styles["elegant"].strip(),
            "casual": styles["casual"].strip(),
            "professional": styles["professional"].strip(),
            "hashtags": hashtags
        }

    def generate_sold_content(
        self,
        address: str,
        sale_price: int,
        client_type: str = "buyer",  # or "seller"
        days_on_market: int = 0,
        over_asking: bool = False
    ) -> Dict[str, str]:
        """Generate content for sold announcement."""
        price_str = f"${sale_price:,}"

        celebration = random.choice(self.emojis['celebration'])
        keys = random.choice(self.emojis['keys'])
        house = random.choice(self.emojis['house'])

        sold_stats = ""
        if days_on_market > 0:
            sold_stats = f"\n⏱️ {days_on_market} Days on Market"
        if over_asking:
            sold_stats += "\n📈 SOLD OVER ASKING!"

        styles = {
            "celebration": f"""
{celebration} SOLD! {celebration}

{house} {address}
{random.choice(self.emojis['money'])} {price_str}{sold_stats}

Another happy {"homeowner" if client_type == "buyer" else "seller"}! {keys}

Thinking of {"buying" if client_type == "seller" else "selling"}? Let's chat! {random.choice(self.emojis['phone'])}
""",

            "grateful": f"""
{keys} Closing Day! {keys}

So grateful to have helped {"find the perfect home" if client_type == "buyer" else "successfully sell"} at {address}.

{price_str}{sold_stats}

Thank you for trusting us with your real estate journey! {random.choice(self.emojis['heart'])}
""",

            "milestone": f"""
Another Successful Close! {celebration}

{house} {address}
{price_str}{sold_stats}

{"Welcome home to our amazing buyers!" if client_type == "buyer" else "Congratulations to our sellers on a successful sale!"}

Ready for your success story? Let's connect! {random.choice(self.emojis['arrow'])}
"""
        }

        hashtags = ["JustSold", "Sold", "ClosingDay", "RealEstateAgent"] + self.hashtag_sets["columbus"][:2]
        if client_type == "buyer":
            hashtags.append("NewHomeowner")
        else:
            hashtags.append("HomeSold")

        return {
            "celebration": styles["celebration"].strip(),
            "grateful": styles["grateful"].strip(),
            "milestone": styles["milestone"].strip(),
            "hashtags": hashtags
        }

    def generate_open_house_content(
        self,
        address: str,
        date: datetime,
        start_time: str,
        end_time: str,
        price: int,
        beds: int = 0,
        baths: float = 0
    ) -> Dict[str, str]:
        """Generate content for open house announcement."""
        date_str = date.strftime("%A, %B %d")
        price_str = f"${price:,}"

        details = f"{beds} BD | {baths} BA" if beds > 0 else ""

        styles = {
            "invitation": f"""
{random.choice(self.emojis['house'])} OPEN HOUSE {random.choice(self.emojis['house'])}

{random.choice(self.emojis['location'])} {address}
{random.choice(self.emojis['calendar'])} {date_str}
{random.choice(self.emojis['time'])} {start_time} - {end_time}
{random.choice(self.emojis['money'])} {price_str}
{details}

Stop by and say hello! No appointment needed.
See you there! 👋
""",

            "countdown": f"""
SAVE THE DATE! 📅

Open House this {date.strftime("%A")}!

📍 {address}
⏰ {start_time} - {end_time}
💰 {price_str}

Mark your calendar and come check out this beautiful home!
""",

            "reminder": f"""
{random.choice(self.emojis['sun'])} This Weekend! {random.choice(self.emojis['sun'])}

Join us for an Open House:

{address}
{date_str}
{start_time} - {end_time}

Priced at {price_str}

Tag someone who's house hunting! 🏠👀
"""
        }

        hashtags = ["OpenHouse", "OpenHouseWeekend"] + self.hashtag_sets["general"][:3] + self.hashtag_sets["columbus"][:2]

        return {
            "invitation": styles["invitation"].strip(),
            "countdown": styles["countdown"].strip(),
            "reminder": styles["reminder"].strip(),
            "hashtags": hashtags
        }

    def generate_market_update_content(
        self,
        area: str,
        median_price: int,
        price_change: float,
        days_on_market: int,
        inventory: str
    ) -> Dict[str, str]:
        """Generate content for market update post."""
        trend = "📈" if price_change > 0 else "📉" if price_change < 0 else "➡️"

        styles = {
            "informative": f"""
📊 {area} Market Update 📊

{random.choice(self.emojis['money'])} Median Price: ${median_price:,}
{trend} Year-over-Year: {price_change:+.1f}%
⏱️ Avg Days on Market: {days_on_market}
🏠 Inventory: {inventory}

What does this mean for you? Let's discuss your real estate goals!
""",

            "brief": f"""
{area} Real Estate Snapshot 📊

• Median: ${median_price:,} ({price_change:+.1f}% YoY)
• DOM: {days_on_market} days
• Market: {inventory} inventory

Questions? Drop them below! 👇
""",

            "actionable": f"""
{area} Market Check-In 🏡

The numbers are in:
${median_price:,} median price
{days_on_market} average days on market
{inventory} inventory levels

{"Great time for sellers!" if price_change > 3 else "Opportunities for buyers!" if price_change < 0 else "Balanced market conditions."}

Let's talk strategy. DM me! 📱
"""
        }

        hashtags = self.hashtag_sets["market"] + self.hashtag_sets["columbus"][:2]

        return {
            "informative": styles["informative"].strip(),
            "brief": styles["brief"].strip(),
            "actionable": styles["actionable"].strip(),
            "hashtags": hashtags
        }

    def generate_tip_content(self, category: str = "buying") -> Dict[str, str]:
        """Generate real estate tip content."""
        tips = {
            "buying": [
                ("Get Pre-Approved First", "Before you start house hunting, get pre-approved for a mortgage. It shows sellers you're serious and helps you know your budget."),
                ("Don't Skip the Inspection", "A home inspection might cost a few hundred dollars, but it could save you thousands in unexpected repairs."),
                ("Look Beyond Cosmetics", "Don't let outdated paint or carpet scare you away from a great home. Focus on location, layout, and bones!"),
                ("Consider Future Resale", "Even if you plan to stay forever, think about resale value. Location and layout matter!"),
            ],
            "selling": [
                ("First Impressions Matter", "Curb appeal can make or break a showing. Fresh mulch, trimmed bushes, and a clean entrance go a long way!"),
                ("Declutter and Depersonalize", "Help buyers envision themselves in your home by removing personal items and excess furniture."),
                ("Price It Right", "The first two weeks are crucial. An overpriced home will sit, while a well-priced home attracts multiple offers."),
                ("Professional Photos Are Worth It", "Most buyers start their search online. Great photos get more clicks, showings, and offers!"),
            ],
            "general": [
                ("Work with a Local Expert", "Real estate is local. An agent who knows your market can help you make informed decisions."),
                ("Don't Make Big Purchases", "Avoid major purchases (new car, furniture) before closing. It can affect your loan approval!"),
                ("Read Everything Carefully", "Real estate involves lots of paperwork. Read and understand everything before signing."),
            ]
        }

        tip_list = tips.get(category, tips["general"])
        title, content = random.choice(tip_list)

        styles = {
            "educational": f"""
💡 Real Estate Tip 💡

{title}

{content}

{random.choice(self.emojis['check'])} Save this for later!
{random.choice(self.emojis['arrow'])} Share with someone who needs to hear this!
""",

            "question": f"""
Did you know? 🤔

{content}

Have questions about {"buying" if category == "buying" else "selling" if category == "selling" else "real estate"}? Drop them below! 👇
""",

            "list_style": f"""
{random.choice(self.emojis['star'])} PRO TIP: {title}

{content}

More tips in my bio! {random.choice(self.emojis['arrow'])}
"""
        }

        hashtags = ["RealEstateTip", "RealEstateAdvice"] + self.hashtag_sets[category if category in self.hashtag_sets else "general"][:3]

        return {
            "educational": styles["educational"].strip(),
            "question": styles["question"].strip(),
            "list_style": styles["list_style"].strip(),
            "hashtags": hashtags,
            "title": title
        }

    def _format_features(self, features: List[str]) -> str:
        """Format feature list with emojis."""
        if not features:
            return ""

        formatted = []
        for feature in features[:5]:
            formatted.append(f"{random.choice(self.emojis['check'])} {feature}")

        return "\n".join(formatted)

    def _bullet_features(self, features: List[str]) -> str:
        """Format features as bullet points."""
        if not features:
            return ""

        return "\n".join(f"• {f}" for f in features[:5])

    def _generate_feature_paragraph(self, features: List[str]) -> str:
        """Generate a paragraph describing features."""
        if not features or len(features) < 2:
            return "A wonderful opportunity awaits."

        if len(features) >= 4:
            return f"Featuring {features[0].lower()}, {features[1].lower()}, and {features[2].lower()}, this home offers everything you've been searching for."
        else:
            return f"This home features {' and '.join(f.lower() for f in features[:2])}."

    def get_hashtag_suggestions(self, post_type: str, location: str = "columbus") -> List[str]:
        """Get hashtag suggestions for a post type."""
        base = self.hashtag_sets.get("general", [])[:3]
        location_tags = self.hashtag_sets.get(location, self.hashtag_sets["columbus"])[:3]

        type_specific = {
            "listing": ["NewListing", "JustListed", "ForSale", "HomeForSale"],
            "sold": ["JustSold", "Sold", "ClosingDay", "HomeSold"],
            "open_house": ["OpenHouse", "OpenHouseWeekend", "HomeTour"],
            "market": ["MarketUpdate", "RealEstateMarket", "HousingMarket"],
            "tip": ["RealEstateTip", "HomeOwnerTips", "RealEstateAdvice"]
        }

        specific = type_specific.get(post_type, [])

        return list(set(base + location_tags + specific))[:15]
