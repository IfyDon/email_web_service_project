from django.contrib import admin
from .models import EmailTemplate, TemplateVersion


class TemplateVersionInline(admin.TabularInline):
    model   = TemplateVersion
    extra   = 0
    fields  = ["version_number", "subject", "created_at"]
    readonly_fields = ["version_number", "subject", "created_at"]
    ordering = ["-version_number"]
    can_delete = False


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display  = ["name", "slug", "user", "body_type",
                     "current_version", "is_active", "created_at"]
    list_filter   = ["body_type", "is_active"]
    search_fields = ["name", "slug", "user__email"]
    readonly_fields = ["id", "slug", "current_version", "created_at", "updated_at"]
    inlines = [TemplateVersionInline]
    ordering = ["-created_at"]

    fieldsets = (
        (None,        {"fields": ("id", "user", "name", "slug", "description", "is_active")}),
        ("Content",   {"fields": ("subject", "body_type", "body_html", "body_mjml", "body_text")}),
        ("Variables", {"fields": ("variable_schema",)}),
        ("Versioning",{"fields": ("current_version", "created_at", "updated_at")}),
    )


@admin.register(TemplateVersion)
class TemplateVersionAdmin(admin.ModelAdmin):
    list_display  = ["template", "version_number", "created_at"]
    search_fields = ["template__name"]
    readonly_fields = [f.name for f in TemplateVersion._meta.get_fields()
                       if hasattr(f, "name")]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False