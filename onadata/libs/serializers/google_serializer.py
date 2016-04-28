from oauth2client.contrib.django_orm import Storage

from django.http import HttpResponseRedirect
from rest_framework import serializers

from onadata.apps.main.models import TokenStorageModel
from onadata.libs.utils.google import google_flow
from onadata.libs.serializers.fields.xform_field import XFormField
from onadata.libs.models.google_sheet_webhook import GoogleSheetService
from onadata.libs.utils.api_export_tools import _get_google_credential


class GoogleCredentialSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=255, required=True)

    def save(self):
        self.is_valid(raise_exception=True)

        request = self.context.get('request')
        storage = Storage(TokenStorageModel, 'id', request.user,
                          'credential')
        code = self.validated_data['code']
        google_creds = google_flow.step2_exchange(code)
        google_creds.set_store(storage)
        storage.put(google_creds)


class GoogleSheetsSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    name = serializers.CharField(max_length=50, required=True)
    service_url = serializers.URLField(default="https://drive.google.com")
    xform = XFormField()
    google_sheet_title = serializers.CharField(max_length=255, required=True)
    send_existing_data = serializers.BooleanField(default=True)
    sync_updates = serializers.BooleanField(default=True)

    def validate(self, attrs):
        request = self.context.get('request')
        if request and request.user and not request.user.is_anonymous():
            response = _get_google_credential(request)
            if isinstance(response, HttpResponseRedirect):
                error = {
                    u"details": u"Google Authorization needed",
                    u"url": response.url
                 }
                raise serializers.ValidationError(error)
        else:
            raise serializers.ValidationError(u"Authentication required")

        return attrs

    def save(self):
        self.is_valid(raise_exception=True)
        # Get the authenticated user
        request = self.context.get('request')
        instance = GoogleSheetService(user=request.user, **self.validated_data)
        instance.save()

        return instance