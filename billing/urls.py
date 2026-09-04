from django.urls import path
from . import views

urlpatterns = [
    path("timer/project/<int:project_pk>/start/", views.timer_start, name="timer_start"),
    path("timer/stop/", views.timer_stop, name="timer_stop"),
    path("expenses/", views.expense_list, name="expense_list"),
    path("expenses/project/<int:project_pk>/new/", views.expense_create, name="expense_create"),
    path("expenses/<int:pk>/edit/", views.expense_edit, name="expense_edit"),
    path("expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"),
    path("expenses/<int:pk>/receipt/", views.expense_receipt, name="expense_receipt"),
    path("time/", views.time_list, name="time_list"),
    path("time/project/<int:project_pk>/new/", views.time_create, name="time_create"),
    path("time/<int:pk>/edit/", views.time_edit, name="time_edit"),
    path("time/<int:pk>/delete/", views.time_delete, name="time_delete"),
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/project/<int:project_pk>/new/", views.invoice_create, name="invoice_create"),
    path("invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:pk>/edit/", views.invoice_edit, name="invoice_edit"),
    path("invoices/<int:pk>/delete/", views.invoice_delete, name="invoice_delete"),
    path("invoices/<int:pk>/status/", views.invoice_status, name="invoice_status"),
]
