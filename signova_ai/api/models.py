from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):

    USER_TYPES = (
        ('deaf', 'Deaf'),
        ('hearing', 'Hearing'),
    )

    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True
    )

    preferred_sign_language = models.CharField(
        max_length=100,
        default='ASL'
    )

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPES
    )

    country = models.CharField(
        max_length=100
    )

    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES
    )

    age = models.IntegerField()

    def __str__(self):
        return self.user.username