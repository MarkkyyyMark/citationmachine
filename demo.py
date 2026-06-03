"""Quick visual check of the citation engine. Run: python demo.py"""

from datetime import date

from citation_engine import Citation, format_citation

card = Citation(
    url="https://www.csis.org/analysis/new-executive-order-ties-us-critical-minerals-security-global-partnerships",
    quote=(
        "During President Trump's second term, critical minerals have emerged "
        "as a prominent element of U.S. foreign policy."
    ),
    authors=["Gracelin Baskaran"],
    qualifications=(
        "Dr. Gracelin Baskaran is director of the Critical Minerals Security "
        "Program at the Center for Strategic and International Studies (CSIS)"
    ),
    title="New Executive Order Ties U.S. Critical Minerals Security to Global Partnerships",
    pub_date=date(2026, 1, 15),
    access_date=date(2026, 1, 20),
)

print(format_citation(card))
