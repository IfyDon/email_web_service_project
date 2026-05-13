from django.contrib.auth.decorators import login_required
from django.urls import path
from web.views import dashboard, account, domains_ui, analytics_ui, webhooks_ui, templates_ui

app_name = "web"

urlpatterns = [
    # ── Public ────────────────────────────────────────────────────────────────
    path("",        dashboard.landing,    name="landing"),
    path("status/", dashboard.status_page, name="status"),

    # ── Dashboard ─────────────────────────────────────────────────────────────
    path("dashboard/",                    login_required(dashboard.overview),       name="dashboard"),
    path("dashboard/messages/",           login_required(dashboard.messages),       name="messages"),
    path("dashboard/messages/<uuid:pk>/", login_required(dashboard.message_detail), name="message-detail"),

    # ── Domains ───────────────────────────────────────────────────────────────
    path("dashboard/domains/",                        login_required(domains_ui.domain_list),   name="domains"),
    path("dashboard/domains/add/",                    login_required(domains_ui.domain_add),    name="domain-add"),
    path("dashboard/domains/<uuid:pk>/",              login_required(domains_ui.domain_detail), name="domain-detail"),
    path("dashboard/domains/<uuid:pk>/verify/",       login_required(domains_ui.domain_verify), name="domain-verify"),
    path("dashboard/domains/<uuid:pk>/delete/",       login_required(domains_ui.domain_delete), name="domain-delete"),

    # ── Templates ─────────────────────────────────────────────────────────────
    path("dashboard/templates/",                login_required(templates_ui.template_list), name="templates"),
    path("dashboard/templates/new/",            login_required(templates_ui.template_edit), name="template-new"),
    path("dashboard/templates/<uuid:pk>/edit/", login_required(templates_ui.template_edit), name="template-edit"),

    # ── Analytics ─────────────────────────────────────────────────────────────
    path("dashboard/analytics/", login_required(analytics_ui.analytics), name="analytics"),

    # ── Webhooks ──────────────────────────────────────────────────────────────
    path("dashboard/webhooks/",                  login_required(webhooks_ui.webhook_list),   name="webhooks"),
    path("dashboard/webhooks/add/",              login_required(webhooks_ui.webhook_add),    name="webhook-add"),
    path("dashboard/webhooks/<uuid:pk>/delete/", login_required(webhooks_ui.webhook_delete), name="webhook-delete"),

    # ── Suppressions ─────────────────────────────────────────────────────────
    path("dashboard/suppressions/", login_required(dashboard.suppressions), name="suppressions"),

    # ── Account & Security ────────────────────────────────────────────────────
    path("dashboard/account/",              login_required(account.account_settings), name="account"),

    # API Keys
    path("dashboard/api-keys/",             login_required(account.api_keys),         name="api-keys"),
    path("dashboard/api-keys/new/",         login_required(account.api_key_create),   name="api-key-create"),
    path("dashboard/api-keys/reveal/",      login_required(account.api_key_reveal),   name="api-key-reveal"),
    path("dashboard/api-keys/<uuid:pk>/revoke/", login_required(account.api_key_revoke), name="api-key-revoke"),

    # 2FA
    path("dashboard/2fa/setup/",        login_required(account.two_fa_setup),        name="2fa-setup"),
    path("dashboard/2fa/backup-codes/", login_required(account.two_fa_backup_codes), name="2fa-backup-codes"),
    path("dashboard/2fa/disable/",      login_required(account.two_fa_disable),      name="2fa-disable"),

    # Billing
    path("dashboard/billing/", login_required(account.billing), name="billing"),

    # ── Unsubscribe (public) ──────────────────────────────────────────────────
    path("unsubscribe/<str:token>/", dashboard.unsubscribe, name="unsubscribe"),
]