"""
Management command to test WAQI API integration.
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from apps.zones.models import Zone
from apps.triggers.services.aqi import AQIService, AQIAPIError

class Command(BaseCommand):
    help = 'Tests the WAQI AQI integration for zones.'

    def add_arguments(self, parser):
        parser.add_argument('--city', type=str, help='Filter by city')
        parser.add_argument('--zone', type=int, help='Filter by zone ID')
        parser.add_argument('--force-live', action='store_true', help='Skip cache and hit API directly')

    def handle(self, *args, **options):
        city = options['city']
        zone_id = options['zone']
        force_live = options['force_live']

        zones = Zone.objects.filter(active=True)
        if city:
            zones = zones.filter(city__iexact=city)
        if zone_id:
            zones = zones.filter(id=zone_id)

        if not zones.exists():
            self.stdout.write(self.style.WARNING("No zones found matching criteria."))
            return

        if force_live:
            # Clear caches for these cities to force a live fetch
            cities = set(zones.values_list('city', flat=True))
            for c in cities:
                cache_key = f"waqi_city_{c.replace(' ', '_').lower()}"
                cache.delete(cache_key)
            self.stdout.write(self.style.WARNING("Cache cleared due to --force-live"))

        service = AQIService()
        self.stdout.write(self.style.SUCCESS(f"Testing AQI for {zones.count()} zones..."))

        for zone in zones:
            self.stdout.write(f"Fetching AQI for {zone.display_name}...")
            try:
                data = service.fetch_aqi(zone)
                cached = data.raw_payload.get('cached', False)
                source_str = "CACHE HIT" if cached else "LIVE API"
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [{source_str}] AQI: {data.aqi_value} ({data.category}) | Station: {data.station_name}"
                    )
                )
            except AQIAPIError as e:
                self.stdout.write(self.style.ERROR(f"  Failed: {e}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Unexpected error: {e}"))

        self.stdout.write(self.style.SUCCESS("Done."))
