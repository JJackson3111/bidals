from rest_framework.routers import DefaultRouter
from django.urls import path

from apps.auctions.views import (
    AuctionViewSet,
    FulfillmentDetailView,
    FulfillmentListView,
    FulfillmentTimelineView,
    LotViewSet,
    OutcomeRepairActionView,
    OutcomeRepairAuditView,
    OutcomeRepairCommentsView,
    OutcomeRepairDetailView,
    OutcomeRepairListView,
    WinnerReviewView,
    WonLotTimelineView,
    WonLotsView,
)

router = DefaultRouter()
router.register("auctions", AuctionViewSet, basename="auction")
router.register("lots", LotViewSet, basename="lot")

urlpatterns = [
    path("dashboard/winners/", WinnerReviewView.as_view(), name="dashboard-winners"),
    path("dashboard/fulfillment/", FulfillmentListView.as_view(), name="dashboard-fulfillment"),
    path("dashboard/fulfillment/<int:pk>/", FulfillmentDetailView.as_view(), name="dashboard-fulfillment-detail"),
    path("dashboard/fulfillment/<int:pk>/timeline/", FulfillmentTimelineView.as_view(), name="dashboard-fulfillment-timeline"),
    path("admin/outcome-repairs/", OutcomeRepairListView.as_view(), name="admin-outcome-repairs"),
    path("admin/outcome-repairs/<int:pk>/", OutcomeRepairDetailView.as_view(), name="admin-outcome-repair-detail"),
    path("admin/outcome-repairs/<int:pk>/audit/", OutcomeRepairAuditView.as_view(), name="admin-outcome-repair-audit"),
    path("admin/outcome-repairs/<int:pk>/comments/", OutcomeRepairCommentsView.as_view(), name="admin-outcome-repair-comments"),
    path("admin/outcome-repairs/<int:pk>/approve/", OutcomeRepairActionView.as_view(action_name="approve"), name="admin-outcome-repair-approve"),
    path("admin/outcome-repairs/<int:pk>/reject/", OutcomeRepairActionView.as_view(action_name="reject"), name="admin-outcome-repair-reject"),
    path("admin/outcome-repairs/<int:pk>/apply/", OutcomeRepairActionView.as_view(action_name="apply"), name="admin-outcome-repair-apply"),
    path("account/won-lots/", WonLotsView.as_view(), name="account-won-lots"),
    path("account/won-lots/<int:pk>/timeline/", WonLotTimelineView.as_view(), name="account-won-lot-timeline"),
    *router.urls,
]
