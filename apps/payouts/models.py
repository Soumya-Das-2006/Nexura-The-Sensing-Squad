from django.conf import settings
from django.db import models
from django.utils import timezone


class Payout(models.Model):
	MODE_CHOICES = [
		("upi", "UPI"),
		("imps", "IMPS"),
		("neft", "NEFT"),
	]
	STATUS_CHOICES = [
		("queued", "Queued"),
		("processing", "Processing"),
		("pending", "Pending"),
		("credited", "Credited"),
		("failed", "Failed"),
		("reversed", "Reversed"),
	]

	claim = models.OneToOneField("claims.Claim", on_delete=models.SET_NULL, null=True, blank=True, related_name="payout")
	worker = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="payouts",
	)
	amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="upi")
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
	utr_number = models.CharField(max_length=80, blank=True)
	failure_reason = models.TextField(blank=True)
	retry_count = models.PositiveIntegerField(default=0)
	initiated_at = models.DateTimeField(default=timezone.now)
	credited_at = models.DateTimeField(null=True, blank=True)
	razorpay_payout_id = models.CharField(max_length=120, blank=True)
	razorpay_fund_acct_id = models.CharField(max_length=120, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-initiated_at"]

	def __str__(self):
		return f"Payout #{self.pk} - {self.worker}"

	@property
	def time_to_credit(self):
		if not self.credited_at:
			return ""
		delta = self.credited_at - self.initiated_at
		mins = int(delta.total_seconds() // 60)
		return f"{mins} min"
