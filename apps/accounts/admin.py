from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Team, TeamMembership


# ── User ──────────────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering      = ["-date_joined"]
    list_display  = [
        "email", "full_name", "role",
        "is_verified", "otp_enabled",
        "monthly_quota", "emails_sent_mtd",
        "is_active", "date_joined",
    ]
    list_filter   = ["role", "is_active", "is_staff", "is_verified", "otp_enabled"]
    search_fields = ["email", "full_name"]
    readonly_fields = ["id", "date_joined", "last_login", "emails_sent_mtd"]

    fieldsets = (
        (None,            {"fields": ("id", "email", "password")}),
        ("Personal",      {"fields": ("full_name",)}),
        ("Role & Quota",  {"fields": ("role", "monthly_quota", "emails_sent_mtd")}),
        ("Security",      {"fields": ("is_verified", "otp_enabled")}),
        ("Permissions",   {"fields": ("is_active", "is_staff", "is_superuser",
                                      "groups", "user_permissions")}),
        ("Timestamps",    {"fields": ("date_joined", "last_login")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "password1", "password2", "role"),
        }),
    )


# ── Team ──────────────────────────────────────────────────────────────────────

class TeamMembershipInline(admin.TabularInline):
    model  = TeamMembership
    extra  = 1
    fields = ["user", "role", "joined"]
    readonly_fields = ["joined"]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display  = ["name", "owner", "created_at"]
    search_fields = ["name", "owner__email"]
    readonly_fields = ["id", "created_at"]
    inlines = [TeamMembershipInline]