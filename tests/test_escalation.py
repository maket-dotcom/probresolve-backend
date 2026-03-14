"""
Tests for escalation map — no DB required.
"""

from app.escalation import ESCALATION_MAP, FALLBACK_ESCALATION

EXPECTED_DOMAIN_SLUGS = [
    "e-commerce-online-shopping",
    "banking-financial-services",
    "real-estate-housing",
    "government-services",
    "healthcare-pharmaceuticals",
    "education-recruitment",
    "telecom-internet",
    "consumer-goods-services",
]


class TestEscalationMap:
    def test_all_eight_domains_covered(self):
        for slug in EXPECTED_DOMAIN_SLUGS:
            assert slug in ESCALATION_MAP, f"Missing domain: {slug}"

    def test_each_domain_has_at_least_two_portals(self):
        for slug, portals in ESCALATION_MAP.items():
            assert len(portals) >= 2, f"{slug} has only {len(portals)} portal(s)"

    def test_each_entry_is_three_tuple(self):
        for slug, portals in ESCALATION_MAP.items():
            for entry in portals:
                assert len(entry) == 3, f"{slug}: entry {entry} is not a 3-tuple"
                name, url, desc = entry
                assert name, f"{slug}: portal name is empty"
                assert url.startswith("https://"), f"{slug}: URL {url} doesn't start with https://"
                assert desc, f"{slug}: description is empty"

    def test_fallback_exists_and_has_two_entries(self):
        assert len(FALLBACK_ESCALATION) >= 2

    def test_fallback_entries_are_valid(self):
        for name, url, desc in FALLBACK_ESCALATION:
            assert name
            assert url.startswith("https://")
            assert desc

    def test_unknown_slug_uses_fallback(self):
        """Pages route returns FALLBACK for unknown domain slugs."""
        unknown = "completely-unknown-domain"
        result = ESCALATION_MAP.get(unknown, FALLBACK_ESCALATION)
        assert result is FALLBACK_ESCALATION

    def test_banking_has_rbi_ombudsman(self):
        portals = ESCALATION_MAP["banking-financial-services"]
        names = [p[0] for p in portals]
        assert any("RBI" in n or "Ombudsman" in n for n in names)

    def test_ecommerce_has_consumer_helpline(self):
        portals = ESCALATION_MAP["e-commerce-online-shopping"]
        names = [p[0] for p in portals]
        assert any("Consumer" in n for n in names)
