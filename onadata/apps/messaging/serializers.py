# -*- coding: utf-8 -*-
"""
Message serializers
"""

from __future__ import unicode_literals

from actstream.actions import action_handler
from actstream.models import Action
from actstream.signals import action
from onadata.apps.messaging.constants import MESSAGE
from onadata.apps.messaging.utils import TargetDoesNotExist, get_target
from rest_framework import exceptions, serializers


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer class for Message objects
    """
    TARGET_CHOICES = (('xform', 'XForm'), ('project', 'Project'),
                      ('user', 'User'))  # yapf: disable

    message = serializers.CharField(source='description', allow_blank=False)
    target_id = serializers.IntegerField(source='target_object_id')
    target_type = serializers.ChoiceField(
        TARGET_CHOICES, source='target_content_type')

    class Meta:
        model = Action
        fields = ['id', 'message', 'target_id', 'target_type']

    def create(self, validated_data):
        """
        Creates the Message in the Action model
        """
        request = self.context['request']
        target_type = validated_data.get("target_content_type")
        target_id = validated_data.get("target_object_id")
        try:
            content_type = get_target(target_type)
        except TargetDoesNotExist:
            raise serializers.ValidationError({
                'target_type': 'Unknown target type'
            })  # yapf: disable
        else:
            try:
                target_object = \
                    content_type.get_object_for_this_type(pk=target_id)
            except content_type.model_class().DoesNotExist:
                raise serializers.ValidationError({
                    'target_id': 'target_id not found'
                })  # yapf: disable
            else:
                # check if request.user has permission to the target_object
                permission = '{}.change_{}'.format(
                    target_object._meta.app_label,
                    target_object._meta.model_name)
                if not request.user.has_perm(permission, target_object):
                    message = ("You do not have permission to add messages "
                               "to target_id %s." % target_object)
                    raise exceptions.PermissionDenied(detail=message)
                results = action.send(
                    request.user,
                    verb=MESSAGE,
                    target=target_object,
                    description=validated_data.get("description"))

                # results will be a list of tuples with the first item in the
                # tuple being the signal handler function and the second
                # being the object.  We want to get the object of the first
                # element in the list whose function is 'action_handler'
                results = [x for x in results if x[0] == action_handler]
                if not results:
                    raise serializers.ValidationError(
                        "Message not created. Please retry.")

                return results[0][1]
