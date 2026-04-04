from django.conf import settings
from django.db import models


class RiskCircle(models.Model):
	name = models.CharField(max_length=120)
	description = models.TextField(blank=True)
	zone = models.ForeignKey("zones.Zone", on_delete=models.CASCADE, related_name="risk_circles")
	pool_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
	max_members = models.PositiveIntegerField(default=50)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["name"]

	def __str__(self):
		return self.name

	@property
	def member_count(self):
		return self.memberships.filter(is_active=True).count()

	@property
	def is_full(self):
		return self.member_count >= self.max_members


class CircleMembership(models.Model):
	worker = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="circle_memberships",
	)
	circle = models.ForeignKey(RiskCircle, on_delete=models.CASCADE, related_name="memberships")
	is_active = models.BooleanField(default=True)
	contribution_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	joined_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-joined_at"]

	def __str__(self):
		return f"{self.worker} in {self.circle}"
