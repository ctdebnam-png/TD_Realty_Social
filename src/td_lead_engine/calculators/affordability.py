"""Affordability calculator for home buyers."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AffordabilityResult:
    """Result of affordability calculation."""
    max_home_price: float
    comfortable_price: float
    stretched_price: float
    monthly_income: float
    monthly_debt_payments: float
    debt_to_income_ratio: float
    max_monthly_payment: float
    comfortable_monthly_payment: float
    breakdown: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class AffordabilityCalculator:
    """Calculate home affordability based on income and debt."""

    def __init__(self):
        # Standard DTI limits
        self.max_front_end_ratio = 0.28  # Housing costs / gross income
        self.max_back_end_ratio = 0.36   # All debt / gross income
        self.conservative_ratio = 0.25   # Comfortable housing ratio
        
        # Loan type DTI limits
        self.loan_limits = {
            'conventional': {'front': 0.28, 'back': 0.43},
            'fha': {'front': 0.31, 'back': 0.43},
            'va': {'front': 0.41, 'back': 0.41},
            'usda': {'front': 0.29, 'back': 0.41}
        }

    def calculate(
        self,
        annual_income: float,
        monthly_debts: float = 0,
        down_payment: float = 0,
        down_payment_percent: float = None,
        interest_rate: float = 6.75,
        loan_term_years: int = 30,
        property_tax_rate: float = 1.5,
        insurance_rate: float = 0.4,
        hoa_monthly: float = 0,
        loan_type: str = 'conventional'
    ) -> AffordabilityResult:
        """Calculate how much home a buyer can afford."""
        
        monthly_income = annual_income / 12
        
        # Get DTI limits for loan type
        limits = self.loan_limits.get(loan_type, self.loan_limits['conventional'])
        max_front_ratio = limits['front']
        max_back_ratio = limits['back']
        
        # Calculate available monthly budget for housing
        max_total_debt = monthly_income * max_back_ratio
        available_for_housing = max_total_debt - monthly_debts
        
        # Front-end check
        max_housing_front = monthly_income * max_front_ratio
        max_housing = min(available_for_housing, max_housing_front)
        
        # Conservative/comfortable budget
        comfortable_housing = monthly_income * self.conservative_ratio
        comfortable_housing = max(0, comfortable_housing - hoa_monthly)
        
        # Stretched budget (back-end ratio)
        stretched_housing = available_for_housing
        
        # Calculate max home price from monthly payment
        # Monthly payment includes PITI + HOA
        # We need to work backwards to get price
        
        max_price = self._payment_to_price(
            max_housing,
            down_payment,
            down_payment_percent or 20,
            interest_rate,
            loan_term_years,
            property_tax_rate,
            insurance_rate,
            hoa_monthly
        )
        
        comfortable_price = self._payment_to_price(
            comfortable_housing,
            down_payment,
            down_payment_percent or 20,
            interest_rate,
            loan_term_years,
            property_tax_rate,
            insurance_rate,
            hoa_monthly
        )
        
        stretched_price = self._payment_to_price(
            stretched_housing,
            down_payment,
            down_payment_percent or 20,
            interest_rate,
            loan_term_years,
            property_tax_rate,
            insurance_rate,
            hoa_monthly
        )
        
        # Calculate current DTI
        current_dti = monthly_debts / monthly_income if monthly_income > 0 else 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            monthly_income, monthly_debts, current_dti, max_price, comfortable_price
        )
        
        return AffordabilityResult(
            max_home_price=round(max_price, 0),
            comfortable_price=round(comfortable_price, 0),
            stretched_price=round(stretched_price, 0),
            monthly_income=round(monthly_income, 2),
            monthly_debt_payments=monthly_debts,
            debt_to_income_ratio=round(current_dti * 100, 1),
            max_monthly_payment=round(max_housing, 2),
            comfortable_monthly_payment=round(comfortable_housing, 2),
            breakdown={
                'gross_monthly_income': monthly_income,
                'existing_monthly_debt': monthly_debts,
                'max_housing_payment': max_housing,
                'comfortable_housing_payment': comfortable_housing,
                'front_end_limit': max_front_ratio * 100,
                'back_end_limit': max_back_ratio * 100
            },
            recommendations=recommendations
        )

    def calculate_from_payment(
        self,
        desired_monthly_payment: float,
        down_payment_percent: float = 20,
        interest_rate: float = 6.75,
        loan_term_years: int = 30,
        property_tax_rate: float = 1.5,
        insurance_rate: float = 0.4,
        hoa_monthly: float = 0
    ) -> Dict:
        """Calculate home price from desired monthly payment."""
        
        price = self._payment_to_price(
            desired_monthly_payment,
            0,
            down_payment_percent,
            interest_rate,
            loan_term_years,
            property_tax_rate,
            insurance_rate,
            hoa_monthly
        )
        
        down_payment = price * (down_payment_percent / 100)
        loan_amount = price - down_payment
        
        # Verify by calculating payment
        monthly_rate = interest_rate / 100 / 12
        num_payments = loan_term_years * 12
        
        if monthly_rate > 0:
            pi_payment = loan_amount * (
                monthly_rate * (1 + monthly_rate) ** num_payments
            ) / (
                (1 + monthly_rate) ** num_payments - 1
            )
        else:
            pi_payment = loan_amount / num_payments
        
        monthly_tax = (price * property_tax_rate / 100) / 12
        monthly_insurance = (price * insurance_rate / 100) / 12
        
        total_payment = pi_payment + monthly_tax + monthly_insurance + hoa_monthly
        
        return {
            'home_price': round(price, 0),
            'down_payment': round(down_payment, 0),
            'loan_amount': round(loan_amount, 0),
            'monthly_payment_breakdown': {
                'principal_interest': round(pi_payment, 2),
                'property_tax': round(monthly_tax, 2),
                'insurance': round(monthly_insurance, 2),
                'hoa': hoa_monthly,
                'total': round(total_payment, 2)
            }
        }

    def compare_scenarios(
        self,
        annual_income: float,
        monthly_debts: float,
        scenarios: List[Dict]
    ) -> List[Dict]:
        """Compare affordability across different scenarios."""
        results = []
        
        for scenario in scenarios:
            result = self.calculate(
                annual_income=annual_income,
                monthly_debts=monthly_debts,
                **scenario
            )
            
            scenario_result = {
                'scenario': scenario,
                'max_price': result.max_home_price,
                'comfortable_price': result.comfortable_price,
                'max_payment': result.max_monthly_payment
            }
            results.append(scenario_result)
        
        return results

    def _payment_to_price(
        self,
        max_payment: float,
        down_payment: float,
        down_payment_percent: float,
        interest_rate: float,
        loan_term_years: int,
        property_tax_rate: float,
        insurance_rate: float,
        hoa_monthly: float
    ) -> float:
        """Calculate max home price from max monthly payment."""
        
        # Remove HOA from available payment
        payment_for_piti = max_payment - hoa_monthly
        
        if payment_for_piti <= 0:
            return 0
        
        # Tax and insurance are percentage of home price
        # PI = Payment - Tax - Insurance
        # Tax = Price * tax_rate / 12
        # Insurance = Price * insurance_rate / 12
        
        # Iterative calculation
        monthly_rate = interest_rate / 100 / 12
        num_payments = loan_term_years * 12
        
        # Start with estimate
        if down_payment > 0:
            price_estimate = down_payment / (down_payment_percent / 100)
        else:
            # Rough estimate: payment * 180 (for 30-year loan at ~6.5%)
            price_estimate = payment_for_piti * 180
        
        # Iterate to find correct price
        for _ in range(20):
            # Calculate monthly tax and insurance
            monthly_tax = (price_estimate * property_tax_rate / 100) / 12
            monthly_insurance = (price_estimate * insurance_rate / 100) / 12
            
            # PI payment available
            pi_available = payment_for_piti - monthly_tax - monthly_insurance
            
            if pi_available <= 0:
                price_estimate *= 0.9
                continue
            
            # Calculate loan amount from PI payment
            if monthly_rate > 0:
                loan_amount = pi_available * (
                    (1 + monthly_rate) ** num_payments - 1
                ) / (
                    monthly_rate * (1 + monthly_rate) ** num_payments
                )
            else:
                loan_amount = pi_available * num_payments
            
            # Calculate price from loan amount
            if down_payment > 0:
                new_price = loan_amount + down_payment
            else:
                new_price = loan_amount / (1 - down_payment_percent / 100)
            
            # Check convergence
            if abs(new_price - price_estimate) < 100:
                return new_price
            
            price_estimate = (price_estimate + new_price) / 2
        
        return price_estimate

    def _generate_recommendations(
        self,
        monthly_income: float,
        monthly_debts: float,
        current_dti: float,
        max_price: float,
        comfortable_price: float
    ) -> List[str]:
        """Generate recommendations for the buyer."""
        recommendations = []
        
        # High debt ratio warning
        if current_dti > 0.30:
            recommendations.append(
                f"Your current debt-to-income ratio ({current_dti:.0%}) is high. "
                "Consider paying down debt before buying."
            )
        
        # Price gap warning
        price_gap = max_price - comfortable_price
        if price_gap > 50000:
            recommendations.append(
                f"Consider staying at or below ${comfortable_price:,.0f} for financial comfort. "
                "Stretching to the max can leave little room for emergencies."
            )
        
        # Down payment impact
        recommendations.append(
            "A larger down payment will reduce your monthly payment and "
            "may help you avoid PMI."
        )
        
        # Pre-approval suggestion
        recommendations.append(
            "Get pre-approved to know your exact budget and strengthen your offers."
        )
        
        # Emergency fund reminder
        recommendations.append(
            "Remember to keep 3-6 months of expenses in reserve after closing."
        )
        
        return recommendations
