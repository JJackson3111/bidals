from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.audit.security import check_security_rate_limit, client_ip, rate_limited_response
from apps.leads.serializers import LeadRequestSerializer
from apps.leads.services import queue_lead_notification


class LeadRequestCreateView(generics.CreateAPIView):
    serializer_class = LeadRequestSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        ip_rate_limit = check_security_rate_limit(
            request,
            scope="lead_request_ip",
            identifier=client_ip(request),
            setting_name="RATE_LIMIT_LEAD_REQUESTS",
            default_rate="3/hour",
        )
        if not ip_rate_limit.allowed:
            return rate_limited_response(ip_rate_limit)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email_rate_limit = check_security_rate_limit(
            request,
            scope="lead_request_email",
            identifier=serializer.validated_data["email"],
            setting_name="RATE_LIMIT_LEAD_REQUESTS",
            default_rate="3/hour",
        )
        if not email_rate_limit.allowed:
            return rate_limited_response(email_rate_limit)

        lead = serializer.save()
        queue_lead_notification(lead)
        response_serializer = self.get_serializer(lead)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
