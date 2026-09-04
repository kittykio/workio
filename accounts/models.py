from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.core.validators import MaxValueValidator, MinValueValidator


class User(AbstractUser):
    class Role(models.TextChoices):
        FREELANCER = "freelancer", "Freelancer"
        CLIENT = "client", "Client"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.FREELANCER)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    headline = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=80, blank=True)
    skills = models.CharField(max_length=250, blank=True, help_text="Comma-separated skills")
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    website = models.URLField(blank=True)
    company = models.CharField(max_length=120, blank=True)
    email_notifications = models.BooleanField(default=False)

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def initials(self):
        return "".join(part[0] for part in self.display_name.split()[:2]).upper()

    @property
    def skill_list(self):
        return [skill.strip() for skill in self.skills.split(",") if skill.strip()]

    def get_absolute_url(self):
        return reverse("profile", kwargs={"username": self.username})

    @property
    def average_rating(self):
        value = self.reviews_received.aggregate(models.Avg("rating"))["rating__avg"]
        return round(value, 1) if value else None


class PortfolioItem(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="portfolio_items")
    title = models.CharField(max_length=140)
    summary = models.TextField(max_length=1200)
    image = models.ImageField(upload_to="portfolio/%Y/%m/", blank=True)
    project_url = models.URLField(blank=True)
    skills = models.CharField(max_length=240, blank=True)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-featured", "-created_at"]

    @property
    def skill_list(self):
        return [item.strip() for item in self.skills.split(",") if item.strip()]


class Review(models.Model):
    project = models.OneToOneField("projects.Project", on_delete=models.CASCADE, related_name="review")
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews_written")
    freelancer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews_received")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    body = models.TextField(max_length=1200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
