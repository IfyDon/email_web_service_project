"""
Domain service — business logic layer between views/tasks and the Domain model.

Responsibilities:
  - Add a domain (generate DKIM keys, save, return DNS instructions)
  - Trigger a DNS verification check (called by API view and Celery task)
  - Sync verification status back to the model

Place: services/domain_service.py
"""

import logging
from django.utils import timezone

from apps.domains.models import Domain
from core.utils.dns_utils import generate_dkim_keypair, verify_domain_all
from apps.authentication.models import AuditLog

logger = logging.getLogger(__name__)


# ── Add domain ────────────────────────────────────────────────────────────────

def add_domain(user, name: str) -> Domain:
    """
    Register a new sending domain for `user`.

    Steps:
      1. Validate the name is not already registered.
      2. Generate a DKIM RSA key pair.
      3. Persist the Domain record.
      4. Log the action.

    Returns the newly created Domain.
    Raises ValueError if the domain already exists.
    """
    name = name.strip().lower().rstrip(".")

    if Domain.objects.filter(name=name).exists():
        raise ValueError(f"Domain '{name}' is already registered.")

    private_pem, public_b64 = generate_dkim_keypair()

    domain = Domain.objects.create(
        user=user,
        name=name,
        dkim_private_key=private_pem,
        dkim_public_key=public_b64,
    )

    AuditLog.record(
        AuditLog.Action.DOMAIN_ADDED,
        user=user,
        domain=name,
    )

    logger.info("Domain '%s' registered for user %s", name, user.email)
    return domain


# ── Verify domain ─────────────────────────────────────────────────────────────

def verify_domain(domain: Domain) -> dict:
    """
    Run SPF / DKIM / DMARC checks against live DNS for `domain`.

    Updates the domain's verification flags and overall status.
    Returns a dict with per-record results (suitable for API response).
    """
    result = verify_domain_all(
        domain=domain.name,
        selector=domain.dkim_selector,
        expected_public_key=domain.dkim_public_key,
    )

    now = timezone.now()

    # Write individual results back to the model
    domain.spf_verified   = result.spf_ok
    domain.spf_last_check = now

    domain.dkim_verified   = result.dkim_ok
    domain.dkim_last_check = now

    domain.dmarc_verified   = result.dmarc_ok
    domain.dmarc_last_check = now

    # Recompute overall status
    domain.sync_status()

    if domain.is_verified:
        AuditLog.record(
            AuditLog.Action.DOMAIN_VERIFIED,
            user=domain.user,
            domain=domain.name,
        )
        logger.info("Domain '%s' fully verified.", domain.name)
    else:
        logger.info(
            "Domain '%s' partial verification: SPF=%s DKIM=%s DMARC=%s",
            domain.name, result.spf_ok, result.dkim_ok, result.dmarc_ok,
        )

    return result.as_dict()


# ── Delete domain ─────────────────────────────────────────────────────────────

def delete_domain(domain: Domain) -> None:
    """
    Remove a domain and its DKIM keys.
    The caller must ensure the user owns the domain before calling this.
    """
    name = domain.name
    domain.delete()
    logger.info("Domain '%s' deleted.", name)