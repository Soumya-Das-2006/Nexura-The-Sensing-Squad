"""
Management command — bulk recompute risk scores for all workers.

Usage:
    python manage.py update_risk_scores
    python manage.py update_risk_scores --worker-id 42
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Recompute and save risk_score for all WorkerProfiles"

    def add_arguments(self, parser):
        parser.add_argument(
            "--worker-id",
            type=int,
            help="Update a single worker by WorkerProfile ID",
        )

    def handle(self, *args, **options):
        from django.utils import timezone
        from apps.workers.models import WorkerProfile
        from apps.pricing.risk_service import predict_risk_score, _load

        if not _load():
            self.stderr.write("ERROR: Risk model failed to load. Aborting.")
            return

        qs = WorkerProfile.objects.select_related("user", "zone")
        if options["worker_id"]:
            qs = qs.filter(pk=options["worker_id"])

        total   = qs.count()
        updated = 0
        errors  = 0

        self.stdout.write(f"Updating {total} worker(s)...")

        for profile in qs.iterator():
            try:
                score = predict_risk_score(profile)
                WorkerProfile.objects.filter(pk=profile.pk).update(
                    risk_score=score,
                    risk_updated_at=timezone.now(),
                )
                updated += 1
                self.stdout.write(
                    f"  [{updated}/{total}] Worker {profile.pk} → {score}"
                )
            except Exception as exc:
                errors += 1
                self.stderr.write(f"  ERROR worker {profile.pk}: {exc}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Updated: {updated}  Errors: {errors}"
            )
        )