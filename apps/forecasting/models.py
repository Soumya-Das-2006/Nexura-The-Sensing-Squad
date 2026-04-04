from django.db import models
from django.utils import timezone


class ZoneForecast(models.Model):
	zone = models.ForeignKey("zones.Zone", on_delete=models.CASCADE, related_name="forecasts")
	forecast_date = models.DateField()
	rain_probability = models.FloatField(default=0.0)
	heat_probability = models.FloatField(default=0.0)
	aqi_probability = models.FloatField(default=0.0)
	disruption_probability = models.FloatField(default=0.0)
	overall_risk_level = models.CharField(max_length=20, default="Low")
	forecasted_rain_mm = models.FloatField(default=0.0)
	forecasted_temp_c = models.FloatField(default=0.0)
	forecasted_aqi = models.FloatField(default=0.0)
	generated_at = models.DateTimeField(default=timezone.now)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-forecast_date", "zone__city"]
		unique_together = ("zone", "forecast_date")

	def __str__(self):
		return f"{self.zone} - {self.forecast_date}"

	@staticmethod
	def compute_risk_level(rain_probability, heat_probability, aqi_probability, disruption_probability):
		"""Return a categorical risk label from forecast probabilities."""
		score = max(
			float(rain_probability or 0.0),
			float(heat_probability or 0.0),
			float(aqi_probability or 0.0),
			float(disruption_probability or 0.0),
		)

		if score >= 0.85:
			return "Critical"
		if score >= 0.65:
			return "High"
		if score >= 0.35:
			return "Moderate"
		return "Low"

	@property
	def risk_color(self):
		return {
			"Low": "green",
			"Moderate": "amber",
			"High": "red",
			"Critical": "crimson",
		}.get(self.overall_risk_level, "gray")

	@property
	def risk_icon(self):
		return {
			"Low": "ok",
			"Moderate": "warn",
			"High": "alert",
			"Critical": "critical",
		}.get(self.overall_risk_level, "info")
