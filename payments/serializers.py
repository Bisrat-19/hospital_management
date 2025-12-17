from rest_framework import serializers
from django.conf import settings
from django.urls import reverse
from decimal import Decimal, InvalidOperation
import uuid, requests
from .models import Payment
from patients.models import Patient
from rest_framework.exceptions import APIException
from .utils import get_chapa_secret_key

CHAPA_INITIALIZE_URL = "https://api.chapa.co/v1/transaction/initialize"
CHAPA_VERIFY_URL = "https://api.chapa.co/v1/transaction/verify/{}"

class ServerConfigError(APIException):
    status_code = 500
    default_detail = "Payment gateway not configured"
    default_code = "payment_config_error"

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['status', 'reference', 'created_at', 'updated_at']

class PaymentCreateSerializer(serializers.ModelSerializer):
    patient_id = serializers.IntegerField(write_only=True)
    payment_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'patient_id', 'amount', 'payment_method', 'status', 'reference', 'payment_url', 'created_at', 'updated_at']
        read_only_fields = ['status', 'reference', 'created_at', 'updated_at']

    def validate_amount(self, value):
        try:
            amount = Decimal(str(value))
            if amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, TypeError):
            raise serializers.ValidationError("Invalid amount")
        return amount

    def validate_payment_method(self, value):
        if value not in ("cash", "chapa"):
            raise serializers.ValidationError("payment_method must be 'cash' or 'chapa'")
        return value

    def validate_patient_id(self, value):
        if not Patient.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid patient_id")
        if Payment.objects.filter(patient_id=value, status='paid').exists():
            raise serializers.ValidationError("Patient already has a successful payment")
        return value

    def create(self, validated):
        patient = Patient.objects.get(id=validated.pop("patient_id"))
        if Payment.objects.filter(patient=patient, status='paid').exists():
            raise serializers.ValidationError("Patient already has a successful payment")
        method = validated.get("payment_method")
        reference = str(uuid.uuid4())
        payment = Payment.objects.create(
            patient=patient,
            amount=validated["amount"],
            payment_method=method,
            reference=reference,
            status='pending'
        )
        self._checkout_url = None
        if method == "cash":
            payment.status = "paid"
            payment.save(update_fields=["status", "updated_at"])
            return payment

        # chapa flow
        secret_key = get_chapa_secret_key()
        if not secret_key:
            payment.status = "failed"
            payment.save(update_fields=["status", "updated_at"])
            raise ServerConfigError("CHAPA_SECRET_KEY not configured (load .env or set in settings)")

        req = self.context.get("request")
        callback_url = req.build_absolute_uri(reverse("payment-webhook")) if req else ""
        return_url = getattr(settings, "PAYMENT_RETURN_URL", None) or callback_url
        
        # Append transaction reference to return URL so we have it when user is redirected
        if return_url:
            separator = '&' if '?' in return_url else '?'
            return_url = f"{return_url}{separator}tx_ref={reference}"

        # Always use configured default email; patients may not have email
        default_email = getattr(settings, "DEFAULT_PAYMENT_EMAIL", None)
        if not default_email or "@" not in default_email:
            raise ServerConfigError("DEFAULT_PAYMENT_EMAIL not configured or invalid")
        email = default_email

        title = "Card Payment"[:16]
        payload = {
            "amount": str(payment.amount),
            "currency": "ETB",
            "email": email,
            "first_name": getattr(patient, "first_name", "") or "",
            "last_name": getattr(patient, "last_name", "") or "",
            "tx_ref": reference,
            "callback_url": callback_url,
            "return_url": return_url,
            "customization": {"title": title},
        }

        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(CHAPA_INITIALIZE_URL, json=payload, headers=headers, timeout=20)
            try:
                data = resp.json()
            except ValueError:
                data = {"status": "error", "message": resp.text}
        except Exception:
            payment.status = "failed"
            payment.save(update_fields=["status", "updated_at"])
            raise serializers.ValidationError("Failed to reach Chapa")

        if data.get("status") == "success" and data.get("data", {}).get("checkout_url"):
            self._checkout_url = data["data"]["checkout_url"]
            return payment

        error_fields = data.get("data") if isinstance(data.get("data"), dict) else {}
        gateway_msg = data.get("message") or "Failed to initialize Chapa payment"
        payment.status = "failed"
        payment.save(update_fields=["status", "updated_at"])
        if error_fields:
            raise serializers.ValidationError(error_fields)
        raise serializers.ValidationError({"detail": gateway_msg})

    def get_payment_url(self, obj):
        return getattr(self, "_checkout_url", None)

    def build_response(self, payment):
        # Centralized payment response used by patient serializer
        data = {
            "id": payment.id,
            "amount": str(payment.amount),
            "payment_method": payment.payment_method,
            "status": payment.status,
            "reference": payment.reference,
        }
        if payment.payment_method == "chapa":
            url = self.get_payment_url(payment)
            if url:
                data["payment_url"] = url
        return data

class PaymentWebhookSerializer(serializers.Serializer):
    tx_ref = serializers.CharField()

    def validate_tx_ref(self, value):
        if not Payment.objects.filter(reference=value).exists():
            raise serializers.ValidationError("Payment not found")
        return value

    def save(self, **kwargs):
        secret_key = get_chapa_secret_key()
        if not secret_key:
            raise ServerConfigError("CHAPA_SECRET_KEY not configured (load .env or set in settings)")
        tx_ref = self.validated_data["tx_ref"]
        payment = Payment.objects.get(reference=tx_ref)
        headers = {
            "Authorization": f"Bearer {secret_key}",
        }
        try:
            resp = requests.get(CHAPA_VERIFY_URL.format(tx_ref), headers=headers, timeout=20)
            data = resp.json()
        except Exception:
            raise serializers.ValidationError("Verification request failed")
        status_value = (data or {}).get("status")
        is_paid = status_value == "success" and (data.get("data") or {}).get("tx_ref") == tx_ref
        payment.status = "paid" if is_paid else "failed"
        payment.save(update_fields=["status", "updated_at"])
        return payment
