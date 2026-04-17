import uuid
from django.db import models


class FraudFlag(models.Model):
	LAYER_CHOICES = [
		(1, "Layer 1"),
		(2, "Layer 2"),
		(3, "Layer 3"),
		(4, "Layer 4"),
		(5, "Layer 5"),
		(6, "Layer 6"),
	]

	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	claim = models.ForeignKey("claims.Claim", on_delete=models.CASCADE, related_name="fraud_flag_records")
	layer = models.PositiveSmallIntegerField(choices=LAYER_CHOICES, default=1)
	flag_type = models.CharField(max_length=80)
	score_contribution = models.FloatField(default=0.0)
	detail = models.TextField(blank=True)
	is_deleted = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["layer", "created_at"]
		indexes = [
			models.Index(fields=['claim', 'is_deleted']),
		]

	def __str__(self):
		return f"Claim #{self.claim_id} - {self.flag_type}"

	def soft_delete(self):
		self.is_deleted = True
		self.save(update_fields=['is_deleted', 'updated_at'])
