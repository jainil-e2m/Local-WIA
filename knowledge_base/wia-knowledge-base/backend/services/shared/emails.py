"""Email address helpers shared by qualification and association."""
import re
from email.utils import getaddresses

# Subdomains count too: reply.leadlockpro.com and email.leadlockpro.com are LeadLock's own system senders.
INTERNAL_DOMAINS = {"weddingindustryads.com", "leadlockpro.com", "e2m.solutions", "e2msolutions.com"}
PUBLIC_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "msn.com",
    "icloud.com", "me.com", "mac.com", "aol.com", "protonmail.com", "proton.me", "gmx.com",
}
# Platforms whose mail is notifications, billing or marketing, never a client writing. Matched with
# subdomains (tasks.clickup.com, docs.google.com, xwf.google.com). Measured on 90 days of hello@ (30 Oct).
SYSTEM_SENDER_DOMAINS = {
    "google.com", "youtube.com", "facebookmail.com", "facebook.com", "meta.com", "instagram.com", "tiktok.com",
    "pinterest.com", "linkedin.com", "microsoft.com", "apple.com", "amazon.com", "amazonses.com",
    "clickup.com", "slack.com", "atlassian.com", "atlassian.net", "notion.so", "asana.com", "canny.io",
    "openai.com", "fathom.video", "zoom.us", "calendly.com", "loom.com", "canva.com", "zapier.com",
    "dubsado.com", "honeybook.com", "docusign.net", "typeform.com", "jotform.com", "kajabimail.net",
    "gohighlevel.com", "leadconnectorhq.com", "msgsndr.com", "hubspot.com", "mailchimp.com", "mcsv.net",
    "sendgrid.net", "mailgun.org", "klaviyo.com", "substack.com", "beehiiv.com", "circle.so",
    "squarespace.com", "wix.com", "wixsiteautomations.com", "shopify.com", "godaddy.com", "bluehost.com",
    "stripe.com", "paypal.com", "intuit.com", "payoneer.com", "theknotww.com", "weddingwire.com",
}
# Mailbox names that are never a person: no-reply, notifications, billing and the like.
_AUTOMATED_LOCAL = re.compile(r"^(no-?reply|do-?not-?reply|donotreply|notifications?|notify|mailer(-daemon)?|bounces?|"
                              r"alerts?|news(letter)?|automated|billing|receipts?|invoices?|[\w.-]*-?noreply)([+.].*)?$")

_EMAIL = re.compile(r"^[^@\s]+@([^@\s]+\.[^@\s]+)$")


def clean(address: str | None) -> str | None:
    if not address:
        return None
    address = address.strip().strip("<>").lower()
    return address if _EMAIL.match(address) else None


def domain_of(address: str | None) -> str | None:
    address = clean(address)
    return address.split("@", 1)[1] if address else None


def within(domain: str | None, roots) -> bool:
    """True when `domain` is one of `roots` or a subdomain of one."""
    return bool(domain) and any(domain == r or domain.endswith("." + r) for r in roots)


def is_internal(address: str | None) -> bool:
    return within(domain_of(address), INTERNAL_DOMAINS)


def is_platform_domain(domain: str | None) -> bool:
    return within(domain, SYSTEM_SENDER_DOMAINS)


def is_automated_sender(address: str | None) -> bool:
    """Platform notifications and role mailboxes that are never a client writing."""
    address = clean(address)
    if not address:
        return False
    local, domain = address.split("@", 1)
    return is_platform_domain(domain) or bool(_AUTOMATED_LOCAL.match(local))


def parse_header_addresses(*values: str | None) -> list[tuple[str, str]]:
    """[(display_name, email)] from RFC 5322 header values; invalid addresses dropped."""
    out = []
    for name, addr in getaddresses([v for v in values if v]):
        email = clean(addr)
        if email:
            out.append((name.strip() or "", email))
    return out
