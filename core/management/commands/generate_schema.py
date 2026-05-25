"""
Management command: generate_schema

Thin wrapper around drf-spectacular's built-in spectacular command
with MailFlow-specific defaults — outputs both JSON and YAML.

Usage:
    python manage.py generate_schema --settings=config.settings.dev

Output:
    docs/openapi.json
    docs/openapi.yaml

Place: core/management/commands/generate_schema.py

Also create the empty init files:
    core/management/__init__.py          ⬅ NEW FILE (empty)
    core/management/commands/__init__.py ⬅ NEW FILE (empty)
"""

import json
import subprocess
import sys
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate OpenAPI schema files (JSON + YAML) into docs/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default="docs",
            help="Directory to write schema files into (default: docs/).",
        )
        parser.add_argument(
            "--validate",
            action="store_true",
            default=False,
            help="Validate the generated schema (requires openapi-schema-validator).",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / "openapi.json"
        yaml_path = output_dir / "openapi.yaml"

        settings_module = "config.settings.dev"

        # ── Generate JSON ──────────────────────────────────────────────────────
        self.stdout.write("  Generating openapi.json …")
        result = subprocess.run(
            [
                sys.executable, "manage.py", "spectacular",
                "--color", "--file", str(json_path), "--format", "openapi-json",
                f"--settings={settings_module}",
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            self.stderr.write(self.style.ERROR(result.stderr))
            raise SystemExit(1)

        # ── Generate YAML ──────────────────────────────────────────────────────
        self.stdout.write("  Generating openapi.yaml …")
        result = subprocess.run(
            [
                sys.executable, "manage.py", "spectacular",
                "--color", "--file", str(yaml_path),
                f"--settings={settings_module}",
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            self.stderr.write(self.style.ERROR(result.stderr))
            raise SystemExit(1)

        # ── Pretty-print JSON (for readability) ───────────────────────────────
        raw  = json.loads(json_path.read_text())
        json_path.write_text(json.dumps(raw, indent=2))

        self.stdout.write(self.style.SUCCESS(
            f"\n✅  Schema written to:\n"
            f"    {json_path.resolve()}\n"
            f"    {yaml_path.resolve()}\n"
        ))

        # ── Optional validation ────────────────────────────────────────────────
        if options["validate"]:
            self.stdout.write("  Validating schema …")
            try:
                import openapi_schema_validator
                schema = json.loads(json_path.read_text())
                openapi_schema_validator.validate(schema)
                self.stdout.write(self.style.SUCCESS("  ✅  Schema is valid."))
            except ImportError:
                self.stdout.write(self.style.WARNING(
                    "  ⚠  openapi-schema-validator not installed. "
                    "Run: pip install openapi-schema-validator"
                ))
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"  ❌  Validation error: {exc}"))