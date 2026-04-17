import logging
from django.core.management.base import BaseCommand
from apps.zones.models import Zone
from apps.triggers.tasks import create_manual_event

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fire a manual disruption trigger for a specific zone or all zones.'

    def add_arguments(self, parser):
        parser.add_argument('--zone', type=int, help='Zone ID to fire trigger for')
        parser.add_argument('--all-zones', action='store_true', help='Fire trigger for all active zones')
        parser.add_argument('--type', type=str, required=True, 
                            choices=['heavy_rain', 'extreme_heat', 'severe_aqi', 'flash_flood', 'curfew_strike', 'platform_down'],
                            help='Type of trigger to fire')
        parser.add_argument('--severity', type=float, required=True, help='Severity value (e.g. 42.0 for heat, 350 for aqi)')
        parser.add_argument('--partial', action='store_true', help='If passed, fires a partial trigger (50%% payout)')
        parser.add_argument('--platform', type=str, default='all', help='Affected platform (for platform_down triggers)')
        parser.add_argument('--sync', action='store_true', help='Run claim processing synchronously (no Celery needed)')

    def handle(self, *args, **options):
        zone_id = options.get('zone')
        all_zones = options.get('all_zones')
        trigger_type = options['type']
        severity = options['severity']
        is_full = not options['partial']
        platform = options['platform']
        sync = options['sync']

        if not zone_id and not all_zones:
            self.stdout.write(self.style.ERROR("You must specify either --zone <id> or --all-zones"))
            return

        zones = []
        if all_zones:
            zones = Zone.objects.filter(active=True)
            if not zones.exists():
                self.stdout.write(self.style.WARNING("No active zones found."))
                return
        else:
            try:
                zone = Zone.objects.get(pk=zone_id)
                zones = [zone]
            except Zone.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Zone with ID {zone_id} does not exist."))
                return

        for zone in zones:
            self.stdout.write(self.style.NOTICE(f"Firing {trigger_type} for zone {zone.pk}..."))
            
            # Since create_manual_event doesn't directly support affected_platform in its signature in tasks.py,
            # we will create the event directly if sync or if we modify create_manual_event.
            # But the user asked for sync flag. Let's do direct creation.
            
            from apps.triggers.tasks import _create_event
            thresholds_map = {
                'heavy_rain':    35.0,
                'extreme_heat':  42.0,
                'severe_aqi':    300.0,
                'flash_flood':   1.0,
                'curfew_strike': 1.0,
                'platform_down': 30.0,
            }

            event = _create_event(
                zone, trigger_type, severity,
                threshold=thresholds_map.get(trigger_type, 0),
                is_full=is_full, source_api='manual', affected_platform=platform
            )
            
            self.stdout.write(self.style.SUCCESS(f"Event created with ID {event.pk}"))

            from apps.claims.tasks import process_pending_claims
            if sync:
                self.stdout.write(self.style.NOTICE(f"Processing claims synchronously..."))
                process_pending_claims()
                self.stdout.write(self.style.SUCCESS(f"Claims processed for event {event.pk}"))
            else:
                self.stdout.write(self.style.NOTICE(f"Queuing claims processing task..."))
                process_pending_claims.delay()
                self.stdout.write(self.style.SUCCESS(f"Task queued for event {event.pk}"))
                
        self.stdout.write(self.style.SUCCESS("Finished firing triggers."))
