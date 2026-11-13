"""Discovery contact filters (30 Oct): automated and platform senders, internal subdomains, admin sender
rules, partners serving several clients, direct correspondents only, and pre-tick defaults."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
import yaml
from sqlalchemy import select

from backend.db import transaction
from backend.models.db import ConnectorAccount, Contact
from backend.models.domain.intake import BusinessHint, ContactCandidate, DiscoveryResult
from backend.services.clients import mapping
from backend.services.intake import discovery
from backend.services.intake.adapters.gmail import GmailAdapter
from backend.services.shared.emails import is_automated_sender, is_internal


@pytest.mark.parametrize("addr", ["notifications@tasks.clickup.com", "rep@xwf.google.com", "comments-noreply@docs.google.com",
                                  "no-reply@squarespace.com", "service@paypal.com", "billing@somevenue.com",
                                  "ads-account-noreply@ads.google.com", "info@e.atlassian.com"])
def test_automated_senders(addr):
    assert is_automated_sender(addr)


@pytest.mark.parametrize("addr", ["owner@venue-example.com", "info@weddings-example.co", "hello@thevenue-example.com",
                                  "events@thehall-example.com", "someone@gmail.com"])
def test_people_are_not_automated(addr):
    assert not is_automated_sender(addr)


def test_internal_includes_subdomains():
    assert is_internal("hello@reply.leadlockpro.com") and is_internal("x@email.leadlockpro.com")
    assert not is_internal("hello@leadlockpro.com.example.org")


def _c(business, email=None, domain=None, evidence="gmail: 1 direct message(s)"):
    return ContactCandidate(business, email, domain, None, evidence)


def test_filter_removes_ruled_senders_and_holds_back_partners():
    a, b, c = uuid4(), uuid4(), uuid4()
    rules = mapping.SenderRules([SimpleNamespace(email="me@ownbiz.com", domain=None, kind="team"),
                                 SimpleNamespace(email=None, domain="agency.com", kind="partner")])
    results = {
        "calendar": DiscoveryResult(contacts=[_c(a, "coach@consult.com", evidence="calendar: attendee of 'A call'")]),
        "gmail": DiscoveryResult(contacts=[
            _c(b, "coach@consult.com"), _c(c, "coach@consult.com"),  # 3 clients overall -> partner
            _c(a, "me@ownbiz.com"), _c(a, "ami@agency.com"),  # team / partner rule
            _c(a, "x@tasks.clickup.com"), _c(a, "hello@reply.leadlockpro.com"),  # platform / internal
            _c(a, "owner@venue-a.com"),
            _c(a, "shared@vendor.com"), _c(b, "shared@vendor.com"),  # two clients: kept, never pre-ticked
        ]),
    }
    partners = discovery.filter_contacts(results, rules)
    assert set(partners) == {"@consult.com"} and partners["@consult.com"] == {a, b, c}
    assert results["calendar"].contacts == []
    left = {(x.email, x.business_id): x.evidence for x in results["gmail"].contacts}
    assert set(left) == {("owner@venue-a.com", a), ("shared@vendor.com", a), ("shared@vendor.com", b)}
    assert "also proposed for another client" in left[("shared@vendor.com", a)]


def test_one_client_discovery_does_not_guess_partners():
    a = uuid4()
    results = {"gmail": DiscoveryResult(contacts=[_c(a, "owner@venue-a.com")])}
    assert discovery.filter_contacts(results, mapping.SenderRules([]), detect_partners=False) == {}
    assert len(results["gmail"].contacts) == 1


def _msg(frm, to, cc="", extra=(), labels=()):
    headers = [{"name": "From", "value": frm}, {"name": "To", "value": to}, {"name": "Cc", "value": cc}, *extra]
    return {"payload": {"headers": headers}, "labelIds": list(labels)}


def test_gmail_proposes_direct_correspondents_only(monkeypatch):
    me = "hello@weddingindustryads.com"
    msgs = {
        "1": _msg("Owner <owner@venueone.com>", me, cc="Planner <planner@planners.com>"),  # they wrote to us
        "2": _msg(me, "coordinator@venueone.com"),  # we wrote to them
        "3": _msg("news@bigvendor.com", me, extra=[{"name": "List-Unsubscribe", "value": "<mailto:x>"}]),  # bulk
        "4": _msg("promo@shop.com", me, labels=["CATEGORY_PROMOTIONS"]),  # promotions tab
        "5": _msg("someone@other.com", "friend@else.com"),  # neither side is the mailbox
    }
    a = GmailAdapter.__new__(GmailAdapter)
    monkeypatch.setattr(a, "identify", lambda: SimpleNamespace(provider_account_id=me, display_identity=me), raising=False)
    monkeypatch.setattr(a, "_search", lambda q: list(msgs), raising=False)
    monkeypatch.setattr(a, "_get", lambda path, params=None: msgs[path.split("/")[1]], raising=False)
    hint = BusinessHint(uuid4(), "Venue One", ("Venue One",))
    found = {(c.email, c.domain) for c in a.discover([hint], None, None).contacts}
    assert found == {("owner@venueone.com", None), ("coordinator@venueone.com", None), (None, "venueone.com")}


@pytest.fixture
def venue():
    with transaction() as s:
        s.add(ConnectorAccount(id=uuid4(), provider="gmail", provider_account_id="hello@x.com",
                               expected_identity="hello@x.com", credential_ref="X"))
        return mapping.create_client(s, name="Venue One", slug="venue-one", actor="a", discover=False).id


def test_full_run_clears_stale_suggestions_but_keeps_decisions(venue, monkeypatch):
    with transaction() as s:
        s.add_all([Contact(id=uuid4(), business_id=venue, email="old@stale.com", status="candidate", origin="discovery"),
                   Contact(id=uuid4(), business_id=venue, email="kept@venueone.com", status="approved", origin="manual"),
                   Contact(id=uuid4(), business_id=venue, email="no@thanks.com", status="rejected", origin="discovery")])

    class Fake:
        def discover(self, hints, start, end):
            return DiscoveryResult(contacts=[_c(venue, "new@venueone.com"), _c(venue, "x@tasks.clickup.com")])

    monkeypatch.setattr(discovery, "get_adapter", lambda provider: Fake())
    discovery.run_discovery(["gmail"], 30, reset=True)
    with transaction() as s:
        assert {(c.email, c.status) for c in s.execute(select(Contact)).scalars()} == {
            ("kept@venueone.com", "approved"), ("no@thanks.com", "rejected"), ("new@venueone.com", "candidate")}


def test_domain_is_pre_ticked_only_when_it_carries_the_client_name(venue, monkeypatch, tmp_path):
    class Fake:
        def discover(self, hints, start, end):
            return DiscoveryResult(contacts=[_c(venue, domain="venueone.com", evidence="gmail: domain matches client name (2 address(es))"),
                                             _c(venue, domain="someagency.com", evidence="gmail: 2 address(es) at this domain")])

    monkeypatch.setattr(discovery, "get_adapter", lambda provider: Fake())
    results = discovery.run_discovery(["gmail"], 30)
    _, approval = discovery.write_proposal(results, tmp_path)
    ticks = {r["domain"]: r["approve"] for r in yaml.safe_load(approval.read_text(encoding="utf-8"))["contacts"]}
    assert ticks == {"venueone.com": True, "someagency.com": False}


def test_sender_rules_refuse_public_domains_and_flag_approved_conflicts(venue):
    with transaction() as s:
        with pytest.raises(mapping.MappingError):
            mapping.add_sender_rule(s, "team", actor="a", reason="x", domain="gmail.com")
        mapping.add_contact(s, venue, actor="a", email="tina.personal@gmail.com")
        mapping.add_sender_rule(s, "team", actor="a", reason="Tina's personal address", email="tina.personal@gmail.com")
        mapping.add_sender_rule(s, "partner", actor="a", reason="web agency", domain="@agency.com")
        assert mapping.sender_rules(s).kind_of("ami@agency.com") == "partner"
        assert [(c.email, why) for c, why in mapping.contact_conflicts(s)] == [("tina.personal@gmail.com", "team sender rule")]


def test_partner_linked_to_a_client_stays_but_never_decides_association(venue):
    from backend.services.intake.scoping import live_contacts
    with transaction() as s:
        mapping.add_contact(s, venue, actor="a", email="coach@consult.com")
        mapping.add_contact(s, venue, actor="a", domain="venueone.com")
        mapping.add_sender_rule(s, "partner", actor="a", reason="consultant for one client, refers many", domain="consult.com")
    with transaction() as s:
        assert {(c.email, c.domain) for c in live_contacts(s)} == {(None, "venueone.com")}
        assert mapping.contact_conflicts(s) == []  # a link, not a conflict
        assert mapping.partner_links(s) == {"@consult.com": ["venue-one"]}
