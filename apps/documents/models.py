from django.conf import settings
from django.db import models


class IncomeDNADocument(models.Model):
	STATUS_CHOICES = [
		("pending", "Pending"),
		("ready", "Ready"),
		("failed", "Failed"),
	]

	worker = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="income_dna_docs",
	)
	period_months = models.PositiveIntegerField(default=3)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
	pdf_file = models.FileField(upload_to="income_dna/", blank=True)
	signature_hex = models.CharField(max_length=256, blank=True)
	failure_reason = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"IncomeDNA #{self.pk} - {self.worker}"
