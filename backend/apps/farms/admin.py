from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Farm, FarmCropHistory, FarmerContext, FarmZone


class FarmZoneInline(admin.TabularInline):
    model = FarmZone
    extra = 0


@admin.register(Farm)
class FarmAdmin(GISModelAdmin):
    list_display = ("name", "owner", "area_hectares", "area_source", "geometry_source", "created_at")
    list_filter = ("area_source", "geometry_source", "country_code")
    search_fields = ("name", "owner__username")
    inlines = [FarmZoneInline]


@admin.register(FarmZone)
class FarmZoneAdmin(GISModelAdmin):
    list_display = ("name", "farm", "area_hectares", "created_at")
    search_fields = ("name", "farm__name")


class FarmCropHistoryInline(admin.TabularInline):
    model = FarmCropHistory
    extra = 0


@admin.register(FarmerContext)
class FarmerContextAdmin(admin.ModelAdmin):
    list_display = ("farm", "texture_class", "ph", "irrigation_type", "updated_at")
    inlines = [FarmCropHistoryInline]
