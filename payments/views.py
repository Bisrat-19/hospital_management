from rest_framework import status, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
from .models import Payment
from .serializers import PaymentSerializer, PaymentCreateSerializer, PaymentWebhookSerializer


from core.mixins import CacheResponseMixin


class PaymentViewSet(CacheResponseMixin, viewsets.ModelViewSet):
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        if payment.payment_method == 'chapa':
            checkout = serializer.get_payment_url(payment)
            return Response({"payment_url": checkout, "reference": payment.reference}, status=status.HTTP_201_CREATED)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get", "post"], url_path="webhook", url_name="webhook", permission_classes=[permissions.AllowAny])
    def webhook(self, request):
        if request.method == "GET":
            tx_ref = (request.query_params.get('trx_ref') or 
                     request.query_params.get('tx_ref') or
                     request.query_params.get('reference'))
            
            if not tx_ref:
                available_params = dict(request.query_params)
                return Response({
                    "error": "Missing transaction reference",
                    "available_params": available_params
                }, status=status.HTTP_400_BAD_REQUEST)
            
            data = {'tx_ref': tx_ref}
        else:
            data = request.data
        
        serializer = self.get_serializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        
        if request.method == "GET":
            from django.shortcuts import redirect
            return_url = getattr(settings, 'PAYMENT_RETURN_URL', None) or 'http://localhost:5173/payment/callback'
            separator = '&' if '?' in return_url else '?'
            frontend_url = f"{return_url}{separator}tx_ref={payment.reference}&status={payment.status}"
            return redirect(frontend_url)
        
        return Response({"message": "Payment status updated", "status": payment.status})

    @action(detail=False, methods=['get'])
    def today(self, request):
        today = timezone.now().date()
        queryset = self.get_queryset().filter(created_at__date=today)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
