from django.contrib import admin
from .models import EmailCode, Listing, Message


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "price", "status", "author_name", "created_at")
    list_filter = ("category", "status")
    search_fields = ("title", "details", "author_name")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("listing", "sender_name", "created_at")


@admin.register(EmailCode)
class EmailCodeAdmin(admin.ModelAdmin):
    list_display = ("email", "mode", "created_at", "attempts", "used")
    readonly_fields = ("code_hash",)
