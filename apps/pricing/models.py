from django.db import models
from django.conf import settings

class PricingHistory(models.Model):
    worker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pricing_history')
    plan_tier = models.ForeignKey('policies.PlanTier', on_delete=models.SET_NULL, null=True)
    risk_score = models.FloatField()
    calculated_premium = models.DecimalField(max_digits=10, decimal_places=2)
    base_premium = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-effective_from', '-created_at']

    def __str__(self):
        return f"{self.worker.mobile} - {self.plan_tier.name if self.plan_tier else 'Unknown'} - Rs{self.calculated_premium}"
