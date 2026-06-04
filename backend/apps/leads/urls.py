from django.urls import path

from apps.leads.views import LeadRequestCreateView


urlpatterns = [
    path("leads/", LeadRequestCreateView.as_view(), name="lead-request-create"),
]
