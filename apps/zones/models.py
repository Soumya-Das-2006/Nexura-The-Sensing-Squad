from django.db import models


class Zone(models.Model):
	city = models.CharField(max_length=100)
	area_name = models.CharField(max_length=120)
	state = models.CharField(max_length=100, blank=True)
	lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
	lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
	radius_km = models.DecimalField(max_digits=6, decimal_places=2, default=5)
	risk_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
	active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["city", "area_name"]

	def __str__(self):
		return self.display_name

	@property
	def display_name(self):
		return f"{self.area_name}, {self.city}"

	@property
	def risk_level(self):
		rm = float(self.risk_multiplier)
		if rm < 1.2:
			return "Low"
		if rm < 1.5:
			return "Moderate"
		if rm < 1.8:
			return "High"
		return "Critical"

	@property
	def risk_color(self):
		mapping = {
			"Low": "green",
			"Moderate": "amber",
			"High": "red",
			"Critical": "crimson",
		}
		return mapping.get(self.risk_level, "gray")
