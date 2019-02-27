from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, ListCreateAPIView


class SUDCaseView(APIView):

    def get(self, request):
        return Response(status=status.HTTP_200_OK)
