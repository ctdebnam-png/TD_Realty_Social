"""Closing cost calculator for buyers and sellers."""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum


class TransactionType(Enum):
    """Type of transaction."""
    PURCHASE = "purchase"
    SALE = "sale"


@dataclass
class CostItem:
    """A single closing cost item."""
    name: str
    amount: float
    category: str
    description: str = ""
    is_estimate: bool = True
    can_shop: bool = False


@dataclass
class ClosingCostEstimate:
    """Complete closing cost estimate."""
    transaction_type: TransactionType
    property_price: float
    items: List[CostItem]
    total_costs: float
    cash_needed: float  # For buyers: down payment + closing costs
    net_proceeds: float  # For sellers: sale price - costs
    breakdown_by_category: Dict[str, float] = field(default_factory=dict)


class ClosingCostCalculator:
    """Calculate closing costs for buyers and sellers."""

    def __init__(self, state: str = "OH"):
        self.state = state
        
        # Ohio-specific rates and fees
        self.ohio_rates = {
            'transfer_tax_rate': 0.001,  # $1 per $1,000 (state)
            'conveyance_fee': 0.004,     # $4 per $1,000 (county)
            'title_insurance_rate': 0.005,
            'recording_fee_deed': 50,
            'recording_fee_mortgage': 75,
        }

    def calculate_buyer_costs(
        self,
        purchase_price: float,
        down_payment: float = None,
        down_payment_percent: float = 20,
        loan_type: str = "conventional",
        is_first_home: bool = False,
        property_type: str = "single_family",
        hoa_transfer_fee: float = 0
    ) -> ClosingCostEstimate:
        """Calculate closing costs for a buyer."""
        items = []
        
        # Calculate down payment if not provided
        if down_payment is None:
            down_payment = purchase_price * (down_payment_percent / 100)
        
        loan_amount = purchase_price - down_payment
        
        # === LENDER FEES ===
        
        # Origination fee (0.5-1% of loan)
        origination = loan_amount * 0.01
        items.append(CostItem(
            name="Loan Origination Fee",
            amount=origination,
            category="Lender Fees",
            description="Fee charged by lender to process the loan",
            can_shop=True
        ))
        
        # Discount points (optional, typically 0-2 points)
        # Not including by default
        
        # Appraisal fee
        items.append(CostItem(
            name="Appraisal Fee",
            amount=500,
            category="Lender Fees",
            description="Required property appraisal",
            can_shop=True
        ))
        
        # Credit report fee
        items.append(CostItem(
            name="Credit Report Fee",
            amount=50,
            category="Lender Fees"
        ))
        
        # Underwriting fee
        items.append(CostItem(
            name="Underwriting Fee",
            amount=400,
            category="Lender Fees",
            description="Lender's processing fee"
        ))
        
        # Flood certification
        items.append(CostItem(
            name="Flood Certification",
            amount=25,
            category="Lender Fees"
        ))
        
        # Tax service fee
        items.append(CostItem(
            name="Tax Service Fee",
            amount=75,
            category="Lender Fees"
        ))
        
        # === TITLE FEES ===
        
        # Title search
        items.append(CostItem(
            name="Title Search",
            amount=300,
            category="Title Fees",
            description="Search for liens and ownership history",
            can_shop=True
        ))
        
        # Owner's title insurance
        title_insurance = purchase_price * self.ohio_rates['title_insurance_rate']
        items.append(CostItem(
            name="Owner's Title Insurance",
            amount=title_insurance,
            category="Title Fees",
            description="Protects buyer against title defects",
            can_shop=True
        ))
        
        # Lender's title insurance
        lender_title = loan_amount * 0.003
        items.append(CostItem(
            name="Lender's Title Insurance",
            amount=lender_title,
            category="Title Fees",
            description="Required by lender"
        ))
        
        # Settlement/closing fee
        items.append(CostItem(
            name="Settlement/Closing Fee",
            amount=450,
            category="Title Fees",
            can_shop=True
        ))
        
        # === GOVERNMENT FEES ===
        
        # Recording fees
        items.append(CostItem(
            name="Recording Fees",
            amount=self.ohio_rates['recording_fee_mortgage'] + 50,
            category="Government Fees",
            description="County recording of deed and mortgage"
        ))
        
        # Transfer tax (buyer typically doesn't pay in Ohio, but including for awareness)
        # Ohio: seller typically pays transfer tax
        
        # === PREPAID ITEMS ===
        
        # Property tax prepaid (typically 2-6 months)
        monthly_tax = (purchase_price * 0.015) / 12  # ~1.5% annual
        prepaid_tax = monthly_tax * 4
        items.append(CostItem(
            name="Property Tax Prepaid",
            amount=prepaid_tax,
            category="Prepaid Items",
            description="4 months of property tax"
        ))
        
        # Homeowners insurance prepaid (12 months)
        annual_insurance = purchase_price * 0.004
        items.append(CostItem(
            name="Homeowners Insurance (12 mo)",
            amount=annual_insurance,
            category="Prepaid Items",
            description="First year of homeowners insurance"
        ))
        
        # Prepaid interest (varies by closing date)
        daily_interest = (loan_amount * 0.0675) / 365
        prepaid_interest = daily_interest * 15  # Assume 15 days
        items.append(CostItem(
            name="Prepaid Interest",
            amount=prepaid_interest,
            category="Prepaid Items",
            description="Interest from closing to first payment"
        ))
        
        # === ESCROW ===
        
        # Property tax escrow (2 months)
        items.append(CostItem(
            name="Property Tax Escrow",
            amount=monthly_tax * 2,
            category="Escrow",
            description="Initial escrow deposit for taxes"
        ))
        
        # Insurance escrow (2 months)
        items.append(CostItem(
            name="Insurance Escrow",
            amount=(annual_insurance / 12) * 2,
            category="Escrow",
            description="Initial escrow deposit for insurance"
        ))
        
        # === OTHER ===
        
        # Home inspection (optional but recommended)
        items.append(CostItem(
            name="Home Inspection",
            amount=400,
            category="Other",
            description="Professional home inspection",
            is_estimate=True
        ))
        
        # HOA transfer fee if applicable
        if hoa_transfer_fee > 0:
            items.append(CostItem(
                name="HOA Transfer Fee",
                amount=hoa_transfer_fee,
                category="Other"
            ))
        
        # Survey (if required)
        items.append(CostItem(
            name="Survey",
            amount=350,
            category="Other",
            description="Property survey if required",
            is_estimate=True
        ))
        
        # Calculate totals
        total_costs = sum(item.amount for item in items)
        cash_needed = down_payment + total_costs
        
        # Breakdown by category
        breakdown = {}
        for item in items:
            breakdown[item.category] = breakdown.get(item.category, 0) + item.amount
        
        return ClosingCostEstimate(
            transaction_type=TransactionType.PURCHASE,
            property_price=purchase_price,
            items=items,
            total_costs=round(total_costs, 2),
            cash_needed=round(cash_needed, 2),
            net_proceeds=0,  # N/A for buyers
            breakdown_by_category=breakdown
        )

    def calculate_seller_costs(
        self,
        sale_price: float,
        remaining_mortgage: float = 0,
        listing_commission_percent: float = 3.0,
        buyer_agent_commission_percent: float = 3.0,
        home_warranty: bool = False,
        hoa_fees_due: float = 0,
        repairs_credit: float = 0
    ) -> ClosingCostEstimate:
        """Calculate closing costs for a seller."""
        items = []
        
        # === REAL ESTATE COMMISSIONS ===
        
        listing_commission = sale_price * (listing_commission_percent / 100)
        items.append(CostItem(
            name="Listing Agent Commission",
            amount=listing_commission,
            category="Commissions",
            description=f"{listing_commission_percent}% to listing agent"
        ))
        
        buyer_commission = sale_price * (buyer_agent_commission_percent / 100)
        items.append(CostItem(
            name="Buyer's Agent Commission",
            amount=buyer_commission,
            category="Commissions",
            description=f"{buyer_agent_commission_percent}% to buyer's agent"
        ))
        
        # === TAXES AND GOVERNMENT FEES ===
        
        # Ohio transfer tax (seller pays)
        transfer_tax = sale_price * self.ohio_rates['transfer_tax_rate']
        items.append(CostItem(
            name="State Transfer Tax",
            amount=transfer_tax,
            category="Taxes & Government",
            description="Ohio real estate transfer tax"
        ))
        
        # County conveyance fee
        conveyance_fee = sale_price * self.ohio_rates['conveyance_fee']
        items.append(CostItem(
            name="County Conveyance Fee",
            amount=conveyance_fee,
            category="Taxes & Government",
            description="County recording fee"
        ))
        
        # Recording fee for deed
        items.append(CostItem(
            name="Deed Recording Fee",
            amount=self.ohio_rates['recording_fee_deed'],
            category="Taxes & Government"
        ))
        
        # Prorated property taxes (if due)
        monthly_tax = (sale_price * 0.015) / 12
        prorated_tax = monthly_tax * 6  # Estimate 6 months proration
        items.append(CostItem(
            name="Prorated Property Taxes",
            amount=prorated_tax,
            category="Taxes & Government",
            description="Property tax proration to closing",
            is_estimate=True
        ))
        
        # === TITLE FEES ===
        
        # Title insurance (owner's policy often paid by seller in Ohio)
        title_insurance = sale_price * self.ohio_rates['title_insurance_rate']
        items.append(CostItem(
            name="Owner's Title Insurance",
            amount=title_insurance,
            category="Title Fees",
            description="Title insurance for buyer"
        ))
        
        # Settlement fee
        items.append(CostItem(
            name="Settlement Fee",
            amount=400,
            category="Title Fees"
        ))
        
        # === PAYOFFS ===
        
        if remaining_mortgage > 0:
            items.append(CostItem(
                name="Mortgage Payoff",
                amount=remaining_mortgage,
                category="Payoffs",
                description="Existing mortgage balance"
            ))
        
        # === OTHER ===
        
        if home_warranty:
            items.append(CostItem(
                name="Home Warranty",
                amount=500,
                category="Other",
                description="Home warranty for buyer"
            ))
        
        if hoa_fees_due > 0:
            items.append(CostItem(
                name="HOA Fees Due",
                amount=hoa_fees_due,
                category="Other"
            ))
        
        if repairs_credit > 0:
            items.append(CostItem(
                name="Repair Credits to Buyer",
                amount=repairs_credit,
                category="Other",
                description="Negotiated repair credits"
            ))
        
        # Calculate totals
        total_costs = sum(item.amount for item in items)
        net_proceeds = sale_price - total_costs
        
        # Breakdown by category
        breakdown = {}
        for item in items:
            breakdown[item.category] = breakdown.get(item.category, 0) + item.amount
        
        return ClosingCostEstimate(
            transaction_type=TransactionType.SALE,
            property_price=sale_price,
            items=items,
            total_costs=round(total_costs, 2),
            cash_needed=0,  # N/A for sellers
            net_proceeds=round(net_proceeds, 2),
            breakdown_by_category=breakdown
        )

    def get_cost_summary(self, estimate: ClosingCostEstimate) -> Dict:
        """Get a simplified summary of closing costs."""
        shoppable_items = [item for item in estimate.items if item.can_shop]
        
        return {
            'transaction_type': estimate.transaction_type.value,
            'property_price': estimate.property_price,
            'total_closing_costs': estimate.total_costs,
            'cost_percentage': round((estimate.total_costs / estimate.property_price) * 100, 2),
            'cash_needed': estimate.cash_needed,
            'net_proceeds': estimate.net_proceeds,
            'breakdown': estimate.breakdown_by_category,
            'shoppable_items': [
                {'name': item.name, 'amount': item.amount}
                for item in shoppable_items
            ],
            'potential_savings': sum(item.amount * 0.1 for item in shoppable_items)  # ~10% savings potential
        }
