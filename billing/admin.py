from django.contrib import admin
from .models import ActiveTimer, Expense, Invoice, InvoiceItem, TimeEntry
admin.site.register(Invoice)
admin.site.register(InvoiceItem)
admin.site.register(TimeEntry)
admin.site.register(ActiveTimer)
admin.site.register(Expense)
