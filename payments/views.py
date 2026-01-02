from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
from django.shortcuts import redirect
from django.db.models import Sum
from .models import Payment
from .serializers import PaymentSerializer, PaymentCreateSerializer, PaymentWebhookSerializer
from .permissions import IsAdminOrReceptionist
from core.mixins import CacheResponseMixin, CacheInvalidationMixin


class PaymentViewSet(CacheResponseMixin, CacheInvalidationMixin, viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related('patient')
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    cache_key_prefix = "payment"

    def get_permissions(self):
        if self.action == 'webhook':
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        if self.action == 'webhook':
            return PaymentWebhookSerializer
        return PaymentSerializer

    def get_cache_keys_to_invalidate(self, instance):
        return [
            "all_payments", 
            f"payment_{instance.id}",
            "payment_total_amount",
            "payment_today_total"
        ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        self._invalidate_cache(payment)
        
        if payment.payment_method == 'chapa':
            checkout = serializer.get_payment_url(payment)
            return Response({"payment_url": checkout, "reference": payment.reference}, status=status.HTTP_201_CREATED)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get", "post"], url_path="webhook", url_name="webhook", permission_classes=[permissions.AllowAny])
    def webhook(self, request):
        data = self._get_webhook_data(request)
        
        serializer = self.get_serializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        self._invalidate_cache(payment)
        
        if request.method == "GET":
            return self._redirect_to_frontend(payment)
        
        return Response({"message": "Payment status updated", "status": payment.status})

    def _get_webhook_data(self, request):
        if request.method == "GET":
            tx_ref = (request.query_params.get('trx_ref') or 
                     request.query_params.get('tx_ref') or
                     request.query_params.get('reference'))
            return {'tx_ref': tx_ref}
        return request.data

    def _redirect_to_frontend(self, payment):
        return_url = getattr(settings, 'PAYMENT_RETURN_URL', None) or 'http://localhost:5173/payment/callback'
        separator = '&' if '?' in return_url else '?'
        frontend_url = f"{return_url}{separator}tx_ref={payment.reference}&status={payment.status}"
        return redirect(frontend_url)

    @action(detail=False, methods=['get'])
    def today(self, request):
        today_date = timezone.now().date()
        queryset = self.get_queryset().filter(created_at__date=today_date)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrReceptionist])
    def total_amount(self, request):
        total = Payment.objects.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
        return Response({"total_amount": float(total)})

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrReceptionist])
    def today_total(self, request):
        today_date = timezone.now().date()
        total = Payment.objects.filter(status='paid', created_at__date=today_date).aggregate(Sum('amount'))['amount__sum'] or 0
        return Response({"today_total": float(total)})
