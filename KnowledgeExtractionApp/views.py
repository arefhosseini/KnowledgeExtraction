from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from KnowledgeExtractionApp.serializers import TextSerializer
from .sparql_wrapper import *


class ResourceRelation(APIView):

    def post(self, request):
        text_serializer = TextSerializer(data=request.data)
        if text_serializer.is_valid():
            sparql = Sparql(text_serializer['text'].value)

            return sparql.get_json_relations()
        return Response(text_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
