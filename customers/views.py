from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from customers.models import WorkshopCustomer
from customers.serializers import WorkshopCustomerSerializer
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework.decorators import action


class SmallResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class WorkshopCustomersViewSet(viewsets.ModelViewSet):
    queryset = WorkshopCustomer.objects.all().order_by("-updated_at")
    serializer_class = WorkshopCustomerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SmallResultsSetPagination

    def get(self, request):
        user = request.user
        customers = WorkshopCustomer.objects.filter()
        serializer = WorkshopCustomerSerializer(customers, many=True)

        return Response(
            {"data": {"customers": serializer.data}}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        user = request.user
        q = (request.query_params.get("q") or "").strip()
        qs = self.get_queryset()

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(surname__icontains=q)
                | Q(name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(document_number=q)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = WorkshopCustomerSerializer(page, many=True)

        return paginator.get_paginated_response({"data": serializer.data, "query": q})
