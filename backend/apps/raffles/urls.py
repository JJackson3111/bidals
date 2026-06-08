from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.raffles.views import MyRaffleTicketsView, RaffleCampaignViewSet

router = DefaultRouter()
router.register("raffles", RaffleCampaignViewSet, basename="raffle")

urlpatterns = [
    path("raffle-tickets/mine/", MyRaffleTicketsView.as_view(), name="my-raffle-tickets"),
    *router.urls,
]
