from apps.leads.models import LeadRequest


def queue_lead_notification(_lead: LeadRequest) -> None:
    # TODO: Wire lead notifications to a configured BIDALS business recipient once that recipient setting exists.
    return None
