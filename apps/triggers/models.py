import uuid
from django.db import models
from django.utils import timezone


class DisruptionEvent(models.Model):
	TRIGGER_CHOICES = [
		("heavy_rain", "Heavy Rain"),
		("extreme_heat", "Extreme Heat"),
		("severe_aqi", "Severe AQI"),
		("flash_flood", "Flash Flood"),
		("curfew_strike", "Curfew or Strike"),
		("platform_down", "Platform Down"),
	]

	zone = models.ForeignKey("zones.Zone", on_delete=models.CASCADE, related_name="disruptions")
	trigger_type = models.CharField(max_length=32, choices=TRIGGER_CHOICES)
	severity_value = models.FloatField(default=0.0)
	threshold_value = models.FloatField(default=0.0)
	is_full_trigger = models.BooleanField(default=True)
	claims_generated = models.BooleanField(default=False)
	affected_platform = models.CharField(max_length=50, blank=True)
	started_at = models.DateTimeField(default=timezone.now)
	ended_at = models.DateTimeField(null=True, blank=True)
	source_api = models.CharField(max_length=100, blank=True)
	raw_payload = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-started_at"]

	def __str__(self):
		return f"{self.get_trigger_type_display()} @ {self.zone}"

	@property
	def duration_hours(self):
		end = self.ended_at or timezone.now()
		return round((end - self.started_at).total_seconds() / 3600, 2)

	@property
	def icon(self):
		return {
			"heavy_rain": "rain",
			"extreme_heat": "heat",
			"severe_aqi": "aqi",
			"flash_flood": "flood",
			"curfew_strike": "curfew",
			"platform_down": "platform",
		}.get(self.trigger_type, "event")

	@property
	def color(self):
		return {
			"heavy_rain": "blue",
			"extreme_heat": "red",
			"severe_aqi": "amber",
			"flash_flood": "cyan",
			"curfew_strike": "slate",
			"platform_down": "gray",
		}.get(self.trigger_type, "gray")

	def close(self):
		if not self.ended_at:
			self.ended_at = timezone.now()
			self.save(update_fields=["ended_at", "updated_at"])


class PlatformDowntimeState(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	platform_name = models.CharField(max_length=50)
	down_since = models.DateTimeField(default=timezone.now)
	is_deleted = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		indexes = [
			models.Index(fields=['platform_name', 'is_deleted']),
		]

	def __str__(self):
		return f"{self.platform_name} down since {self.down_since}"

	def soft_delete(self):
		self.is_deleted = True
		self.save(update_fields=['is_deleted', 'updated_at'])
