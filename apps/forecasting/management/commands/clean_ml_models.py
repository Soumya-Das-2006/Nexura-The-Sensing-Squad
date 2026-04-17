"""
Management command — clean duplicate flat Prophet model files.

The ml_models/prophet/ folder has models in two layouts:
  FLAT (duplicate):   prophet/prophet_{city}_{metric}.pkl   ← DELETE these
  SUBFOLDER (correct): prophet/{city}/prophet_{city}_{metric}.pkl  ← KEEP these

Usage:
    python manage.py clean_ml_models --dry-run   (preview only)
    python manage.py clean_ml_models             (actually delete)
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Remove duplicate flat Prophet model files from ml_models/prophet/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview files to delete without actually deleting",
        )

    def handle(self, *args, **options):
        from django.conf import settings

        prophet_dir = settings.ML_MODELS_DIR / "prophet"
        dry_run     = options["dry_run"]

        if not prophet_dir.exists():
            self.stderr.write(f"ERROR: {prophet_dir} does not exist.")
            return

        # Flat files sit directly in prophet/ (not in a subfolder)
        flat_files = [
            f for f in prophet_dir.iterdir()
            if f.is_file() and f.suffix == ".pkl"
        ]

        if not flat_files:
            self.stdout.write(self.style.SUCCESS("No flat files found. Already clean."))
            return

        self.stdout.write(f"Found {len(flat_files)} flat duplicate file(s):\n")

        deleted = 0
        skipped = 0

        for f in sorted(flat_files):
            # Verify the subfolder version exists before deleting flat copy
            parts     = f.stem.replace("prophet_", "", 1).split("_", 1)
            city      = parts[0] if len(parts) >= 1 else ""
            subfolder = prophet_dir / city / f.name

            if subfolder.exists():
                self.stdout.write(f"  {'[DRY RUN] ' if dry_run else ''}DELETE: {f.name}")
                if not dry_run:
                    f.unlink()
                    deleted += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f"  SKIP (no subfolder copy): {f.name}")
                )
                skipped += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDry run complete. {len(flat_files) - skipped} file(s) "
                    f"would be deleted, {skipped} skipped."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nDone. Deleted: {deleted}  Skipped: {skipped}"
                )
            )

        # Show remaining structure
        self.stdout.write("\nRemaining subfolders:")
        for d in sorted(prophet_dir.iterdir()):
            if d.is_dir():
                count = len(list(d.glob("*.pkl")))
                self.stdout.write(f"  {d.name}/ → {count} model(s)")