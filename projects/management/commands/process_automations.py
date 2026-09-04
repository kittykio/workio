from django.core.management.base import BaseCommand

from projects.automations import run_due_automations


class Command(BaseCommand):
    help = "Process due Workio scheduled automation rules."

    def handle(self, *args, **options):
        count = run_due_automations()
        self.stdout.write(self.style.SUCCESS(f"Processed {count} automation action(s)."))
