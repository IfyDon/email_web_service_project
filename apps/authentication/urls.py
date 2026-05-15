from django.urls import path
from .views import (
    SignupView, LoginView, TwoFALoginView, LogoutView,
    MeView, ChangePasswordView,
    PasswordResetRequestView, PasswordResetConfirmView,
    APIKeyListCreateView, APIKeyDetailView,
    TwoFASetupView, TwoFAVerifyView, TwoFADisableView,
    BackupCodeRegenerateView,
)

app_name = "authentication"

urlpatterns = [
    path("signup/",                  SignupView.as_view(),               name="signup"),
    path("login/",                   LoginView.as_view(),                name="login"),
    path("login/2fa/",               TwoFALoginView.as_view(),           name="login-2fa"),
    path("logout/",                  LogoutView.as_view(),               name="logout"),
    path("me/",                      MeView.as_view(),                   name="me"),
    path("change-password/",         ChangePasswordView.as_view(),       name="change-password"),
    path("password-reset/request/",  PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/",  PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("api-keys/",                APIKeyListCreateView.as_view(),     name="api-keys"),
    path("api-keys/<uuid:pk>/",      APIKeyDetailView.as_view(),         name="api-key-detail"),
    path("2fa/setup/",               TwoFASetupView.as_view(),           name="2fa-setup"),
    path("2fa/verify/",              TwoFAVerifyView.as_view(),          name="2fa-verify"),
    path("2fa/disable/",             TwoFADisableView.as_view(),         name="2fa-disable"),
    path("2fa/backup-codes/",        BackupCodeRegenerateView.as_view(), name="2fa-backup-codes"),
]