from django.conf import settings
from django.db import models


class PremiumPayment(models.Model):
	STATUS_CHOICES = [
		("pending", "Pending"),
		("captured", "Captured"),
		("failed", "Failed"),
		("grace", "Grace"),
		("refunded", "Refunded"),
	]

	policy = models.ForeignKey("policies.Policy", on_delete=models.CASCADE, related_name="payments")
	worker = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="premium_payments",
	)
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	week_start_date = models.DateField()
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
	failure_reason = models.TextField(blank=True)
	razorpay_payment_id = models.CharField(max_length=120, blank=True)
	razorpay_order_id = models.CharField(max_length=120, blank=True)
	razorpay_subscription_id = models.CharField(max_length=120, blank=True)
	razorpay_signature = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-week_start_date", "-created_at"]
		unique_together = ("policy", "week_start_date")

	def __str__(self):
		return f"Payment #{self.pk} - {self.worker}"

	@property
	def week_label(self):
		return self.week_start_date.strftime("%d %b %Y")

	def capture(self, razorpay_payment_id=""):
		self.status = "captured"
		if razorpay_payment_id:
			self.razorpay_payment_id = razorpay_payment_id
			self.save(update_fields=["status", "razorpay_payment_id", "updated_at"])
			return
		self.save(update_fields=["status", "updated_at"])

	def fail(self, reason=""):
		self.status = "failed"
		self.failure_reason = reason or "Payment failed"
		self.save(update_fields=["status", "failure_reason", "updated_at"])
