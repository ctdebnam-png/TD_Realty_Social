"""Net sheet calculators for buyers and sellers."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SellerNetSheet:
    """Seller net sheet calculation result."""
    sale_price: float
    existing_mortgage: float
    total_closing_costs: float
    net_proceeds: float
    line_items: List[Dict] = field(default_factory=list)


@dataclass
class BuyerNetSheet:
    """Buyer net sheet/funds needed calculation."""
    purchase_price: float
    down_payment: float
    total_closing_costs: float
    total_funds_needed: float
    credits: float
    net_funds_needed: float
    line_items: List[Dict] = field(default_factory=list)


class NetSheetCalculator:
    """Calculate net proceeds for sellers and funds needed for buyers."""

    def calculate_seller_net(
        self,
        sale_price: float,
        existing_mortgage: float = 0,
        second_mortgage: float = 0,
        home_equity_line: float = 0,
        other_liens: float = 0,
        listing_commission_pct: float = 3.0,
        buyer_agent_commission_pct: float = 3.0,
        transfer_tax_rate: float = 0.005,
        title_insurance_rate: float = 0.005,
        prorated_taxes: float = 0,
        hoa_dues: float = 0,
        repairs_concessions: float = 0,
        home_warranty: float = 0,
        other_costs: float = 0,
        other_credits: float = 0
    ) -> SellerNetSheet:
        """Calculate seller's net proceeds."""
        line_items = []
        
        # CREDITS (Positive)
        line_items.append({
            'category': 'Sale',
            'description': 'Sale Price',
            'credit': sale_price,
            'debit': 0
        })
        
        if other_credits > 0:
            line_items.append({
                'category': 'Credits',
                'description': 'Other Credits',
                'credit': other_credits,
                'debit': 0
            })
        
        total_credits = sale_price + other_credits
        
        # DEBITS (Negative)
        
        # Payoffs
        if existing_mortgage > 0:
            line_items.append({
                'category': 'Payoffs',
                'description': 'First Mortgage Payoff',
                'credit': 0,
                'debit': existing_mortgage
            })
        
        if second_mortgage > 0:
            line_items.append({
                'category': 'Payoffs',
                'description': 'Second Mortgage Payoff',
                'credit': 0,
                'debit': second_mortgage
            })
        
        if home_equity_line > 0:
            line_items.append({
                'category': 'Payoffs',
                'description': 'Home Equity Line Payoff',
                'credit': 0,
                'debit': home_equity_line
            })
        
        if other_liens > 0:
            line_items.append({
                'category': 'Payoffs',
                'description': 'Other Liens',
                'credit': 0,
                'debit': other_liens
            })
        
        # Commissions
        listing_commission = sale_price * (listing_commission_pct / 100)
        line_items.append({
            'category': 'Commissions',
            'description': f'Listing Agent ({listing_commission_pct}%)',
            'credit': 0,
            'debit': listing_commission
        })
        
        buyer_commission = sale_price * (buyer_agent_commission_pct / 100)
        line_items.append({
            'category': 'Commissions',
            'description': f"Buyer's Agent ({buyer_agent_commission_pct}%)",
            'credit': 0,
            'debit': buyer_commission
        })
        
        # Title & Escrow
        title_insurance = sale_price * title_insurance_rate
        line_items.append({
            'category': 'Title & Escrow',
            'description': "Owner's Title Insurance",
            'credit': 0,
            'debit': title_insurance
        })
        
        line_items.append({
            'category': 'Title & Escrow',
            'description': 'Escrow/Settlement Fee',
            'credit': 0,
            'debit': 400
        })
        
        # Government
        transfer_tax = sale_price * transfer_tax_rate
        line_items.append({
            'category': 'Government',
            'description': 'Transfer Tax/Conveyance Fee',
            'credit': 0,
            'debit': transfer_tax
        })
        
        line_items.append({
            'category': 'Government',
            'description': 'Recording Fees',
            'credit': 0,
            'debit': 50
        })
        
        if prorated_taxes > 0:
            line_items.append({
                'category': 'Government',
                'description': 'Prorated Property Taxes',
                'credit': 0,
                'debit': prorated_taxes
            })
        
        # Other
        if hoa_dues > 0:
            line_items.append({
                'category': 'Other',
                'description': 'HOA Dues/Transfer Fee',
                'credit': 0,
                'debit': hoa_dues
            })
        
        if repairs_concessions > 0:
            line_items.append({
                'category': 'Other',
                'description': 'Repairs/Concessions',
                'credit': 0,
                'debit': repairs_concessions
            })
        
        if home_warranty > 0:
            line_items.append({
                'category': 'Other',
                'description': 'Home Warranty',
                'credit': 0,
                'debit': home_warranty
            })
        
        if other_costs > 0:
            line_items.append({
                'category': 'Other',
                'description': 'Other Costs',
                'credit': 0,
                'debit': other_costs
            })
        
        # Calculate totals
        total_debits = sum(item['debit'] for item in line_items)
        total_closing_costs = total_debits - (existing_mortgage + second_mortgage + 
                                               home_equity_line + other_liens)
        net_proceeds = total_credits - total_debits
        
        return SellerNetSheet(
            sale_price=sale_price,
            existing_mortgage=existing_mortgage + second_mortgage + home_equity_line + other_liens,
            total_closing_costs=round(total_closing_costs, 2),
            net_proceeds=round(net_proceeds, 2),
            line_items=line_items
        )

    def calculate_buyer_funds(
        self,
        purchase_price: float,
        down_payment_pct: float = 20,
        loan_origination_fee: float = None,
        appraisal_fee: float = 500,
        credit_report: float = 50,
        title_insurance: float = None,
        escrow_fee: float = 450,
        recording_fees: float = 125,
        prepaid_taxes_months: int = 4,
        prepaid_insurance_months: int = 12,
        escrow_taxes_months: int = 2,
        escrow_insurance_months: int = 2,
        property_tax_rate: float = 0.015,
        annual_insurance: float = None,
        home_inspection: float = 400,
        survey: float = 350,
        hoa_transfer: float = 0,
        seller_credits: float = 0,
        earnest_money: float = None
    ) -> BuyerNetSheet:
        """Calculate buyer's total funds needed."""
        line_items = []
        
        down_payment = purchase_price * (down_payment_pct / 100)
        loan_amount = purchase_price - down_payment
        
        # Down Payment
        line_items.append({
            'category': 'Down Payment',
            'description': f'Down Payment ({down_payment_pct}%)',
            'amount': down_payment
        })
        
        # Lender Fees
        origination = loan_origination_fee if loan_origination_fee else loan_amount * 0.01
        line_items.append({
            'category': 'Lender Fees',
            'description': 'Loan Origination (1%)',
            'amount': origination
        })
        
        line_items.append({
            'category': 'Lender Fees',
            'description': 'Appraisal Fee',
            'amount': appraisal_fee
        })
        
        line_items.append({
            'category': 'Lender Fees',
            'description': 'Credit Report',
            'amount': credit_report
        })
        
        line_items.append({
            'category': 'Lender Fees',
            'description': 'Underwriting Fee',
            'amount': 400
        })
        
        # Title & Escrow
        title_cost = title_insurance if title_insurance else purchase_price * 0.005
        line_items.append({
            'category': 'Title & Escrow',
            'description': "Owner's Title Insurance",
            'amount': title_cost
        })
        
        line_items.append({
            'category': 'Title & Escrow',
            'description': "Lender's Title Insurance",
            'amount': loan_amount * 0.003
        })
        
        line_items.append({
            'category': 'Title & Escrow',
            'description': 'Title Search',
            'amount': 300
        })
        
        line_items.append({
            'category': 'Title & Escrow',
            'description': 'Settlement/Escrow Fee',
            'amount': escrow_fee
        })
        
        # Government Fees
        line_items.append({
            'category': 'Government',
            'description': 'Recording Fees',
            'amount': recording_fees
        })
        
        # Prepaids
        monthly_tax = (purchase_price * property_tax_rate) / 12
        annual_ins = annual_insurance if annual_insurance else purchase_price * 0.004
        monthly_ins = annual_ins / 12
        
        line_items.append({
            'category': 'Prepaids',
            'description': f'Property Tax ({prepaid_taxes_months} months)',
            'amount': monthly_tax * prepaid_taxes_months
        })
        
        line_items.append({
            'category': 'Prepaids',
            'description': f'Homeowners Insurance ({prepaid_insurance_months} months)',
            'amount': annual_ins
        })
        
        # Assume 15 days prepaid interest
        daily_interest = (loan_amount * 0.0675) / 365
        line_items.append({
            'category': 'Prepaids',
            'description': 'Prepaid Interest (15 days)',
            'amount': daily_interest * 15
        })
        
        # Escrow
        line_items.append({
            'category': 'Escrow',
            'description': f'Tax Escrow ({escrow_taxes_months} months)',
            'amount': monthly_tax * escrow_taxes_months
        })
        
        line_items.append({
            'category': 'Escrow',
            'description': f'Insurance Escrow ({escrow_insurance_months} months)',
            'amount': monthly_ins * escrow_insurance_months
        })
        
        # Other
        line_items.append({
            'category': 'Other',
            'description': 'Home Inspection',
            'amount': home_inspection
        })
        
        line_items.append({
            'category': 'Other',
            'description': 'Survey',
            'amount': survey
        })
        
        if hoa_transfer > 0:
            line_items.append({
                'category': 'Other',
                'description': 'HOA Transfer Fee',
                'amount': hoa_transfer
            })
        
        # Calculate totals
        total_funds = sum(item['amount'] for item in line_items)
        closing_costs = total_funds - down_payment
        
        # Credits
        credits = seller_credits
        earnest = earnest_money if earnest_money else purchase_price * 0.01
        
        line_items.append({
            'category': 'Credits',
            'description': 'Earnest Money Deposit (already paid)',
            'amount': -earnest
        })
        
        if seller_credits > 0:
            line_items.append({
                'category': 'Credits',
                'description': 'Seller Credits',
                'amount': -seller_credits
            })
        
        net_funds = total_funds - earnest - seller_credits
        
        return BuyerNetSheet(
            purchase_price=purchase_price,
            down_payment=round(down_payment, 2),
            total_closing_costs=round(closing_costs, 2),
            total_funds_needed=round(total_funds, 2),
            credits=round(earnest + seller_credits, 2),
            net_funds_needed=round(net_funds, 2),
            line_items=line_items
        )

    def format_net_sheet(self, result) -> str:
        """Format net sheet for display."""
        lines = []
        
        if isinstance(result, SellerNetSheet):
            lines.append("=" * 50)
            lines.append("SELLER NET SHEET")
            lines.append("=" * 50)
            lines.append(f"Sale Price: ${result.sale_price:,.2f}")
            lines.append("-" * 50)
            
            current_category = None
            for item in result.line_items:
                if item['category'] != current_category:
                    current_category = item['category']
                    lines.append(f"\n{current_category.upper()}")
                
                if item['credit'] > 0:
                    lines.append(f"  {item['description']:<35} +${item['credit']:>12,.2f}")
                else:
                    lines.append(f"  {item['description']:<35} -${item['debit']:>12,.2f}")
            
            lines.append("-" * 50)
            lines.append(f"{'ESTIMATED NET PROCEEDS:':<35} ${result.net_proceeds:>12,.2f}")
            lines.append("=" * 50)
        
        else:  # BuyerNetSheet
            lines.append("=" * 50)
            lines.append("BUYER FUNDS NEEDED")
            lines.append("=" * 50)
            lines.append(f"Purchase Price: ${result.purchase_price:,.2f}")
            lines.append("-" * 50)
            
            current_category = None
            for item in result.line_items:
                if item['category'] != current_category:
                    current_category = item['category']
                    lines.append(f"\n{current_category.upper()}")
                
                if item['amount'] >= 0:
                    lines.append(f"  {item['description']:<35} ${item['amount']:>12,.2f}")
                else:
                    lines.append(f"  {item['description']:<35} (${abs(item['amount']):>10,.2f})")
            
            lines.append("-" * 50)
            lines.append(f"{'TOTAL FUNDS NEEDED:':<35} ${result.net_funds_needed:>12,.2f}")
            lines.append("=" * 50)
        
        return "\n".join(lines)
