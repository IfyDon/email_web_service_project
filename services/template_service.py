"""
Template service — business logic for creating, updating,
rendering, and previewing email templates.

Responsibilities:
  - MJML → HTML compilation
  - HTML sanitisation (bleach)
  - CSS inlining (premailer) for email client compatibility
  - Plain-text auto-generation from HTML (bs4)
  - Jinja2 context substitution for rendering
  - Version snapshotting before every update

Place: services/template_service.py
"""

import logging
import re

from django.utils.text import slugify

import bleach
import jinja2
import jinja2.sandbox
from bs4 import BeautifulSoup

from apps.templates_app.models import EmailTemplate, TemplateVersion
from core.exceptions import TemplateRenderError

logger = logging.getLogger(__name__)

# ── Allowed HTML tags/attrs for sanitisation ──────────────────────────────────
ALLOWED_TAGS = list(bleach.sanitizer.ALLOWED_TAGS) + [
    "html", "head", "body", "meta", "style", "link",
    "table", "thead", "tbody", "tr", "th", "td",
    "div", "span", "p", "a", "img", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote", "pre", "code",
    "strong", "em", "b", "i", "u",
    "center", "font",
]
ALLOWED_ATTRS = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "*":    ["class", "id", "style", "align", "valign", "width", "height",
             "border", "cellpadding", "cellspacing", "bgcolor"],
    "a":    ["href", "title", "target", "rel"],
    "img":  ["src", "alt", "width", "height", "style"],
    "td":   ["colspan", "rowspan", "width", "align"],
    "th":   ["colspan", "rowspan", "width", "align"],
    "meta": ["name", "content", "charset", "http-equiv"],
    "link": ["rel", "href", "type"],
}

# ── Jinja2 sandbox environment ────────────────────────────────────────────────
_jinja_env = jinja2.sandbox.SandboxedEnvironment(
    autoescape=True,
    undefined=jinja2.Undefined,   # silently ignore missing vars (don't crash)
)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _compile_mjml(mjml_source: str) -> str:
    """
    Compile MJML source to HTML.
    Falls back gracefully if mjml-python is not installed.
    """
    try:
        import mjml
        result = mjml.mjml_to_html(mjml_source)
        if result.errors:
            raise TemplateRenderError(
                f"MJML compilation errors: {result.errors}"
            )
        return result.html
    except ImportError:
        logger.warning("mjml-python not installed — returning raw MJML as-is.")
        return mjml_source


def _sanitise_html(html: str) -> str:
    """Strip dangerous tags/attrs from user-supplied HTML."""
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True,
    )


def _inline_css(html: str) -> str:
    """
    Inline CSS <style> rules into element style= attributes using premailer.
    Makes emails render correctly in Gmail and Outlook.
    """
    try:
        import premailer
        return premailer.transform(html, raise_errors=False)
    except Exception as exc:
        logger.warning("premailer inlining failed: %s", exc)
        return html


def _html_to_text(html: str) -> str:
    """Extract clean plain text from an HTML string using BeautifulSoup."""
    soup = BeautifulSoup(html, "lxml")
    # Replace <br> and <p> with newlines
    for tag in soup.find_all(["br", "p", "div", "tr"]):
        tag.insert_before("\n")
    # Extract links as [text](url)
    for tag in soup.find_all("a"):
        href = tag.get("href", "")
        tag.replace_with(f"{tag.get_text()} ({href})" if href else tag.get_text())
    text = soup.get_text(separator=" ")
    # Collapse excessive whitespace / blank lines
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _render_jinja(template_str: str, context: dict) -> str:
    """
    Render a Jinja2 template string with the given context.
    Uses a sandboxed environment so user templates cannot execute Python.
    """
    try:
        tmpl = _jinja_env.from_string(template_str)
        return tmpl.render(**context)
    except jinja2.TemplateError as exc:
        raise TemplateRenderError(f"Template rendering failed: {exc}") from exc


# ── Public API ────────────────────────────────────────────────────────────────

def create_template(
    user,
    *,
    name: str,
    subject: str,
    body_html: str = "",
    body_mjml: str = "",
    body_text: str = "",
    description: str = "",
    variable_schema: dict | None = None,
) -> EmailTemplate:
    """
    Create a new EmailTemplate for `user`.

    Pipeline:
      1. If body_mjml provided → compile to HTML.
      2. Sanitise HTML.
      3. Inline CSS.
      4. Auto-generate plain text if body_text is empty.
      5. Persist.
    """
    body_type = EmailTemplate.BodyType.HTML

    if body_mjml:
        body_type = EmailTemplate.BodyType.MJML
        body_html = _compile_mjml(body_mjml)

    if body_html:
        body_html = _sanitise_html(body_html)
        body_html = _inline_css(body_html)

    if not body_text and body_html:
        body_text = _html_to_text(body_html)

    slug = slugify(name)[:200]
    # Ensure slug uniqueness per user
    if EmailTemplate.objects.filter(user=user, slug=slug).exists():
        import uuid as _uuid
        slug = f"{slug}-{str(_uuid.uuid4())[:8]}"

    template = EmailTemplate.objects.create(
        user=user,
        name=name,
        description=description,
        slug=slug,
        subject=subject,
        body_type=body_type,
        body_html=body_html,
        body_mjml=body_mjml,
        body_text=body_text,
        variable_schema=variable_schema or {},
    )

    logger.info("Template '%s' created for user %s", template.name, user.email)
    return template


def update_template(
    template: EmailTemplate,
    *,
    name: str | None = None,
    subject: str | None = None,
    body_html: str | None = None,
    body_mjml: str | None = None,
    body_text: str | None = None,
    description: str | None = None,
    variable_schema: dict | None = None,
) -> EmailTemplate:
    """
    Update an existing template.
    Snapshots the current version before applying changes.
    """
    # Snapshot before mutating
    template.snapshot()
    template.current_version += 1

    if name is not None:
        template.name = name

    if description is not None:
        template.description = description

    if variable_schema is not None:
        template.variable_schema = variable_schema

    if subject is not None:
        template.subject = subject

    if body_mjml is not None:
        template.body_mjml = body_mjml
        template.body_type = EmailTemplate.BodyType.MJML
        body_html = _compile_mjml(body_mjml)

    if body_html is not None:
        body_html = _sanitise_html(body_html)
        body_html = _inline_css(body_html)
        template.body_html = body_html
        if not body_text:
            template.body_text = _html_to_text(body_html)

    if body_text is not None:
        template.body_text = body_text

    template.save()
    logger.info("Template '%s' updated to v%s", template.name, template.current_version)
    return template


def render_template(
    template: EmailTemplate,
    context: dict,
) -> dict:
    """
    Render a template with variable substitution.

    Returns:
        {
            "subject":   str,
            "body_html": str,
            "body_text": str,
        }

    Raises TemplateRenderError on Jinja2 syntax errors.
    """
    return {
        "subject":   _render_jinja(template.subject,   context),
        "body_html": _render_jinja(template.body_html, context),
        "body_text": _render_jinja(template.body_text, context),
    }


def preview_template(
    template: EmailTemplate,
    context: dict | None = None,
) -> dict:
    """
    Render the template with sample/provided context for dashboard preview.
    Fills in missing variables with a placeholder so the preview never crashes.
    """
    safe_context = {k: f"[{k}]" for k in template.variable_schema}
    safe_context.update(context or {})
    return render_template(template, safe_context)


def delete_template(template: EmailTemplate) -> None:
    """Soft-delete: mark template inactive (preserves history)."""
    template.is_active = False
    template.save(update_fields=["is_active"])
    logger.info("Template '%s' deactivated.", template.name)


def get_template_by_slug(user, slug: str) -> EmailTemplate:
    """Retrieve an active template by its machine-readable slug."""
    return EmailTemplate.objects.get(user=user, slug=slug, is_active=True)