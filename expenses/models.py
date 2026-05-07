from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
# Create your models here.

class Expense(models.Model):
    category_choices=[('Food','Food'),
                      ('Travel','Travel'),
                      ('Shopping','Shopping'),
                      ('Bills','Bills'),
                      ('Others','Others'),
                      ]
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    amount=models.FloatField()
    category=models.CharField(max_length=20,choices=category_choices)
    # ✅ Main expense/payment date
    date = models.DateField(default=now)

    # ✅ OCR bill details
    bill_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    description=models.TextField(blank=True)
    

    def __str__(self):
      return f"{self.category}-{self.amount}"
    
class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.FloatField()
    month = models.IntegerField()
    year = models.IntegerField()
    

    def __str__(self):
        return f"{self.user.username} - {self.month}/{self.year}"
    

class Receipt(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    image=models.ImageField(upload_to='receipts/')
    uploaded_at=models.DateTimeField(auto_now_add=True)
    