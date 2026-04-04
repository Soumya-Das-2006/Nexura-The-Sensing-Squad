from django.conf import settings
from django.db import models
from django.utils import timezone


class Claim(models.Model):
	STATUS_CHOICES = [
		("pending", "Pending"),
		("approved", "Approved"),
		("rejected", "Rejected"),
		("on_hold", "On Hold"),
	]

	worker = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="claims",
	)
	policy = models.ForeignKey("policies.Policy", on_delete=models.SET_NULL, null=True, blank=True, related_name="claims")
	disruption_event = models.ForeignKey("triggers.DisruptionEvent", on_delete=models.SET_NULL, null=True, blank=True, related_name="claims")
	payout_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	fraud_score = models.FloatField(default=0.0)
	fraud_flags = models.JSONField(default=list, blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
	rejection_reason = models.TextField(blank=True)
	reviewed_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="reviewed_claims",
	)
	reviewed_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"Claim #{self.pk} - {self.worker}"

	@property
	def fraud_tier(self):
		if self.fraud_score < 0.5:
			return "Low"
		if self.fraud_score < 0.7:
			return "Medium"
		return "High"

	@property
	def fraud_color(self):
		if self.fraud_score < 0.5:
			return "green"
		if self.fraud_score < 0.7:
			return "amber"
		return "red"

	@property
	def trigger_icon(self):
		if self.disruption_event:
			return self.disruption_event.icon
		return "event"

	@property
	def has_payout(self):
		return hasattr(self, "payout")

	def approve(self, reviewed_by=None):
		self.status = "approved"
		self.rejection_reason = ""
		self.reviewed_by = reviewed_by
		self.reviewed_at = timezone.now()
		self.save(update_fields=["status", "rejection_reason", "reviewed_by", "reviewed_at", "updated_at"])

	def reject(self, reason="", reviewed_by=None):
		self.status = "rejected"
		self.rejection_reason = reason or "Rejected"
		self.reviewed_by = reviewed_by
		self.reviewed_at = timezone.now()
		self.save(update_fields=["status", "rejection_reason", "reviewed_by", "reviewed_at", "updated_at"])
