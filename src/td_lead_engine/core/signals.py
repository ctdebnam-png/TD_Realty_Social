"""Intent signals for lead scoring - tuned for Central Ohio real estate."""

from dataclasses import dataclass
from enum import Enum
from typing import List


class SignalCategory(Enum):
    """Categories of buying/selling intent signals."""

    BUYER_ACTIVE = "buyer_active"  # Actively searching
    BUYER_PASSIVE = "buyer_passive"  # Considering buying
    SELLER_ACTIVE = "seller_active"  # Ready to sell
    SELLER_PASSIVE = "seller_passive"  # Considering selling
    INVESTOR = "investor"  # Investment interest
    TIMELINE = "timeline"  # Urgency indicators
    LOCATION = "location"  # Central Ohio specific
    NEGATIVE = "negative"  # Competitor/agent signals
    LIFE_EVENT = "life_event"  # Major life changes
    FINANCIAL = "financial"  # Financial readiness


@dataclass
class IntentSignal:
    """A single intent signal with scoring weight."""

    phrase: str
    weight: int
    category: SignalCategory
    description: str = ""


# 50+ intent phrases tuned for Central Ohio real estate
INTENT_SIGNALS: List[IntentSignal] = [
    # === BUYER - ACTIVE (High Intent) ===
    IntentSignal("first time homebuyer", 80, SignalCategory.BUYER_ACTIVE, "FTB with high motivation"),
    IntentSignal("first time home buyer", 80, SignalCategory.BUYER_ACTIVE, "FTB alternate spelling"),
    IntentSignal("looking for a house", 75, SignalCategory.BUYER_ACTIVE, "Active search"),
    IntentSignal("looking for a home", 75, SignalCategory.BUYER_ACTIVE, "Active search"),
    IntentSignal("house hunting", 85, SignalCategory.BUYER_ACTIVE, "Active search behavior"),
    IntentSignal("home hunting", 85, SignalCategory.BUYER_ACTIVE, "Active search behavior"),
    IntentSignal("searching for a home", 80, SignalCategory.BUYER_ACTIVE, "Active search"),
    IntentSignal("ready to buy", 90, SignalCategory.BUYER_ACTIVE, "High intent declaration"),
    IntentSignal("want to buy a house", 75, SignalCategory.BUYER_ACTIVE, "Direct intent"),
    IntentSignal("want to buy a home", 75, SignalCategory.BUYER_ACTIVE, "Direct intent"),
    IntentSignal("need a realtor", 85, SignalCategory.BUYER_ACTIVE, "Seeking representation"),
    IntentSignal("need an agent", 85, SignalCategory.BUYER_ACTIVE, "Seeking representation"),
    IntentSignal("looking for a realtor", 85, SignalCategory.BUYER_ACTIVE, "Seeking representation"),
    IntentSignal("preapproved", 90, SignalCategory.BUYER_ACTIVE, "Financially ready"),
    IntentSignal("pre-approved", 90, SignalCategory.BUYER_ACTIVE, "Financially ready"),
    IntentSignal("got preapproval", 90, SignalCategory.BUYER_ACTIVE, "Financially ready"),
    IntentSignal("mortgage approved", 95, SignalCategory.BUYER_ACTIVE, "Financially committed"),

    # === BUYER - PASSIVE (Considering) ===
    IntentSignal("thinking about buying", 50, SignalCategory.BUYER_PASSIVE, "Early stage"),
    IntentSignal("considering buying", 50, SignalCategory.BUYER_PASSIVE, "Early stage"),
    IntentSignal("might buy", 40, SignalCategory.BUYER_PASSIVE, "Early stage"),
    IntentSignal("saving for a house", 45, SignalCategory.BUYER_PASSIVE, "Future buyer"),
    IntentSignal("saving for a home", 45, SignalCategory.BUYER_PASSIVE, "Future buyer"),
    IntentSignal("down payment", 55, SignalCategory.BUYER_PASSIVE, "Preparing financially"),
    IntentSignal("how much house can i afford", 60, SignalCategory.BUYER_PASSIVE, "Research phase"),
    IntentSignal("what can i afford", 55, SignalCategory.BUYER_PASSIVE, "Research phase"),

    # === SELLER - ACTIVE (High Intent) ===
    IntentSignal("listing my house", 90, SignalCategory.SELLER_ACTIVE, "Ready to list"),
    IntentSignal("listing my home", 90, SignalCategory.SELLER_ACTIVE, "Ready to list"),
    IntentSignal("selling my house", 85, SignalCategory.SELLER_ACTIVE, "Active seller"),
    IntentSignal("selling my home", 85, SignalCategory.SELLER_ACTIVE, "Active seller"),
    IntentSignal("ready to sell", 90, SignalCategory.SELLER_ACTIVE, "High intent"),
    IntentSignal("need to sell", 85, SignalCategory.SELLER_ACTIVE, "Motivated seller"),
    IntentSignal("time to sell", 80, SignalCategory.SELLER_ACTIVE, "Decision made"),
    IntentSignal("putting house on market", 95, SignalCategory.SELLER_ACTIVE, "Imminent listing"),
    IntentSignal("what is my home worth", 70, SignalCategory.SELLER_ACTIVE, "CMA interest"),
    IntentSignal("what's my home worth", 70, SignalCategory.SELLER_ACTIVE, "CMA interest"),
    IntentSignal("home value", 50, SignalCategory.SELLER_ACTIVE, "Research phase"),

    # === SELLER - PASSIVE (Considering) ===
    IntentSignal("thinking about selling", 55, SignalCategory.SELLER_PASSIVE, "Early stage"),
    IntentSignal("considering selling", 55, SignalCategory.SELLER_PASSIVE, "Early stage"),
    IntentSignal("might sell", 40, SignalCategory.SELLER_PASSIVE, "Very early"),
    IntentSignal("should i sell", 50, SignalCategory.SELLER_PASSIVE, "Research phase"),
    IntentSignal("good time to sell", 45, SignalCategory.SELLER_PASSIVE, "Market research"),

    # === INVESTOR ===
    IntentSignal("investment property", 70, SignalCategory.INVESTOR, "Investor interest"),
    IntentSignal("rental property", 65, SignalCategory.INVESTOR, "Rental investor"),
    IntentSignal("looking to invest", 60, SignalCategory.INVESTOR, "Investment interest"),
    IntentSignal("real estate investing", 55, SignalCategory.INVESTOR, "Investor mindset"),
    IntentSignal("flip", 50, SignalCategory.INVESTOR, "Fix and flip"),
    IntentSignal("fixer upper", 55, SignalCategory.INVESTOR, "Value-add buyer"),
    IntentSignal("cash flow", 60, SignalCategory.INVESTOR, "Rental investor"),
    IntentSignal("passive income", 45, SignalCategory.INVESTOR, "Investment motivation"),

    # === TIMELINE (Urgency) ===
    IntentSignal("asap", 70, SignalCategory.TIMELINE, "Urgent"),
    IntentSignal("as soon as possible", 70, SignalCategory.TIMELINE, "Urgent"),
    IntentSignal("this month", 65, SignalCategory.TIMELINE, "Near-term"),
    IntentSignal("next month", 55, SignalCategory.TIMELINE, "Near-term"),
    IntentSignal("this year", 35, SignalCategory.TIMELINE, "Within year"),
    IntentSignal("by spring", 50, SignalCategory.TIMELINE, "Seasonal target"),
    IntentSignal("by summer", 50, SignalCategory.TIMELINE, "Seasonal target"),
    IntentSignal("before school", 60, SignalCategory.TIMELINE, "School year deadline"),
    IntentSignal("before school starts", 65, SignalCategory.TIMELINE, "School year deadline"),
    IntentSignal("lease is up", 75, SignalCategory.TIMELINE, "Rental expiring"),
    IntentSignal("lease ends", 75, SignalCategory.TIMELINE, "Rental expiring"),
    IntentSignal("lease ending", 75, SignalCategory.TIMELINE, "Rental expiring"),

    # === LOCATION - Central Ohio ===
    IntentSignal("columbus", 25, SignalCategory.LOCATION, "Columbus metro"),
    IntentSignal("powell", 30, SignalCategory.LOCATION, "Powell OH"),
    IntentSignal("dublin", 30, SignalCategory.LOCATION, "Dublin OH"),
    IntentSignal("westerville", 30, SignalCategory.LOCATION, "Westerville OH"),
    IntentSignal("new albany", 30, SignalCategory.LOCATION, "New Albany OH"),
    IntentSignal("hilliard", 30, SignalCategory.LOCATION, "Hilliard OH"),
    IntentSignal("grove city", 30, SignalCategory.LOCATION, "Grove City OH"),
    IntentSignal("gahanna", 30, SignalCategory.LOCATION, "Gahanna OH"),
    IntentSignal("reynoldsburg", 30, SignalCategory.LOCATION, "Reynoldsburg OH"),
    IntentSignal("pickerington", 30, SignalCategory.LOCATION, "Pickerington OH"),
    IntentSignal("delaware", 25, SignalCategory.LOCATION, "Delaware OH"),
    IntentSignal("lewis center", 30, SignalCategory.LOCATION, "Lewis Center OH"),
    IntentSignal("worthington", 30, SignalCategory.LOCATION, "Worthington OH"),
    IntentSignal("upper arlington", 30, SignalCategory.LOCATION, "Upper Arlington OH"),
    IntentSignal("bexley", 30, SignalCategory.LOCATION, "Bexley OH"),
    IntentSignal("grandview", 30, SignalCategory.LOCATION, "Grandview Heights OH"),
    IntentSignal("german village", 30, SignalCategory.LOCATION, "German Village"),
    IntentSignal("short north", 30, SignalCategory.LOCATION, "Short North"),
    IntentSignal("clintonville", 30, SignalCategory.LOCATION, "Clintonville"),
    IntentSignal("olde towne east", 25, SignalCategory.LOCATION, "OTE Columbus"),
    IntentSignal("italian village", 25, SignalCategory.LOCATION, "Italian Village"),
    IntentSignal("franklinton", 25, SignalCategory.LOCATION, "Franklinton"),
    IntentSignal("central ohio", 20, SignalCategory.LOCATION, "General region"),
    IntentSignal("franklin county", 20, SignalCategory.LOCATION, "Franklin County"),
    IntentSignal("ohio", 10, SignalCategory.LOCATION, "State mention"),

    # === LIFE EVENTS ===
    IntentSignal("getting married", 60, SignalCategory.LIFE_EVENT, "Major life change"),
    IntentSignal("engaged", 55, SignalCategory.LIFE_EVENT, "Pre-marriage"),
    IntentSignal("having a baby", 65, SignalCategory.LIFE_EVENT, "Growing family"),
    IntentSignal("pregnant", 60, SignalCategory.LIFE_EVENT, "Growing family"),
    IntentSignal("expecting", 55, SignalCategory.LIFE_EVENT, "Growing family"),
    IntentSignal("new job", 50, SignalCategory.LIFE_EVENT, "Career change"),
    IntentSignal("relocating", 70, SignalCategory.LIFE_EVENT, "Moving to area"),
    IntentSignal("moving to", 65, SignalCategory.LIFE_EVENT, "Relocation"),
    IntentSignal("transferred", 70, SignalCategory.LIFE_EVENT, "Job transfer"),
    IntentSignal("retiring", 55, SignalCategory.LIFE_EVENT, "Retirement"),
    IntentSignal("downsizing", 60, SignalCategory.LIFE_EVENT, "Lifestyle change"),
    IntentSignal("need more space", 65, SignalCategory.LIFE_EVENT, "Outgrowing current"),
    IntentSignal("outgrown", 60, SignalCategory.LIFE_EVENT, "Outgrowing current"),
    IntentSignal("divorce", 50, SignalCategory.LIFE_EVENT, "Life change"),
    IntentSignal("empty nester", 55, SignalCategory.LIFE_EVENT, "Lifestyle change"),
    IntentSignal("kids moving out", 50, SignalCategory.LIFE_EVENT, "Lifestyle change"),

    # === FINANCIAL ===
    IntentSignal("just sold", 75, SignalCategory.FINANCIAL, "Has equity"),
    IntentSignal("inheritance", 50, SignalCategory.FINANCIAL, "Capital event"),
    IntentSignal("bonus", 40, SignalCategory.FINANCIAL, "Extra funds"),
    IntentSignal("got a raise", 35, SignalCategory.FINANCIAL, "Income increase"),
    IntentSignal("pay off", 30, SignalCategory.FINANCIAL, "Debt free"),
    IntentSignal("good credit", 45, SignalCategory.FINANCIAL, "Creditworthy"),
    IntentSignal("credit score", 40, SignalCategory.FINANCIAL, "Financial awareness"),

    # === NEGATIVE SIGNALS (Competitors/Agents) ===
    IntentSignal("i'm a realtor", -100, SignalCategory.NEGATIVE, "Competitor"),
    IntentSignal("i am a realtor", -100, SignalCategory.NEGATIVE, "Competitor"),
    IntentSignal("as a realtor", -100, SignalCategory.NEGATIVE, "Competitor"),
    IntentSignal("as an agent", -100, SignalCategory.NEGATIVE, "Competitor"),
    IntentSignal("i'm an agent", -100, SignalCategory.NEGATIVE, "Competitor"),
    IntentSignal("licensed agent", -100, SignalCategory.NEGATIVE, "Competitor"),
    IntentSignal("real estate agent", -50, SignalCategory.NEGATIVE, "Possible competitor"),
    IntentSignal("keller williams", -80, SignalCategory.NEGATIVE, "Competitor brand"),
    IntentSignal("coldwell banker", -80, SignalCategory.NEGATIVE, "Competitor brand"),
    IntentSignal("remax", -80, SignalCategory.NEGATIVE, "Competitor brand"),
    IntentSignal("re/max", -80, SignalCategory.NEGATIVE, "Competitor brand"),
    IntentSignal("century 21", -80, SignalCategory.NEGATIVE, "Competitor brand"),
    IntentSignal("berkshire hathaway", -80, SignalCategory.NEGATIVE, "Competitor brand"),
    IntentSignal("exp realty", -80, SignalCategory.NEGATIVE, "Competitor brand"),
    IntentSignal("compass real estate", -80, SignalCategory.NEGATIVE, "Competitor brand"),
    IntentSignal("just browsing", -30, SignalCategory.NEGATIVE, "Low intent"),
    IntentSignal("not interested", -50, SignalCategory.NEGATIVE, "Explicit rejection"),
    IntentSignal("unsubscribe", -100, SignalCategory.NEGATIVE, "Opt out"),
]


def get_signals_by_category(category: SignalCategory) -> List[IntentSignal]:
    """Get all signals for a specific category."""
    return [s for s in INTENT_SIGNALS if s.category == category]


def get_positive_signals() -> List[IntentSignal]:
    """Get all signals with positive weights."""
    return [s for s in INTENT_SIGNALS if s.weight > 0]


def get_negative_signals() -> List[IntentSignal]:
    """Get all signals with negative weights."""
    return [s for s in INTENT_SIGNALS if s.weight < 0]
