"""Investment property analysis calculator."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class InvestmentAnalysis:
    """Result of investment property analysis."""
    purchase_price: float
    down_payment: float
    loan_amount: float
    
    # Income
    monthly_rent: float
    annual_gross_income: float
    effective_gross_income: float
    
    # Expenses
    monthly_expenses: float
    annual_expenses: float
    
    # Cash flow
    monthly_cash_flow: float
    annual_cash_flow: float
    
    # Returns
    cap_rate: float
    cash_on_cash_return: float
    roi_year_1: float
    
    # Ratios
    gross_rent_multiplier: float
    debt_service_coverage: float
    
    # Projections
    year_5_equity: float
    year_5_total_return: float
    
    expense_breakdown: Dict[str, float] = field(default_factory=dict)
    monthly_breakdown: Dict[str, float] = field(default_factory=dict)


class InvestmentCalculator:
    """Calculate investment property returns and metrics."""

    def __init__(self):
        # Default assumptions
        self.default_vacancy_rate = 0.05  # 5%
        self.default_maintenance_rate = 0.10  # 10% of rent
        self.default_management_rate = 0.08  # 8% of rent
        self.default_appreciation_rate = 0.03  # 3% annual
        self.default_rent_growth_rate = 0.02  # 2% annual

    def analyze(
        self,
        purchase_price: float,
        monthly_rent: float,
        down_payment_percent: float = 25,
        interest_rate: float = 7.0,
        loan_term_years: int = 30,
        property_tax_rate: float = 1.5,
        insurance_annual: float = None,
        vacancy_rate: float = None,
        maintenance_rate: float = None,
        management_rate: float = None,
        hoa_monthly: float = 0,
        other_monthly_expenses: float = 0,
        closing_costs: float = None,
        repair_reserve: float = None
    ) -> InvestmentAnalysis:
        """Analyze an investment property."""
        
        # Calculate financing
        down_payment = purchase_price * (down_payment_percent / 100)
        loan_amount = purchase_price - down_payment
        
        # Closing costs (estimate if not provided)
        if closing_costs is None:
            closing_costs = purchase_price * 0.03  # 3% estimate
        
        total_investment = down_payment + closing_costs + (repair_reserve or 0)
        
        # Calculate mortgage payment
        monthly_rate = interest_rate / 100 / 12
        num_payments = loan_term_years * 12
        
        if monthly_rate > 0:
            monthly_mortgage = loan_amount * (
                monthly_rate * (1 + monthly_rate) ** num_payments
            ) / (
                (1 + monthly_rate) ** num_payments - 1
            )
        else:
            monthly_mortgage = loan_amount / num_payments
        
        # Income calculations
        annual_gross_income = monthly_rent * 12
        vacancy = vacancy_rate if vacancy_rate is not None else self.default_vacancy_rate
        effective_gross_income = annual_gross_income * (1 - vacancy)
        
        # Expense calculations
        maintenance = maintenance_rate if maintenance_rate is not None else self.default_maintenance_rate
        management = management_rate if management_rate is not None else self.default_management_rate
        
        monthly_property_tax = (purchase_price * property_tax_rate / 100) / 12
        
        if insurance_annual is None:
            insurance_annual = purchase_price * 0.005  # 0.5% estimate
        monthly_insurance = insurance_annual / 12
        
        monthly_maintenance = monthly_rent * maintenance
        monthly_management = monthly_rent * management
        monthly_vacancy_reserve = monthly_rent * vacancy
        
        monthly_expenses = (
            monthly_mortgage +
            monthly_property_tax +
            monthly_insurance +
            monthly_maintenance +
            monthly_management +
            hoa_monthly +
            other_monthly_expenses
        )
        
        annual_expenses = monthly_expenses * 12
        
        # Operating expenses (excluding mortgage)
        monthly_operating = monthly_expenses - monthly_mortgage
        annual_operating = monthly_operating * 12
        noi = effective_gross_income - annual_operating  # Net Operating Income
        
        # Cash flow
        monthly_cash_flow = monthly_rent - monthly_expenses - monthly_vacancy_reserve
        annual_cash_flow = monthly_cash_flow * 12
        
        # Key metrics
        cap_rate = (noi / purchase_price) * 100 if purchase_price > 0 else 0
        cash_on_cash = (annual_cash_flow / total_investment) * 100 if total_investment > 0 else 0
        
        # First year ROI including principal paydown
        first_year_principal = self._calculate_principal_paydown(
            loan_amount, monthly_rate, num_payments, 1
        )
        first_year_appreciation = purchase_price * self.default_appreciation_rate
        roi_year_1 = (
            (annual_cash_flow + first_year_principal + first_year_appreciation) /
            total_investment * 100
        ) if total_investment > 0 else 0
        
        # Gross Rent Multiplier
        grm = purchase_price / annual_gross_income if annual_gross_income > 0 else 0
        
        # Debt Service Coverage Ratio
        annual_debt_service = monthly_mortgage * 12
        dscr = noi / annual_debt_service if annual_debt_service > 0 else 0
        
        # 5-year projections
        year_5_equity, year_5_return = self._project_5_year(
            purchase_price, loan_amount, monthly_rate, num_payments,
            annual_cash_flow, total_investment
        )
        
        return InvestmentAnalysis(
            purchase_price=purchase_price,
            down_payment=round(down_payment, 2),
            loan_amount=round(loan_amount, 2),
            monthly_rent=monthly_rent,
            annual_gross_income=round(annual_gross_income, 2),
            effective_gross_income=round(effective_gross_income, 2),
            monthly_expenses=round(monthly_expenses, 2),
            annual_expenses=round(annual_expenses, 2),
            monthly_cash_flow=round(monthly_cash_flow, 2),
            annual_cash_flow=round(annual_cash_flow, 2),
            cap_rate=round(cap_rate, 2),
            cash_on_cash_return=round(cash_on_cash, 2),
            roi_year_1=round(roi_year_1, 2),
            gross_rent_multiplier=round(grm, 2),
            debt_service_coverage=round(dscr, 2),
            year_5_equity=round(year_5_equity, 0),
            year_5_total_return=round(year_5_return, 2),
            expense_breakdown={
                'mortgage': round(monthly_mortgage, 2),
                'property_tax': round(monthly_property_tax, 2),
                'insurance': round(monthly_insurance, 2),
                'maintenance': round(monthly_maintenance, 2),
                'management': round(monthly_management, 2),
                'hoa': hoa_monthly,
                'vacancy_reserve': round(monthly_vacancy_reserve, 2),
                'other': other_monthly_expenses
            },
            monthly_breakdown={
                'gross_rent': monthly_rent,
                'vacancy_loss': round(-monthly_vacancy_reserve, 2),
                'effective_income': round(monthly_rent - monthly_vacancy_reserve, 2),
                'total_expenses': round(-monthly_expenses, 2),
                'net_cash_flow': round(monthly_cash_flow, 2)
            }
        )

    def calculate_rent_needed(
        self,
        purchase_price: float,
        desired_cash_flow: float,
        down_payment_percent: float = 25,
        interest_rate: float = 7.0,
        loan_term_years: int = 30,
        property_tax_rate: float = 1.5,
        vacancy_rate: float = 0.05,
        expense_ratio: float = 0.40
    ) -> Dict:
        """Calculate rent needed for desired cash flow."""
        
        down_payment = purchase_price * (down_payment_percent / 100)
        loan_amount = purchase_price - down_payment
        
        monthly_rate = interest_rate / 100 / 12
        num_payments = loan_term_years * 12
        
        if monthly_rate > 0:
            monthly_mortgage = loan_amount * (
                monthly_rate * (1 + monthly_rate) ** num_payments
            ) / (
                (1 + monthly_rate) ** num_payments - 1
            )
        else:
            monthly_mortgage = loan_amount / num_payments
        
        monthly_tax = (purchase_price * property_tax_rate / 100) / 12
        monthly_insurance = (purchase_price * 0.005) / 12
        
        # Fixed costs
        fixed_costs = monthly_mortgage + monthly_tax + monthly_insurance
        
        # Rent needed = (Fixed + Cash Flow) / (1 - Variable% - Vacancy%)
        variable_rate = expense_ratio - (monthly_tax + monthly_insurance) / (purchase_price * 0.01)
        variable_rate = max(0.15, min(0.30, variable_rate))  # Reasonable bounds
        
        rent_needed = (fixed_costs + desired_cash_flow) / (1 - variable_rate - vacancy_rate)
        
        return {
            'rent_needed': round(rent_needed, 0),
            'with_vacancy': round(rent_needed * (1 - vacancy_rate), 0),
            'mortgage_payment': round(monthly_mortgage, 2),
            'fixed_costs': round(fixed_costs, 2),
            'rent_to_price_ratio': round((rent_needed / purchase_price) * 100, 3)
        }

    def compare_properties(
        self,
        properties: List[Dict]
    ) -> List[Dict]:
        """Compare multiple investment properties."""
        results = []
        
        for prop in properties:
            analysis = self.analyze(**prop)
            
            results.append({
                'name': prop.get('name', 'Property'),
                'purchase_price': analysis.purchase_price,
                'monthly_rent': analysis.monthly_rent,
                'monthly_cash_flow': analysis.monthly_cash_flow,
                'cap_rate': analysis.cap_rate,
                'cash_on_cash': analysis.cash_on_cash_return,
                'dscr': analysis.debt_service_coverage,
                'year_5_equity': analysis.year_5_equity,
                'score': self._calculate_investment_score(analysis)
            })
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results

    def _calculate_principal_paydown(
        self,
        loan_amount: float,
        monthly_rate: float,
        num_payments: int,
        years: int
    ) -> float:
        """Calculate principal paid down over N years."""
        if monthly_rate == 0:
            return loan_amount * years / (num_payments / 12)
        
        monthly_payment = loan_amount * (
            monthly_rate * (1 + monthly_rate) ** num_payments
        ) / (
            (1 + monthly_rate) ** num_payments - 1
        )
        
        balance = loan_amount
        total_principal = 0
        
        for month in range(years * 12):
            interest = balance * monthly_rate
            principal = monthly_payment - interest
            total_principal += principal
            balance -= principal
        
        return total_principal

    def _project_5_year(
        self,
        purchase_price: float,
        loan_amount: float,
        monthly_rate: float,
        num_payments: int,
        annual_cash_flow: float,
        initial_investment: float
    ) -> tuple:
        """Project 5-year equity and return."""
        
        # Appreciation
        year_5_value = purchase_price * (1 + self.default_appreciation_rate) ** 5
        
        # Principal paydown
        principal_paid = self._calculate_principal_paydown(
            loan_amount, monthly_rate, num_payments, 5
        )
        
        # Remaining balance
        year_5_balance = loan_amount - principal_paid
        
        # Equity
        year_5_equity = year_5_value - year_5_balance
        
        # Total cash flow (with growth)
        total_cash_flow = 0
        cf = annual_cash_flow
        for year in range(5):
            total_cash_flow += cf
            cf *= (1 + self.default_rent_growth_rate)
        
        # Total return
        appreciation_gain = year_5_value - purchase_price
        total_return = (
            (total_cash_flow + appreciation_gain + principal_paid) /
            initial_investment * 100
        ) if initial_investment > 0 else 0
        
        return year_5_equity, total_return

    def _calculate_investment_score(self, analysis: InvestmentAnalysis) -> float:
        """Calculate overall investment score (0-100)."""
        score = 0
        
        # Cap rate (up to 25 points)
        if analysis.cap_rate >= 10:
            score += 25
        elif analysis.cap_rate >= 8:
            score += 20
        elif analysis.cap_rate >= 6:
            score += 15
        elif analysis.cap_rate >= 4:
            score += 10
        else:
            score += 5
        
        # Cash on cash (up to 25 points)
        if analysis.cash_on_cash_return >= 15:
            score += 25
        elif analysis.cash_on_cash_return >= 10:
            score += 20
        elif analysis.cash_on_cash_return >= 8:
            score += 15
        elif analysis.cash_on_cash_return >= 5:
            score += 10
        else:
            score += 5
        
        # Cash flow (up to 25 points)
        if analysis.monthly_cash_flow >= 500:
            score += 25
        elif analysis.monthly_cash_flow >= 300:
            score += 20
        elif analysis.monthly_cash_flow >= 200:
            score += 15
        elif analysis.monthly_cash_flow >= 100:
            score += 10
        elif analysis.monthly_cash_flow > 0:
            score += 5
        
        # DSCR (up to 25 points)
        if analysis.debt_service_coverage >= 1.5:
            score += 25
        elif analysis.debt_service_coverage >= 1.3:
            score += 20
        elif analysis.debt_service_coverage >= 1.2:
            score += 15
        elif analysis.debt_service_coverage >= 1.1:
            score += 10
        elif analysis.debt_service_coverage >= 1.0:
            score += 5
        
        return score
