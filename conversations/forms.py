from django import forms
from .models import Message
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("body", "attachment")
        widgets = {"body": forms.Textarea(attrs={"rows": 2, "placeholder": "Write a message…"})}

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("body") and not cleaned.get("attachment"):
            raise forms.ValidationError("Write a message or attach a file.")
        attachment = cleaned.get("attachment")
        if attachment and attachment.size > 10 * 1024 * 1024:
            self.add_error("attachment", "Attachments must be 10 MB or smaller.")
        return cleaned
