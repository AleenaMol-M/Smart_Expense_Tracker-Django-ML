from django.contrib import admin
from .models import Expense, Budget, Receipt


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "amount", "date")
    list_filter = ("category", "date")
    search_fields = ("user__username", "category", "description")


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "month", "year")
    list_filter = ("month", "year")
    search_fields = ("user__username",)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("user", "uploaded_at")
    search_fields = ("user__username",)