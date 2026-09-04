from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import PortfolioItem, Review, User


class SignupForm(UserCreationForm):
    email = forms.EmailField()
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "role")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("avatar", "first_name", "last_name", "headline", "bio", "location", "skills", "hourly_rate", "website", "company")
        widgets = {
            "avatar": forms.FileInput(attrs={"accept": "image/*"}),
            "bio": forms.Textarea(attrs={"rows": 5}),
            "skills": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.role == User.Role.CLIENT:
            self.fields.pop("skills", None)
            self.fields.pop("hourly_rate", None)

    def clean_skills(self):
        skills = []
        seen = set()
        for value in self.cleaned_data.get("skills", "").split(","):
            skill = value.strip()
            key = skill.casefold()
            if skill and key not in seen:
                skills.append(skill)
                seen.add(key)
        value = ", ".join(skills)
        if len(value) > 250:
            raise forms.ValidationError("Your expertise must be 250 characters or fewer in total.")
        return value

    def clean_avatar(self):
        if self.data.get("avatar-clear"):
            return False
        return self.cleaned_data.get("avatar")


class AccountSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email", "email_notifications")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email


class PortfolioItemForm(forms.ModelForm):
    class Meta:
        model = PortfolioItem
        fields = ("title", "summary", "image", "project_url", "skills", "featured")
        widgets = {"summary": forms.Textarea(attrs={"rows": 5})}

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 8 * 1024 * 1024:
            raise forms.ValidationError("Images must be 8 MB or smaller.")
        return image


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "body")
        widgets = {"rating": forms.RadioSelect(choices=[(value, "★" * value) for value in range(5, 0, -1)]), "body": forms.Textarea(attrs={"rows": 5, "placeholder": "What was it like working together?"})}
