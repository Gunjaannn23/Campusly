from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_page, name="login"),
    path("home/", views.home_page, name="home"),
    path("api/auth/request-code/", views.request_code),
    path("api/auth/verify/", views.verify_code),
    path("api/auth/me/", views.me),
    path("api/auth/logout/", views.logout_view),
    path("api/listings/", views.listings),
    path("api/listings/<int:pk>/", views.listing_detail),
    path("api/listings/<int:pk>/status/", views.listing_status),
    path("api/messages/", views.messages_view),
]
