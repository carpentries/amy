from django.contrib import admin

from src.offering.models import AccountBenefitDiscount


class AccountBenefitDiscountAdmin(admin.ModelAdmin[AccountBenefitDiscount]):
    list_display = ("name",)
    search_fields = ("name",)


admin.site.register(AccountBenefitDiscount, AccountBenefitDiscountAdmin)
