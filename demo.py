"""Quick visual check of the citation engine. Run: python demo.py"""

from datetime import date

from citation_engine import Citation, format_citation, format_citation_html

baskaran = Citation(
    url="https://www.csis.org/analysis/new-executive-order-ties-us-critical-minerals-security-global-partnerships",
    quote=(
        "During President Trump's second term, critical minerals have emerged "
        "as a prominent element of U.S. foreign policy."
    ),
    authors=["Gracelin Baskaran"],
    short_credential="Director of the Critical Minerals Security Program at CSIS",
    qualifications=(
        "Dr. Gracelin Baskaran is director of the Critical Minerals Security "
        "Program at the Center for Strategic and International Studies (CSIS)"
    ),
    title="New Executive Order Ties U.S. Critical Minerals Security to Global Partnerships",
    publication="CSIS",
    pub_date=date(2026, 1, 15),
    access_date=date(2026, 1, 20),
)

print("=== PLAIN TEXT ===")
print(format_citation(baskaran))
print()
print("=== HTML (pastes into Google Docs with the lead bold) ===")
print(format_citation_html(baskaran))
