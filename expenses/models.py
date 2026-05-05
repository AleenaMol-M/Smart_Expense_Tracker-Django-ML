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
    date=models.DateField(default=now)
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