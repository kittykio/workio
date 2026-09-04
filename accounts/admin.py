from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import PortfolioItem, Review, User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Portfolio", {"fields": ("role", "avatar", "headline", "bio", "location", "skills", "hourly_rate", "website", "company")}),)

admin.site.register(PortfolioItem)
admin.site.register(Review)
