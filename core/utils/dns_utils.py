"""
DNS utilities for domain verification.

Provides:
  - TXT record lookup via dnspython
  - SPF, DKIM, DMARC verification helpers
  - RSA DKIM key pair generation via cryptography

Place: core/utils/dns_utils.py
"""

import base64
import logging

import dns.resolver
import dns.exception
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# ── Key generation ────────────────────────────────────────────────────────────

def generate_dkim_keypair() -> tuple[str, str]:
    """
    Generate a 2048-bit RSA key pair for DKIM signing.

    Returns:
        (private_key_pem: str, public_key_base64: str)

    The public_key_base64 goes into the DNS TXT record as the `p=` value.
    The private_key_pem is stored (encrypted at rest) and used to sign outgoing mail.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_b64 = base64.b64encode(public_der).decode("utf-8")

    return private_pem, public_b64


# ── DNS lookup ────────────────────────────────────────────────────────────────

def get_txt_records(hostname: str) -> list[str]:
    """
    Query DNS TXT records for `hostname`.
    Returns a list of record strings (concatenated if multi-part).
    Returns [] on NXDOMAIN / timeout / any resolver error.
    """
    try:
        answers = dns.resolver.resolve(hostname, "TXT", lifetime=10)
        records = []
        for rdata in answers:
            # Each TXT record may have multiple strings – join them
            value = "".join(s.decode("utf-8") for s in rdata.strings)
            records.append(value)
        return records
    except dns.resolver.NXDOMAIN:
        logger.debug("DNS NXDOMAIN for %s", hostname)
        return []
    except dns.resolver.NoAnswer:
        logger.debug("DNS NoAnswer for %s", hostname)
        return []
    except dns.exception.Timeout:
        logger.warning("DNS timeout querying %s", hostname)
        return []
    except Exception as exc:
        logger.warning("DNS error querying %s: %s", hostname, exc)
        return []


# ── SPF verification ──────────────────────────────────────────────────────────

SPF_INCLUDE = "include:spf.mailflow.io"

def verify_spf(domain: str) -> tuple[bool, str]:
    """
    Check that the domain's TXT record contains the expected SPF include.

    Returns:
        (verified: bool, detail: str)
    """
    records = get_txt_records(domain)
    spf_records = [r for r in records if r.startswith("v=spf1")]

    if not spf_records:
        return False, "No SPF record found on the domain."

    for rec in spf_records:
        if SPF_INCLUDE in rec:
            return True, f"SPF record found and valid: {rec}"

    return False, (
        f"SPF record found but missing '{SPF_INCLUDE}'. "
        f"Current record: {spf_records[0]}"
    )


# ── DKIM verification ─────────────────────────────────────────────────────────

def verify_dkim(domain: str, selector: str, expected_public_key: str) -> tuple[bool, str]:
    """
    Check that the DKIM TXT record at `<selector>._domainkey.<domain>`
    contains a `p=` value matching `expected_public_key`.

    Returns:
        (verified: bool, detail: str)
    """
    hostname = f"{selector}._domainkey.{domain}"
    records  = get_txt_records(hostname)

    if not records:
        return False, f"No DKIM TXT record found at {hostname}."

    for rec in records:
        if "v=DKIM1" in rec:
            # Extract p= value (may be split across tags)
            p_value = _extract_dkim_p(rec)
            if not p_value:
                return False, f"DKIM record found at {hostname} but has no p= value."
            # Normalise whitespace before comparing
            if _normalise_key(p_value) == _normalise_key(expected_public_key):
                return True, f"DKIM record verified at {hostname}."
            return False, (
                f"DKIM record found at {hostname} but p= value does not match. "
                "Check that the record was published correctly."
            )

    return False, f"No valid DKIM record (v=DKIM1) found at {hostname}."


def _extract_dkim_p(record: str) -> str:
    """Extract the p= value from a DKIM TXT record string."""
    for part in record.split(";"):
        part = part.strip()
        if part.startswith("p="):
            return part[2:].strip()
    return ""


def _normalise_key(key: str) -> str:
    """Remove whitespace and newlines for comparison."""
    return "".join(key.split())


# ── DMARC verification ────────────────────────────────────────────────────────

def verify_dmarc(domain: str) -> tuple[bool, str]:
    """
    Check that a DMARC TXT record exists at `_dmarc.<domain>`
    with at least `v=DMARC1` and a `p=` policy.

    Returns:
        (verified: bool, detail: str)
    """
    hostname = f"_dmarc.{domain}"
    records  = get_txt_records(hostname)

    if not records:
        return False, f"No DMARC record found at {hostname}."

    for rec in records:
        if rec.startswith("v=DMARC1"):
            if "p=" in rec:
                return True, f"DMARC record found and valid: {rec}"
            return False, "DMARC record found but missing policy (p=)."

    return False, f"No valid DMARC record (v=DMARC1) found at {hostname}."


# ── Convenience: verify all three at once ────────────────────────────────────

class DomainVerificationResult:
    """Container for the results of a full domain verification check."""
    __slots__ = [
        "spf_ok", "spf_detail",
        "dkim_ok", "dkim_detail",
        "dmarc_ok", "dmarc_detail",
    ]

    def __init__(self, spf, dkim, dmarc):
        self.spf_ok,  self.spf_detail  = spf
        self.dkim_ok, self.dkim_detail  = dkim
        self.dmarc_ok, self.dmarc_detail = dmarc

    @property
    def all_ok(self) -> bool:
        return self.spf_ok and self.dkim_ok and self.dmarc_ok

    def as_dict(self) -> dict:
        return {
            "spf":   {"verified": self.spf_ok,   "detail": self.spf_detail},
            "dkim":  {"verified": self.dkim_ok,  "detail": self.dkim_detail},
            "dmarc": {"verified": self.dmarc_ok, "detail": self.dmarc_detail},
            "all_verified": self.all_ok,
        }


def verify_domain_all(
    domain: str, selector: str, expected_public_key: str
) -> DomainVerificationResult:
    """Run SPF, DKIM, and DMARC checks and return a single result object."""
    return DomainVerificationResult(
        spf=verify_spf(domain),
        dkim=verify_dkim(domain, selector, expected_public_key),
        dmarc=verify_dmarc(domain),
    )