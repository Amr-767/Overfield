from django.contrib import admin

from .models import FarmerProfile


@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "preferred_language", "updated_at")
    search_fields = ("user__username", "user__email", "display_name")
