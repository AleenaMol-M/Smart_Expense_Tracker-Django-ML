from django.utils.timezone import now
from datetime import timedelta
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from .forms import ExpenseForm,BudgetForm,ReceiptForm
from .models import Expense,Budget,Receipt
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import calendar
import numpy as np
import cv2
import re
from PIL import Image
from datetime import datetime
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# Create your views here.

@login_required
def expense_list(request):
    expenses = Expense.objects.filter(user=request.user).order_by('-date', '-id')

    total = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    category_data = (
    Expense.objects
    .filter(user=request.user)
    .values('category')
    .annotate(total=Sum('amount'))
)

    # Filter high expenses (user-specific)
    expense = Expense.objects.filter(user=request.user, amount__gt=500)

    # 🔹 Smart insights
    insights = []

    if category_data:
        # Highest spending category
        highest = max(category_data, key=lambda x: x['total'])
        insights.append(f"You Spend Most On {highest['category']}")

        # High food spending
        for item in category_data:
            if item['category'] == 'Food' and item['total'] > 0.3 * total:
                insights.append("Your Food Spending Is High")

    

    return render(request, 'expense_list.html', {
        'expenses': expenses,
        'total': total,
        'category_data': category_data,
        'expense': expense,
        'insights': insights
    })

@login_required
def add_expense(request):
    if request.method=='POST':
        form=ExpenseForm(request.POST)
        if form.is_valid():
            expense=form.save(commit=False)
            expense.user=request.user
            expense.save()
            return redirect('expense_list')
    else:
        form=ExpenseForm()
    return render(request,'add_expense.html',{'form':form})

    # “Show only expenses above ₹500”

@login_required
def show_expnese(request):
    expense=Expense.objects.filter(amount__gt=500)
    return render(request,'expense_list.html',{'expense':expense})

@login_required
def delete_expense(request, id):
    expense = get_object_or_404(Expense, id=id, user=request.user)
    expense.delete()
    return redirect('expense_list')

@login_required
def edit_expense(request, id):
    expense = get_object_or_404(Expense, id=id, user=request.user)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)

    return render(request, 'edit_expense.html', {'form': form})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()

    return render(request, 'signup.html', {'form': form})
    
def home(request):
    return render(request, 'home.html')

@login_required
def user_dashboard(request):
    expenses = Expense.objects.filter(user=request.user)

    category_predictions = {}
    total_prediction = 0
    alerts = []

    # 🔹 Get current month budget
    today = now()

    budget_obj = Budget.objects.filter(
        user=request.user,
        month=today.month,
        year=today.year
    ).first()

    # 🔹 If no budget → use last month's budget
    if not budget_obj:
        last_budget = Budget.objects.filter(user=request.user).order_by('-year', '-month').first()
        budget = last_budget.amount if last_budget else None
    else:
        budget = budget_obj.amount

    # 🔹 ML Prediction
    if expenses.exists():
        categories = expenses.values_list('category', flat=True).distinct()

        for cat in categories:
            cat_expenses = expenses.filter(category=cat)

            data = []
            for exp in cat_expenses:
                data.append({
                    'date': exp.date,
                    'amount': exp.amount
                })

            df = pd.DataFrame(data)

            if df.empty:
                continue

            df['date'] = pd.to_datetime(df['date'])

            df_daily = df.groupby('date')['amount'].sum().reset_index()

            if len(df_daily) < 2:
                avg_daily = df_daily['amount'].mean()
                monthly_pred = avg_daily * 30
            else:
                df_daily['days'] = (df_daily['date'] - df_daily['date'].min()).dt.days
                df_daily['month'] = df_daily['date'].dt.month
                df_daily['day_of_week'] = df_daily['date'].dt.dayofweek
                df_daily['week'] = df_daily['date'].dt.isocalendar().week.astype(int)

                X = df_daily.drop(['amount', 'date'], axis=1)
                y = df_daily['amount']

                model = RandomForestRegressor(n_estimators=100, random_state=42)
                model.fit(X, y)

                future_date = df_daily['date'].max() + pd.Timedelta(days=1)

                future_input = {
                    'days': df_daily['days'].max() + 1,
                    'month': future_date.month,
                    'day_of_week': future_date.dayofweek,
                    'week': int(future_date.isocalendar().week)
                }

                future_df = pd.DataFrame([future_input])

                daily_pred = model.predict(future_df)[0]

                # 🔥 spending frequency adjustment
                active_days = len(df_daily)
                total_days = (df_daily['date'].max() - df_daily['date'].min()).days + 1

                ratio = active_days / total_days if total_days > 0 else 1
                expected_days = ratio * 30

                monthly_pred = daily_pred * expected_days

                # 🔒 prevent extreme values
                monthly_pred = min(monthly_pred, df_daily['amount'].sum() * 1.5)

            category_predictions[cat] = round(monthly_pred, 2)

        total_prediction = sum(category_predictions.values())

    # 🔹 Alerts logic
    if budget:
        if total_prediction > budget:
            alerts.append("⚠️ You may exceed your budget this month")

        elif total_prediction > 0.8 * budget:
            alerts.append("⚠️ You are close to your budget limit")
    # 🔥 ANOMALY DETECTION
    anomaly_message = None

    today = now().date()

# today's total spending
    today_spend = expenses.filter(date=today).aggregate(Sum('amount'))['amount__sum'] or 0

# daily totals (past data)
    daily_data = expenses.values('date').annotate(total=Sum('amount'))

    daily_amounts = [item['total'] for item in daily_data if item['date'] != today]

# need enough data
    if len(daily_amounts) >= 5:
        import numpy as np

        avg = np.mean(daily_amounts)
        std = np.std(daily_amounts)

    # anomaly condition
        if std > 0 and today_spend > avg + 2 * std:
            anomaly_message = f"⚠️ Unusual spending today! ₹{today_spend} (usual ₹{round(avg,2)})"
    return render(request, 'user_dashboard.html', {
        'category_predictions': category_predictions,
        'total_prediction': round(total_prediction, 2),
        'budget': budget,
        'alerts': alerts,'anomaly_message': anomaly_message
    })

@login_required
def daily_expenses(request):
    today=now().date()
    expenses=Expense.objects.filter(user=request.user,date=today)
    return render(request,'daily_expenses.html',{'expenses':expenses})

@login_required
def weekly_expenses(request):
    today = now().date()

    # ✅ FIX 1: Current WEEK (Monday → today)
    start_of_week = today - timedelta(days=today.weekday())

    expenses = Expense.objects.filter(
        user=request.user,
        date__range=[start_of_week, today]
    ).order_by('-date', '-id')  # latest first

    # 👉 All expenses for anomaly detection
    all_expenses = Expense.objects.filter(user=request.user)

    # 📊 Step 1: Group by (year, week)
    weekly_dict = {}

    for exp in all_expenses:
        year, week, _ = exp.date.isocalendar()
        key = (year, week)

        weekly_dict.setdefault(key, 0)
        weekly_dict[key] += exp.amount

    weekly_anomaly = None

    # 📌 Step 2: Current week key
    current_year, current_week_num, _ = today.isocalendar()
    current_key = (current_year, current_week_num)

    current_week_total = weekly_dict.get(current_key, 0)

    # 📌 Step 3: Past weeks only
    past_values = [
        total for key, total in weekly_dict.items()
        if key != current_key
    ]

    # 📌 Step 4: Apply anomaly logic (MEDIAN ✔)
    if len(past_values) >= 2:
        median = np.median(past_values)

        if current_week_total > median * 1.2:
            weekly_anomaly = (
                f"⚠️ High spending this week "
                f"(₹{current_week_total}, median ₹{round(median, 2)})"
            )

        elif current_week_total < median * 0.8:
            weekly_anomaly = (
                f"📉 Low spending this week "
                f"(₹{current_week_total}, median ₹{round(median, 2)})"
            )

        else:
            weekly_anomaly = (
                f"✅ Normal spending this week "
                f"(₹{current_week_total})"
            )

    # 📊 BONUS: weekly total for UI
    weekly_total = sum(exp.amount for exp in expenses)

    return render(request, 'weekly_expenses.html', {
        'expenses': expenses,
        'weekly_anomaly': weekly_anomaly,
        'weekly_total': weekly_total
    })
@login_required
def monthly_expenses(request):
    today = now().date()

    # ✅ Current month expenses (latest first)
    expenses = Expense.objects.filter(
        user=request.user,
        date__month=today.month,
        date__year=today.year
    ).order_by('-date', '-id')

    # 👉 All expenses (for anomaly detection)
    all_expenses = Expense.objects.filter(user=request.user)

    # 📊 Step 1: Group by (year, month)
    monthly_dict = {}

    for exp in all_expenses:
        key = (exp.date.year, exp.date.month)
        monthly_dict.setdefault(key, 0)
        monthly_dict[key] += exp.amount

    # 📌 Step 2: Current month
    current_key = (today.year, today.month)
    current_month_total = monthly_dict.get(current_key, 0)

    # 📌 Step 3: Past months
    past_values = [
        total for key, total in monthly_dict.items()
        if key != current_key
    ]

    # 📌 Step 4: Median-based anomaly
    monthly_anomaly = None

    if len(past_values) >= 1:
        median = np.median(past_values)

        if current_month_total > median * 1.2:
            monthly_anomaly = (
                f"⚠️ High spending this month "
                f"(₹{current_month_total}, median ₹{round(median, 2)})"
            )

        elif current_month_total < median * 0.8:
            monthly_anomaly = (
                f"📉 Low spending this month "
                f"(₹{current_month_total}, median ₹{round(median, 2)})"
            )

        else:
            monthly_anomaly = (
                f"✅ Normal spending this month (₹{current_month_total})"
            )
    else:
        monthly_anomaly = "Not enough data to analyze"

    # ✅ Monthly total (for UI)
    monthly_total = sum(exp.amount for exp in expenses)

    # 🔥 Previous month calculation
    first_day_this_month = today.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)

    prev_month = last_day_prev_month.month
    prev_year = last_day_prev_month.year

    prev_expenses = Expense.objects.filter(
        user=request.user,
        date__month=prev_month,
        date__year=prev_year
    )

    previous_month_total = sum(exp.amount for exp in prev_expenses)

    # 📊 Comparison logic (IMPROVED UX)
    comparison_message = None

    if previous_month_total > 0:
        difference = current_month_total - previous_month_total
        percentage_change = (difference / previous_month_total) * 100

        # 🔥 UX FIX: if previous month is too small
        if previous_month_total < 1000:
            if difference > 0:
                comparison_message = (
                    f"📈 You spent ₹{difference} more than last month"
                )
            elif difference < 0:
                comparison_message = (
                    f"📉 You spent ₹{abs(difference)} less than last month"
                )
            else:
                comparison_message = "😐 Spending is same as last month"

        else:
            if difference > 0:
                comparison_message = (
                    f"📈 You spent ₹{difference} more "
                    f"({round(percentage_change,1)}%) than last month"
                )
            elif difference < 0:
                comparison_message = (
                    f"📉 You spent ₹{abs(difference)} less "
                    f"({abs(round(percentage_change,1))}%) than last month"
                )
            else:
                comparison_message = "😐 Spending is same as last month"

    else:
        comparison_message = "No data for previous month"

      # 📈 Monthly trend data
    trend_data = []

    sorted_months = sorted(monthly_dict.keys())

    for year, month in sorted_months:
        label = f"{calendar.month_abbr[month]} {year}"
        total = monthly_dict[(year, month)]

        trend_data.append({
        'month': label,
        'total': total
    })

    return render(request, 'monthly_expenses.html', {
        'expenses': expenses,
        'monthly_anomaly': monthly_anomaly,
        'monthly_total': monthly_total,
        'previous_month_total': previous_month_total,
        'comparison_message': comparison_message,'trend_data': trend_data
    })
@login_required
def set_budget(request):
    from django.utils.timezone import now

    today = now()

    # ✅ Just get existing (DON'T create)
    budget_obj = Budget.objects.filter(
        user=request.user,
        month=today.month,
        year=today.year
    ).first()

    if request.method == "POST":
        form = BudgetForm(request.POST, instance=budget_obj)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.month = today.month
            budget.year = today.year
            budget.save()
            return redirect('user_dashboard')
    else:
        form = BudgetForm(instance=budget_obj)

    return render(request, 'set_budget.html', {'form': form})

@login_required
def budgets(request):
    expenses = Expense.objects.filter(user=request.user)
    today = now()

    # 📊 Current month spending
    current_month_expenses = expenses.filter(
        date__month=today.month,
        date__year=today.year
    )

    spent = current_month_expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    # 💰 Get current budget
    budget_obj = Budget.objects.filter(
        user=request.user,
        month=today.month,
        year=today.year
    ).first()

    # fallback to last budget
    if not budget_obj:
        last_budget = Budget.objects.filter(user=request.user).order_by('-year', '-month').first()
        budget = last_budget.amount if last_budget else None
    else:
        budget = budget_obj.amount

    # 💰 Remaining & daily limit
    remaining = None
    daily_limit = None
    alerts = []

    if budget:
        remaining = budget - spent

        days_in_month = calendar.monthrange(today.year, today.month)[1]
        days_left = days_in_month - today.day

        if days_left > 0:
            daily_limit = remaining / days_left

        # alerts
        if remaining < 0:
            alerts.append("⚠️ You have exceeded your budget")
        elif remaining < 0.2 * budget:
            alerts.append("⚠️ You are close to your budget limit")
    # 📊 Budget usage percentage
    usage_percent = None

    if budget and budget > 0:
        usage_percent = (spent / budget) * 100
    return render(request, 'budgets.html', {
    'budget': budget,
    'spent': spent,
    'remaining': remaining,
    'daily_limit': round(daily_limit, 2) if daily_limit else None,
    'alerts': alerts,
    'usage_percent': usage_percent
})
#OCR core
def extract_text(image_path):
    img=cv2.imread(image_path)
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)

    text=pytesseract.image_to_string(gray)
    return text

import re

def extract_amount(text):

    # 🔥 Important keywords
    keywords = [
        'Payable',
        'Bill Amount',
        'Total',
        'Amount'
    ]

    for keyword in keywords:

        # flexible pattern
        pattern = rf'{keyword}\s*[:=\-]?\s*(\d+\s*\.?\s*\d*)'

        match = re.search(pattern, text, re.IGNORECASE)

        if match:

            amount = match.group(1)

            # remove spaces
            amount = amount.replace(" ", "")

            try:
                return float(amount)
            except:
                pass

    return None
import re

def extract_date(text):

    # ✅ Try Bill Date first
    bill_match = re.search(
        r'Bill\s*Date\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})',
        text,
        re.IGNORECASE
    )

    if bill_match:
        return bill_match.group(1)

    # ✅ Try Due Date
    due_match = re.search(
        r'Due\s*Date\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})',
        text,
        re.IGNORECASE
    )

    if due_match:
        return due_match.group(1)

    # ✅ Fallback: first normal date
    dates = re.findall(r'\d{2}/\d{2}/\d{4}', text)

    if dates:
        return dates[0]

    return None
##.........................................#

def extract_bill_date(text):

    match = re.search(
        r'Bill\s*Date\s*[:=\-]?\s*(\d{2}/\d{2}/\d{4})',
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return None

def extract_due_date(text):

    match = re.search(
        r'Due\s*Date\s*[:=\-]?\s*(\d{2}/\d{2}/\d{4})',
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return None

def extract_category(text):

    text = text.lower()

    # 🔥 Bills
    if 'kseb' in text or 'electricity' in text or 'bill' in text:
        return 'Bills'

    # 🍔 Food
    elif 'swiggy' in text or 'zomato' in text or 'restaurant' in text:
        return 'Food'

    # 🚕 Travel
    elif 'uber' in text or 'ola' in text or 'bus' in text or 'train' in text:
        return 'Travel'

    # 🛒 Shopping
    elif 'amazon' in text or 'flipkart' in text or 'shopping' in text:
        return 'Shopping'

    # ❓ Default
    return 'Others'

def extract_description(text):

    text_lower = text.lower()

    if 'kseb' or 'electricity' in text_lower:
        return 'KSEB Electricity Bill'

    elif 'swiggy' in text_lower:
        return 'Swiggy Food Order'

    elif 'zomato' in text_lower:
        return 'Zomato Food Order'

    elif 'uber' or 'travel' in text_lower:
        return 'Uber Ride'

    elif 'amazon' in text_lower:
        return 'Amazon Shopping'

    return 'Scanned Receipt'

@login_required
def scan_receipt(request):

    extracted_data = None

    if request.method == 'POST':

        form = ReceiptForm(request.POST, request.FILES)

        if form.is_valid():

            receipt = form.save(commit=False)
            receipt.user = request.user
            receipt.save()

            image_path = receipt.image.path

            # 🔍 OCR TEXT
            text = extract_text(image_path)
            print(text)
            # 💰 Extract amount
            amount = extract_amount(text)
          
            category = extract_category(text)

            description = extract_description(text)
            # 📅 Extract bill date
            bill_date = extract_bill_date(text)

            # 📅 Extract due date
            due_date = extract_due_date(text)

            # ✅ Convert bill date
            if bill_date:
                try:
                    bill_date = datetime.strptime(
                        bill_date,
                        "%d/%m/%Y"
                    ).date()
                except:
                    bill_date = None

            # ✅ Convert due date
            if due_date:
                try:
                    due_date = datetime.strptime(
                        due_date,
                        "%d/%m/%Y"
                    ).date()
                except:
                    due_date = None

            # ✅ Save expense
            if amount:

                Expense.objects.create(
                    user=request.user,
                    amount=amount,
                    category=category,
                    description=description,

                    # actual payment date
                    date=now().date(),

                    # bill info
                    bill_date=bill_date,
                    due_date=due_date
                )

            extracted_data = {
                'text': text,
                'amount': amount,
                'category': category,
                'description':description,
                'bill_date': bill_date,
                'due_date': due_date,
                'image_url': receipt.image.url,
            }

    else:
        form = ReceiptForm()

    return render(request, 'scan_receipt.html', {
        'form': form,
        'data': extracted_data
    })