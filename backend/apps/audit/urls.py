from rest_framework.routers import DefaultRouter
from django.urls import path

from apps.audit.views import (
    AccountNotificationListView,
    AccountNotificationReadView,
    AccountNotificationUnreadCountView,
    AccountNotificationsMarkAllReadView,
    AdminActivityExportView,
    AuditLogViewSet,
    OperationsSummaryView,
    ReleaseCheckView,
)

router = DefaultRouter()
router.register("audit", AuditLogViewSet, basename="audit")

urlpatterns = [
    path("admin/activity/export/", AdminActivityExportView.as_view(), name="admin-activity-export"),
    path("admin/release-check/", ReleaseCheckView.as_view(), name="admin-release-check"),
    path("account/notifications/", AccountNotificationListView.as_view(), name="account-notifications"),
    path("account/notifications/unread-count/", AccountNotificationUnreadCountView.as_view(), name="account-notifications-unread-count"),
    path("account/notifications/<int:pk>/read/", AccountNotificationReadView.as_view(), name="account-notification-read"),
    path("account/notifications/mark-all-read/", AccountNotificationsMarkAllReadView.as_view(), name="account-notifications-mark-all-read"),
    path("operations/", OperationsSummaryView.as_view(), name="operations-summary"),
    *router.urls,
]
