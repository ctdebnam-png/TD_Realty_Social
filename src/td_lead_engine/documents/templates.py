"""Document templates for real estate transactions."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from string import Template

logger = logging.getLogger(__name__)


@dataclass
class ContractTemplate:
    """Contract template definition."""

    id: str
    name: str
    template_type: str  # "listing", "buyer_agency", "purchase", "addendum", etc.
    content: str  # Template content with ${variable} placeholders
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    version: str = "1.0"
    state: str = "OH"  # State-specific forms


class DocumentTemplates:
    """Generate documents from templates."""

    def __init__(self):
        """Initialize templates."""
        self.templates: Dict[str, ContractTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """Load default Ohio real estate templates."""

        # Buyer Agency Agreement
        self.templates["buyer_agency"] = ContractTemplate(
            id="buyer_agency_oh",
            name="Ohio Exclusive Buyer Agency Agreement",
            template_type="buyer_agency",
            required_fields=["buyer_name", "buyer_address", "agent_name", "broker_name",
                           "commission_rate", "start_date", "end_date"],
            optional_fields=["specific_properties", "geographic_area", "property_types"],
            content="""
EXCLUSIVE BUYER AGENCY AGREEMENT
State of Ohio

This Agreement is entered into on ${start_date} between:

BUYER(S): ${buyer_name}
Address: ${buyer_address}
Phone: ${buyer_phone}
Email: ${buyer_email}

and

AGENT: ${agent_name}
Broker: ${broker_name}
Address: ${broker_address}
Phone: ${agent_phone}

1. AGENCY RELATIONSHIP
Buyer hereby employs Agent as Buyer's exclusive agent for the purpose of locating
and negotiating the purchase or lease of real property.

2. TERM
This agreement shall begin on ${start_date} and end on ${end_date}, unless extended
by written agreement of the parties.

3. PROPERTY DESCRIPTION
Type of Property: ${property_types}
Geographic Area: ${geographic_area}
Price Range: ${price_range}

4. COMPENSATION
Buyer agrees that Agent shall receive compensation equal to ${commission_rate}% of
the purchase price. This compensation may be paid by the seller, the listing broker,
or the buyer.

5. BUYER'S DUTIES
Buyer agrees to:
- Work exclusively with Agent during the term of this agreement
- Provide accurate financial information
- Notify Agent of any properties of interest
- Be available for property showings

6. AGENT'S DUTIES
Agent agrees to:
- Act in Buyer's best interest
- Maintain confidentiality
- Present all offers and counteroffers
- Disclose material facts
- Provide professional guidance

7. DUAL AGENCY DISCLOSURE
Buyer acknowledges that situations may arise where Agent represents both buyer and
seller in the same transaction. In such cases, written consent will be required.

SIGNATURES:

______________________________ Date: __________
Buyer: ${buyer_name}

______________________________ Date: __________
Buyer: ${buyer_name_2}

______________________________ Date: __________
Agent: ${agent_name}
"""
        )

        # Listing Agreement
        self.templates["listing_agreement"] = ContractTemplate(
            id="listing_agreement_oh",
            name="Ohio Exclusive Right to Sell Listing Agreement",
            template_type="listing",
            required_fields=["seller_name", "property_address", "list_price", "agent_name",
                           "broker_name", "commission_rate", "start_date", "end_date"],
            content="""
EXCLUSIVE RIGHT TO SELL LISTING AGREEMENT
State of Ohio

This Agreement is entered into on ${start_date} between:

SELLER(S): ${seller_name}
Property Address: ${property_address}
City: ${city}, State: ${state}, ZIP: ${zip_code}

and

AGENT: ${agent_name}
Broker: ${broker_name}
Office Address: ${broker_address}

1. GRANT OF AUTHORITY
Seller grants Agent the exclusive right to sell the above-described property.

2. TERM
This agreement begins on ${start_date} and expires on ${end_date}.

3. LIST PRICE
The property shall be offered at an initial list price of $${list_price}.

4. COMPENSATION
Seller agrees to pay a commission of ${commission_rate}% of the final sale price.
Commission is earned when:
- A ready, willing, and able buyer is procured
- The property is sold during the listing period
- The property is sold within ${protection_period} days after expiration to someone
  introduced during the listing period

5. MARKETING
Agent agrees to:
- List property on MLS within ${mls_days} days
- Provide professional photography
- Market property on major real estate websites
- Conduct open houses as agreed
- Provide regular activity reports

6. SELLER'S REPRESENTATIONS
Seller represents that:
- Seller has authority to sell the property
- All information provided is accurate
- Property will be maintained in current condition
- All known defects have been disclosed

7. PROPERTY CONDITION
Included items: ${inclusions}
Excluded items: ${exclusions}

8. FAIR HOUSING
This property will be shown and sold in compliance with all fair housing laws.

SIGNATURES:

______________________________ Date: __________
Seller: ${seller_name}

______________________________ Date: __________
Seller: ${seller_name_2}

______________________________ Date: __________
Agent: ${agent_name}
"""
        )

        # Purchase Agreement
        self.templates["purchase_agreement"] = ContractTemplate(
            id="purchase_agreement_oh",
            name="Ohio Residential Purchase Agreement",
            template_type="purchase",
            required_fields=["buyer_name", "seller_name", "property_address", "purchase_price",
                           "earnest_money", "closing_date"],
            content="""
RESIDENTIAL PURCHASE AGREEMENT
State of Ohio

Date: ${offer_date}

1. PARTIES
BUYER(S): ${buyer_name}
Address: ${buyer_address}

SELLER(S): ${seller_name}

2. PROPERTY
Address: ${property_address}
City: ${city}, County: ${county}, State: OH, ZIP: ${zip_code}
Legal Description: ${legal_description}
Parcel Number: ${parcel_number}

3. PURCHASE PRICE AND TERMS
Purchase Price: $${purchase_price}
Earnest Money Deposit: $${earnest_money}
   To be held by: ${escrow_holder}
Down Payment: $${down_payment}
Loan Amount: $${loan_amount}
Balance at Closing: $${balance_at_closing}

4. FINANCING
Type of Financing: ${financing_type}
   [ ] Conventional  [ ] FHA  [ ] VA  [ ] Cash  [ ] Other: ________
Loan Term: ${loan_term} years
Interest Rate: Not to exceed ${max_interest_rate}%

5. CONTINGENCIES
A. Financing Contingency: ${financing_contingency_days} days
B. Inspection Contingency: ${inspection_days} days
C. Appraisal Contingency: Property must appraise at purchase price
D. Sale of Buyer's Property: ${sale_contingency}

6. CLOSING
Closing Date: ${closing_date}
Possession Date: ${possession_date}
Closing Location: ${closing_location}

7. INSPECTIONS
Buyer shall have ${inspection_days} days to conduct inspections including:
- General home inspection
- Radon testing
- Pest inspection
- Other: ${other_inspections}

8. TITLE
Seller shall provide marketable title, free of liens and encumbrances except:
${title_exceptions}

9. PROPERTY CONDITION
A. Seller agrees to maintain property in current condition
B. All systems shall be in working order at closing
C. Seller shall complete the following repairs: ${required_repairs}

10. INCLUSIONS AND EXCLUSIONS
Included: ${inclusions}
Excluded: ${exclusions}

11. DISCLOSURES
Seller has provided or will provide:
- Residential Property Disclosure Form
- Lead-Based Paint Disclosure (if built before 1978)
- Other: ${other_disclosures}

12. ADDITIONAL TERMS
${additional_terms}

13. ACCEPTANCE
This offer shall expire if not accepted by ${expiration_date} at ${expiration_time}.

SIGNATURES:

BUYER:
______________________________ Date: __________ Time: __________
${buyer_name}

______________________________ Date: __________ Time: __________
${buyer_name_2}

SELLER:
______________________________ Date: __________ Time: __________
${seller_name}

______________________________ Date: __________ Time: __________
${seller_name_2}
"""
        )

        # Counter Offer
        self.templates["counter_offer"] = ContractTemplate(
            id="counter_offer_oh",
            name="Counter Offer",
            template_type="counter_offer",
            required_fields=["original_offer_date", "property_address", "counter_items"],
            content="""
COUNTER OFFER

Date: ${counter_date}

Reference: Purchase Agreement dated ${original_offer_date}
Property: ${property_address}

The undersigned Seller(s) hereby makes the following counter offer to Buyer(s):

ORIGINAL TERMS MODIFIED:
${counter_items}

All other terms and conditions of the original Purchase Agreement dated
${original_offer_date} remain in full force and effect.

This Counter Offer shall expire if not accepted by ${expiration_date} at
${expiration_time}.

______________________________ Date: __________ Time: __________
Seller: ${seller_name}

ACCEPTANCE:
The undersigned Buyer(s) hereby accepts the above Counter Offer.

______________________________ Date: __________ Time: __________
Buyer: ${buyer_name}
"""
        )

        # Inspection Response
        self.templates["inspection_response"] = ContractTemplate(
            id="inspection_response_oh",
            name="Buyer's Inspection Response",
            template_type="inspection_response",
            required_fields=["property_address", "inspection_date", "response_type"],
            content="""
BUYER'S INSPECTION RESPONSE

Date: ${response_date}

Property: ${property_address}
Inspection Date: ${inspection_date}
Inspector: ${inspector_name}

Pursuant to the inspection contingency in the Purchase Agreement, Buyer hereby:

[ ] ACCEPTS the property in its current condition, waiving the inspection contingency.

[ ] REQUESTS the following repairs be completed by Seller prior to closing:
${repair_requests}

[ ] REQUESTS a credit of $${credit_amount} at closing in lieu of repairs.

[ ] TERMINATES the Purchase Agreement due to unsatisfactory inspection results.
    Earnest money shall be returned to Buyer.

Seller shall respond to this request within ${response_days} days.

______________________________ Date: __________
Buyer: ${buyer_name}

SELLER'S RESPONSE:

[ ] ACCEPTS Buyer's requests as stated above.

[ ] AGREES to the following repairs/credits:
${seller_response}

[ ] DECLINES to make repairs. Buyer may accept property as-is or terminate.

______________________________ Date: __________
Seller: ${seller_name}
"""
        )

        # Seller Disclosure
        self.templates["seller_disclosure"] = ContractTemplate(
            id="seller_disclosure_oh",
            name="Ohio Residential Property Disclosure Form",
            template_type="disclosure",
            required_fields=["property_address", "seller_name"],
            content="""
OHIO RESIDENTIAL PROPERTY DISCLOSURE FORM

Property Address: ${property_address}
Seller(s): ${seller_name}
Date: ${disclosure_date}

INSTRUCTIONS: Seller must disclose all known material facts about the property.

1. WATER SUPPLY
   Source: [ ] Public [ ] Private Well [ ] Other: ________
   Known problems: ${water_problems}

2. SEWAGE SYSTEM
   Type: [ ] Public Sewer [ ] Septic [ ] Other: ________
   Last pumped/inspected: ${septic_date}
   Known problems: ${sewage_problems}

3. ROOF
   Age: ${roof_age} years
   Known leaks or problems: ${roof_problems}

4. BASEMENT/FOUNDATION
   Water intrusion: [ ] Yes [ ] No
   Structural issues: [ ] Yes [ ] No
   Details: ${basement_problems}

5. HVAC SYSTEMS
   Heating type: ${heating_type}, Age: ${heating_age}
   Cooling type: ${cooling_type}, Age: ${cooling_age}
   Known problems: ${hvac_problems}

6. ELECTRICAL
   Service amps: ${electrical_amps}
   Known problems: ${electrical_problems}

7. PLUMBING
   Known problems: ${plumbing_problems}

8. ENVIRONMENTAL
   Known presence of:
   [ ] Lead paint  [ ] Asbestos  [ ] Radon  [ ] Mold  [ ] Underground tanks
   Details: ${environmental_issues}

9. PEST/TERMITE
   Known infestations: ${pest_issues}
   Treatment history: ${pest_treatment}

10. ADDITIONS/IMPROVEMENTS
    Made without permits: ${unpermitted_work}

11. OTHER KNOWN DEFECTS
${other_defects}

12. ADDITIONAL COMMENTS
${additional_comments}

SELLER CERTIFICATION:
The information contained in this disclosure is true and accurate to the best of
my knowledge as of the date signed.

______________________________ Date: __________
Seller: ${seller_name}

______________________________ Date: __________
Seller: ${seller_name_2}

BUYER ACKNOWLEDGMENT:
Buyer acknowledges receipt of this disclosure.

______________________________ Date: __________
Buyer: ${buyer_name}
"""
        )

    def get_template(self, template_id: str) -> Optional[ContractTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)

    def list_templates(self) -> List[Dict[str, str]]:
        """List available templates."""
        return [
            {
                "id": t.id,
                "name": t.name,
                "type": t.template_type,
                "state": t.state
            }
            for t in self.templates.values()
        ]

    def generate_document(
        self,
        template_id: str,
        variables: Dict[str, Any]
    ) -> Optional[str]:
        """Generate a document from a template."""
        template = self.templates.get(template_id)

        if not template:
            logger.error(f"Template not found: {template_id}")
            return None

        # Check required fields
        missing = [f for f in template.required_fields if f not in variables]
        if missing:
            logger.warning(f"Missing required fields: {missing}")

        # Set defaults for missing optional fields
        for field in template.optional_fields:
            if field not in variables:
                variables[field] = ""

        # Fill common defaults
        variables.setdefault("state", "OH")
        variables.setdefault("date", datetime.now().strftime("%B %d, %Y"))

        try:
            # Use safe substitution to handle missing variables
            tmpl = Template(template.content)
            return tmpl.safe_substitute(variables)
        except Exception as e:
            logger.error(f"Error generating document: {e}")
            return None

    def validate_fields(self, template_id: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that all required fields are provided."""
        template = self.templates.get(template_id)

        if not template:
            return {"valid": False, "error": "Template not found"}

        missing = [f for f in template.required_fields if f not in variables or not variables[f]]
        empty_optional = [f for f in template.optional_fields if f not in variables]

        return {
            "valid": len(missing) == 0,
            "missing_required": missing,
            "missing_optional": empty_optional,
            "all_fields": template.required_fields + template.optional_fields
        }

    def add_custom_template(
        self,
        template_id: str,
        name: str,
        template_type: str,
        content: str,
        required_fields: List[str],
        optional_fields: List[str] = None
    ):
        """Add a custom template."""
        self.templates[template_id] = ContractTemplate(
            id=template_id,
            name=name,
            template_type=template_type,
            content=content,
            required_fields=required_fields,
            optional_fields=optional_fields or []
        )
