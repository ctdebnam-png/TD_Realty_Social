"""Mortgage payment calculator."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any
import math


class LoanType(Enum):
    """Types of mortgage loans."""
    CONVENTIONAL = "conventional"
    FHA = "fha"
    VA = "va"
    USDA = "usda"
    JUMBO = "jumbo"


@dataclass
class MortgageResult:
    """Result of mortgage calculation."""
    loan_type: LoanType
    purchase_price: float
    down_payment: float
    down_payment_percent: float
    loan_amount: float
    interest_rate: float
    loan_term_years: int
    monthly_principal_interest: float
    monthly_pmi: float
    monthly_property_tax: float
    monthly_homeowners_insurance: float
    monthly_hoa: float
    total_monthly_payment: float
    total_interest_paid: float
    total_cost_of_loan: float
    amortization_schedule: List[Dict] = field(default_factory=list)


class MortgageCalculator:
    """Calculate mortgage payments and amortization."""

    def __init__(self):
        # Current average rates (would be updated from API in production)
        self.current_rates = {
            LoanType.CONVENTIONAL: {'30_year': 6.75, '15_year': 6.00},
            LoanType.FHA: {'30_year': 6.50, '15_year': 5.75},
            LoanType.VA: {'30_year': 6.25, '15_year': 5.50},
            LoanType.USDA: {'30_year': 6.50, '15_year': 5.75},
            LoanType.JUMBO: {'30_year': 7.00, '15_year': 6.25}
        }
        
        # PMI rates by down payment percentage
        self.pmi_rates = {
            (0, 5): 1.10,
            (5, 10): 0.85,
            (10, 15): 0.55,
            (15, 20): 0.35,
            (20, 100): 0.0
        }
        
        # Loan limits for 2024 (Central Ohio - Franklin County)
        self.loan_limits = {
            LoanType.CONVENTIONAL: 766550,
            LoanType.FHA: 472030,
            LoanType.VA: float('inf'),  # No limit for VA
            LoanType.USDA: 377600,
            LoanType.JUMBO: float('inf')
        }

    def calculate(
        self,
        purchase_price: float,
        down_payment: float = None,
        down_payment_percent: float = None,
        interest_rate: float = None,
        loan_term_years: int = 30,
        loan_type: LoanType = LoanType.CONVENTIONAL,
        property_tax_rate: float = 1.5,  # Annual % of home value
        insurance_annual: float = None,
        hoa_monthly: float = 0,
        include_amortization: bool = False
    ) -> MortgageResult:
        """Calculate mortgage payment details."""
        
        # Calculate down payment
        if down_payment is None and down_payment_percent is not None:
            down_payment = purchase_price * (down_payment_percent / 100)
        elif down_payment is None:
            # Default down payments by loan type
            default_down = {
                LoanType.CONVENTIONAL: 20,
                LoanType.FHA: 3.5,
                LoanType.VA: 0,
                LoanType.USDA: 0,
                LoanType.JUMBO: 20
            }
            down_payment_percent = default_down[loan_type]
            down_payment = purchase_price * (down_payment_percent / 100)
        else:
            down_payment_percent = (down_payment / purchase_price) * 100
        
        loan_amount = purchase_price - down_payment
        
        # Get interest rate
        if interest_rate is None:
            term_key = f'{loan_term_years}_year'
            if term_key in self.current_rates[loan_type]:
                interest_rate = self.current_rates[loan_type][term_key]
            else:
                interest_rate = self.current_rates[loan_type]['30_year']
        
        # Monthly interest rate
        monthly_rate = interest_rate / 100 / 12
        num_payments = loan_term_years * 12
        
        # Calculate principal & interest using amortization formula
        if monthly_rate > 0:
            monthly_pi = loan_amount * (
                monthly_rate * (1 + monthly_rate) ** num_payments
            ) / (
                (1 + monthly_rate) ** num_payments - 1
            )
        else:
            monthly_pi = loan_amount / num_payments
        
        # PMI (if applicable)
        monthly_pmi = 0
        if down_payment_percent < 20 and loan_type == LoanType.CONVENTIONAL:
            pmi_rate = self._get_pmi_rate(down_payment_percent)
            monthly_pmi = (loan_amount * pmi_rate / 100) / 12
        elif loan_type == LoanType.FHA:
            # FHA MIP
            monthly_pmi = (loan_amount * 0.85 / 100) / 12
        
        # Property tax
        monthly_tax = (purchase_price * property_tax_rate / 100) / 12
        
        # Homeowners insurance
        if insurance_annual is None:
            insurance_annual = purchase_price * 0.004  # ~0.4% of home value
        monthly_insurance = insurance_annual / 12
        
        # Total monthly payment
        total_monthly = monthly_pi + monthly_pmi + monthly_tax + monthly_insurance + hoa_monthly
        
        # Total interest over life of loan
        total_interest = (monthly_pi * num_payments) - loan_amount
        total_cost = loan_amount + total_interest
        
        # Generate amortization schedule if requested
        amortization = []
        if include_amortization:
            amortization = self._generate_amortization(
                loan_amount, monthly_rate, num_payments, monthly_pi
            )
        
        return MortgageResult(
            loan_type=loan_type,
            purchase_price=purchase_price,
            down_payment=down_payment,
            down_payment_percent=down_payment_percent,
            loan_amount=loan_amount,
            interest_rate=interest_rate,
            loan_term_years=loan_term_years,
            monthly_principal_interest=round(monthly_pi, 2),
            monthly_pmi=round(monthly_pmi, 2),
            monthly_property_tax=round(monthly_tax, 2),
            monthly_homeowners_insurance=round(monthly_insurance, 2),
            monthly_hoa=hoa_monthly,
            total_monthly_payment=round(total_monthly, 2),
            total_interest_paid=round(total_interest, 2),
            total_cost_of_loan=round(total_cost, 2),
            amortization_schedule=amortization
        )

    def compare_scenarios(
        self,
        purchase_price: float,
        scenarios: List[Dict]
    ) -> List[MortgageResult]:
        """Compare multiple mortgage scenarios."""
        results = []
        for scenario in scenarios:
            result = self.calculate(
                purchase_price=purchase_price,
                **scenario
            )
            results.append(result)
        return results

    def calculate_refinance_savings(
        self,
        current_loan_amount: float,
        current_rate: float,
        current_term_remaining: int,
        new_rate: float,
        new_term_years: int = 30,
        closing_costs: float = 0
    ) -> Dict:
        """Calculate potential refinance savings."""
        # Current payment
        current_monthly_rate = current_rate / 100 / 12
        current_payments = current_term_remaining * 12
        
        if current_monthly_rate > 0:
            current_payment = current_loan_amount * (
                current_monthly_rate * (1 + current_monthly_rate) ** current_payments
            ) / (
                (1 + current_monthly_rate) ** current_payments - 1
            )
        else:
            current_payment = current_loan_amount / current_payments
        
        # New payment
        new_monthly_rate = new_rate / 100 / 12
        new_payments = new_term_years * 12
        
        if new_monthly_rate > 0:
            new_payment = current_loan_amount * (
                new_monthly_rate * (1 + new_monthly_rate) ** new_payments
            ) / (
                (1 + new_monthly_rate) ** new_payments - 1
            )
        else:
            new_payment = current_loan_amount / new_payments
        
        monthly_savings = current_payment - new_payment
        total_current_cost = current_payment * current_payments
        total_new_cost = (new_payment * new_payments) + closing_costs
        total_savings = total_current_cost - total_new_cost
        
        breakeven_months = closing_costs / monthly_savings if monthly_savings > 0 else float('inf')
        
        return {
            'current_payment': round(current_payment, 2),
            'new_payment': round(new_payment, 2),
            'monthly_savings': round(monthly_savings, 2),
            'total_savings': round(total_savings, 2),
            'closing_costs': closing_costs,
            'breakeven_months': round(breakeven_months, 1),
            'worth_refinancing': monthly_savings > 100 and breakeven_months < 36
        }

    def get_current_rates(self) -> Dict[str, float]:
        """Get current interest rates."""
        rates = {}
        for loan_type, terms in self.current_rates.items():
            for term, rate in terms.items():
                rates[f'{loan_type.value}_{term}'] = rate
        return rates

    def _get_pmi_rate(self, down_payment_percent: float) -> float:
        """Get PMI rate based on down payment percentage."""
        for (low, high), rate in self.pmi_rates.items():
            if low <= down_payment_percent < high:
                return rate
        return 0.0

    def _generate_amortization(
        self,
        loan_amount: float,
        monthly_rate: float,
        num_payments: int,
        monthly_payment: float
    ) -> List[Dict]:
        """Generate amortization schedule."""
        schedule = []
        balance = loan_amount
        total_interest = 0
        total_principal = 0
        
        for month in range(1, num_payments + 1):
            interest_payment = balance * monthly_rate
            principal_payment = monthly_payment - interest_payment
            balance -= principal_payment
            
            total_interest += interest_payment
            total_principal += principal_payment
            
            schedule.append({
                'month': month,
                'payment': round(monthly_payment, 2),
                'principal': round(principal_payment, 2),
                'interest': round(interest_payment, 2),
                'balance': round(max(0, balance), 2),
                'total_interest': round(total_interest, 2),
                'total_principal': round(total_principal, 2)
            })
        
        return schedule
