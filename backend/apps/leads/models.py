from django.core.validators import MaxLengthValidator
from django.db import models
from django.utils import timezone


class LeadStatus(models.TextChoices):
    NEW = "new", "New"
    REVIEWED = "reviewed", "Reviewed"
    CONTACTED = "contacted", "Contacted"
    ARCHIVED = "archived", "Archived"


class LeadSourcePage(models.TextChoices):
    BOOK_DEMO = "book_demo", "Book demo"
    CONTACT = "contact", "Contact"


class FundraisingFocus(models.TextChoices):
    AUCTIONS = "auctions", "Auctions"
    RAFFLES = "raffles", "Raffles"
    DONATIONS = "donations", "Donations"
    MULTI_CHANNEL = "multi_channel", "Multi-channel event"
    GENERAL_ENQUIRY = "general_enquiry", "General enquiry"
    PARTNERSHIP = "partnership", "Partnership"
    SUPPORT = "support", "Support"
    OTHER = "other", "Other"


class LeadRequest(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(max_length=254)
    organisation = models.CharField(max_length=160)
    fundraising_focus = models.CharField(max_length=40, choices=FundraisingFocus.choices)
    message = models.TextField(validators=(MaxLengthValidator(2000),))
    source_page = models.CharField(max_length=40, choices=LeadSourcePage.choices)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=LeadStatus.choices, default=LeadStatus.NEW)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("status", "-created_at"), name="lead_status_created_idx"),
            models.Index(fields=("source_page", "-created_at"), name="lead_source_created_idx"),
            models.Index(fields=("email", "-created_at"), name="lead_email_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.organisation} - {self.email}"
