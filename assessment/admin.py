from django.contrib import admin

from .models import AccessCode, UserProfile


@admin.register(AccessCode)
class AccessCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "is_used", "used_by", "used_at", "created_at")
    list_filter = ("used_at",)
    search_fields = ("code",)
    readonly_fields = ("used_at", "used_by", "created_at")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "runs_remaining", "created_at", "updated_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
