from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),   # 👈 homepage (login/signup)

    path('dashboard/', views.user_dashboard, name='user_dashboard'),

    path('expense_list/', views.expense_list, name='expense_list'),
    path('add_expense/', views.add_expense, name='add_expense'),
    path('show_expnese/', views.show_expnese, name='show_expnese'),

    path('signup/', views.signup, name='signup'),

    path('daily_expenses/', views.daily_expenses, name='daily_expenses'),
    path('weekly_expenses/', views.weekly_expenses, name='weekly_expenses'),
    path('monthly_expenses/', views.monthly_expenses, name='monthly_expenses'),
    path('budgets/', views.budgets, name='budgets'),
    path('set_budget/', views.set_budget, name='set_budget'),
    path('delete_expense/<int:id>/', views.delete_expense, name='delete_expense'),
    path('edit_expense/<int:id>/', views.edit_expense, name='edit_expense'),

]