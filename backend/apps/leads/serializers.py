from rest_framework import serializers

from apps.leads.models import FundraisingFocus, LeadRequest, LeadSourcePage


class LeadRequestSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=120, trim_whitespace=True)
    email = serializers.EmailField(max_length=254)
    organisation = serializers.CharField(max_length=160, trim_whitespace=True)
    fundraising_focus = serializers.ChoiceField(choices=FundraisingFocus.choices)
    message = serializers.CharField(max_length=2000, trim_whitespace=True)
    source_page = serializers.ChoiceField(choices=LeadSourcePage.choices)
    website = serializers.CharField(max_length=200, required=False, allow_blank=True, trim_whitespace=True, write_only=True)

    class Meta:
        model = LeadRequest
        fields = (
            "id",
            "name",
            "email",
            "organisation",
            "fundraising_focus",
            "message",
            "source_page",
            "created_at",
            "status",
            "website",
        )
        read_only_fields = ("id", "created_at", "status")

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate(self, attrs):
        if attrs.pop("website", "").strip():
            raise serializers.ValidationError({"detail": "Unable to accept this request."})
        return attrs
