from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import PortfolioItem, Review, User
from conversations.models import Conversation, Message
from billing.models import Expense, Invoice, InvoiceItem, TimeEntry
from projects.models import Milestone, Project, ProjectActivity, ProjectComment, ProjectInvitation, Task


class Command(BaseCommand):
    help = "Create a reusable demo workspace"

    def handle(self, *args, **options):
        freelancer, _ = User.objects.get_or_create(username="maya", defaults={"email": "maya@example.com", "first_name": "Maya", "last_name": "Chen", "role": "freelancer", "headline": "Product designer & Django developer", "bio": "I help thoughtful teams turn complex ideas into calm, useful digital products.", "location": "Tokyo, Japan", "skills": "Django, Product Design, Python, UX Strategy", "hourly_rate": 85})
        freelancer.set_password("demo12345")
        freelancer.save()
        client, _ = User.objects.get_or_create(username="jordan", defaults={"email": "jordan@example.com", "first_name": "Jordan", "last_name": "Lee", "role": "client", "headline": "Founder at Paper & Pine", "company": "Paper & Pine", "location": "Melbourne, Australia"})
        client.set_password("demo12345")
        client.save()
        project, _ = Project.objects.get_or_create(title="Brand website refresh", freelancer=freelancer, client=client, defaults={"description": "A clear, warm new website that makes the studio's work effortless to explore.", "status": "active", "budget": 6400, "deadline": date.today() + timedelta(days=30)})
        for title, done in [("Discovery & strategy", True), ("Visual direction", True), ("Homepage design", False), ("Django implementation", False)]:
            Task.objects.get_or_create(project=project, title=title, defaults={"completed": done})
        strategy, _ = Milestone.objects.get_or_create(project=project, title="Strategy approved", defaults={"description": "Audience, content and visual direction aligned.", "completed": True, "order": 1})
        launch, _ = Milestone.objects.get_or_create(project=project, title="Website launch", defaults={"description": "Production-ready build reviewed and published.", "due_date": project.deadline, "order": 2})
        project.tasks.filter(title__in=["Discovery & strategy", "Visual direction"]).update(milestone=strategy)
        project.tasks.filter(title__in=["Homepage design", "Django implementation"]).update(milestone=launch)
        ProjectComment.objects.get_or_create(project=project, author=client, body="The new direction feels warm and clear. Let’s carry this into the homepage.")
        demo_time, _ = TimeEntry.objects.get_or_create(project=project, user=freelancer, date=date.today(), description="Homepage visual design", defaults={"hours": 3.5})
        invoice, _ = Invoice.objects.get_or_create(project=project, number="INV-DEMO-001", defaults={"issued_on": date.today(), "due_on": date.today() + timedelta(days=14), "status": "sent", "notes": "Thank you for the thoughtful collaboration."})
        demo_item = InvoiceItem.objects.filter(invoice=invoice, source_time_entry=demo_time).first()
        if not demo_item:
            demo_item = InvoiceItem.objects.filter(invoice=invoice, description="Strategy and visual design").first()
        if not demo_item:
            demo_item = InvoiceItem(invoice=invoice)
        demo_item.source_time_entry = demo_time
        demo_item.description = f"{demo_time.date:%b %d} — {demo_time.description}"
        demo_item.quantity = demo_time.hours
        demo_item.rate = freelancer.hourly_rate or 85
        demo_item.save()
        Expense.objects.get_or_create(project=project, user=freelancer, vendor="Type Foundry", description="Webfont license", defaults={"date": date.today() - timedelta(days=2), "amount": 48, "billable": True})
        PortfolioItem.objects.get_or_create(owner=freelancer, title="Paper & Pine commerce experience", defaults={"summary": "A quieter, faster shopping experience that brought the studio's tactile brand online and improved product discovery.", "skills": "Django, UX Strategy, Product Design", "featured": True})
        completed, _ = Project.objects.get_or_create(title="Studio booking portal", freelancer=freelancer, client=client, defaults={"description": "A streamlined booking and client intake experience.", "status": "completed", "budget": 3800, "deadline": date.today() - timedelta(days=20)})
        Review.objects.get_or_create(project=completed, defaults={"reviewer": client, "freelancer": freelancer, "rating": 5, "body": "Maya brought clarity to every decision and delivered a portal our clients genuinely enjoy using."})
        ProjectInvitation.objects.get_or_create(inviter=freelancer, client_email="newclient@example.com", project_title="Product launch microsite", defaults={"client_name": "New Client", "project_description": "A focused launch experience for an upcoming product.", "budget": 2800, "deadline": date.today() + timedelta(days=45), "expires_at": timezone.now() + timedelta(days=14)})
        for actor, kind, text in [(freelancer, "project", "Created the project"), (client, "comment", "Posted a project update"), (freelancer, "time", "Logged 3.50 hours: Homepage visual design"), (freelancer, "invoice", "Created invoice INV-DEMO-001")]:
            ProjectActivity.objects.get_or_create(project=project, actor=actor, kind=kind, text=text)
        conversation = Conversation.objects.filter(participants=freelancer).filter(participants=client).first()
        if not conversation:
            conversation = Conversation.objects.create(project=project)
            conversation.participants.add(freelancer, client)
            Message.objects.create(conversation=conversation, sender=client, body="The new direction feels exactly right. Excited for the next round!")
        self.stdout.write(self.style.SUCCESS("Demo ready — log in as maya or jordan with password demo12345"))
