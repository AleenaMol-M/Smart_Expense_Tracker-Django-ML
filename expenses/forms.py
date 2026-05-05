from django import forms
from .models import Expense,Budget

class ExpenseForm(forms.ModelForm):
    class Meta:
        model=Expense
        fields = ['amount', 'category', 'date', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['amount']

        