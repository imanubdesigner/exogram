from django.urls import path

from .views import (
    AcceptInvitationView,
    CreateInvitationLinkView,
    CredentialsUpdateView,
    CurrentUserView,
    DisplayPreferencesView,
    ForgotPasswordView,
    GoodreadsActivateView,
    GoodreadsReadingView,
    InvitationListView,
    InvitationStatsView,
    LoginView,
    LogoutView,
    NetworkTreeView,
    PrivacySettingsView,
    ProfileUpdateView,
    PublicProfileView,
    RegisterByTokenView,
    RegisterView,
    ResetInvitedUserTempPasswordView,
    ResetPasswordView,
    SendInvitationView,
    TokenRefreshCookieView,
    UserActivityView,
    ValidateInvitationView,
    WaitlistActivateView,
    WaitlistCommunityView,
    WaitlistView,
    complete_onboarding,
    delete_account,
    export_data,
)

urlpatterns = [
    # Autenticación
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('accounts/accept-invite/', AcceptInvitationView.as_view(), name='accept_invite'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/token/refresh/', TokenRefreshCookieView.as_view(), name='token_refresh'),

    # Sistema de invitaciones
    path('invitations/', InvitationListView.as_view(), name='invitation_list'),
    path('invitations/send/', SendInvitationView.as_view(), name='send_invitation'),
    path('invitations/link/', CreateInvitationLinkView.as_view(), name='create_invitation_link'),
    path(
        'invitations/<int:invited_user_id>/reset-temp-password/',
        ResetInvitedUserTempPasswordView.as_view(),
        name='reset_invited_user_temp_password',
    ),
    path('invitations/validate/<str:token>/', ValidateInvitationView.as_view(), name='validate_invitation'),
    path('invitations/stats/', InvitationStatsView.as_view(), name='invitation_stats'),

    # Registro por token de invitación (Modelo B)
    path('auth/register-by-token/', RegisterByTokenView.as_view(), name='register_by_token'),

    # Lista de espera (Modelo A)
    path('waitlist/', WaitlistView.as_view(), name='waitlist'),
    path('waitlist/community/', WaitlistCommunityView.as_view(), name='waitlist_community'),
    path('waitlist/<int:entry_id>/activate/', WaitlistActivateView.as_view(), name='waitlist_activate'),

    # Perfil del usuario autenticado
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('me/credentials/update/', CredentialsUpdateView.as_view(), name='update_credentials'),
    path('me/profile/', ProfileUpdateView.as_view(), name='update_profile'),
    path('me/goodreads/activate/', GoodreadsActivateView.as_view(), name='activate_goodreads'),
    path('me/goodreads/reading/', GoodreadsReadingView.as_view(), name='goodreads_reading'),
    path('me/privacy/', PrivacySettingsView.as_view(), name='privacy_settings'),
    path('me/display/', DisplayPreferencesView.as_view(), name='display_preferences'),
    path('me/onboarding/complete/', complete_onboarding, name='complete_onboarding'),
    path('me/network-tree/', NetworkTreeView.as_view(), name='network_tree'),
    path('me/activity/', UserActivityView.as_view(), name='user_activity'),

    # Exportación y eliminación
    path('me/export/', export_data, name='export_data'),
    path('me/delete/', delete_account, name='delete_account'),

    # Perfiles públicos (solo el perfil base, no los highlights/notas)
    path('users/<str:nickname>/', PublicProfileView.as_view(), name='public_profile'),
]
