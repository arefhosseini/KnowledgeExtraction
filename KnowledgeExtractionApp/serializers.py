from rest_framework import serializers
from .models import Relation, Text


class RelationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Relation
        fields = ('id', 'subject', 'predicate', 'object')


class TextSerializer(serializers.ModelSerializer):

    class Meta:
        model = Text
        fields = '__all__'
