from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class WorkerProfile(models.Model):
	PLATFORM_CHOICES = [
		("zomato", "Zomato"),
		("swiggy", "Swiggy"),
		("amazon", "Amazon Flex"),
		("zepto", "Zepto"),
		("blinkit", "Blinkit"),
		("dunzo", "Dunzo"),
		("other", "Other"),
	]

	SEGMENT_CHOICES = [
		("bike", "Bike"),
		("bicycle", "Bicycle"),
		("auto", "Auto Rickshaw"),
		("car", "Car"),
	]

	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="workerprofile",
	)
	name = models.CharField(max_length=120)
	platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default="other")
	segment = models.CharField(max_length=20, choices=SEGMENT_CHOICES, default="bike")
	zone = models.ForeignKey(
		"zones.Zone",
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="workers",
	)

	upi_id = models.CharField(
		max_length=100,
		blank=True,
		validators=[
			RegexValidator(
				regex=r'^[a-zA-Z0-9._-]+@[a-zA-Z]{2,}$',
				message='Enter a valid UPI ID (e.g. name@upi, name@paytm, name@oksbi).',
			)
		],
	)

	risk_score = models.FloatField(default=0.0)
	risk_updated_at = models.DateTimeField(null=True, blank=True)

	grace_tokens = models.PositiveIntegerField(default=0)

	razorpay_contact_id = models.CharField(max_length=120, blank=True)
	razorpay_fund_acct_id = models.CharField(max_length=120, blank=True)
	razorpay_mandate_id = models.CharField(max_length=120, blank=True)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.user.mobile} - {self.name}"

	@property
	def city(self):
		return self.zone.city if self.zone_id else ""

	@property
	def risk_label(self):
		if self.risk_score < 0.35:
			return "Low"
		if self.risk_score < 0.70:
			return "Medium"
		return "High"

	@property
	def risk_color(self):
		if self.risk_score < 0.35:
			return "green"
		if self.risk_score < 0.70:
			return "amber"
		return "red"

	@property
	def razorpay_ready(self):
		return bool(self.upi_id and self.razorpay_contact_id and self.razorpay_fund_acct_id)

	def kyc_status(self):
		if hasattr(self.user, "kyc"):
			return self.user.kyc.status
		return "pending"
