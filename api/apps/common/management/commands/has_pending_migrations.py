from django.core.management.base import BaseCommand
from django.db import connections
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Exit with status 10 when Django migrations are pending."

    def handle(self, *args, **options):
        executor = MigrationExecutor(connections["default"])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        if not plan:
            self.stdout.write("No pending migrations.")
            return

        for migration, backward in plan:
            direction = "backward" if backward else "forward"
            self.stdout.write(f"{migration.app_label}.{migration.name} ({direction})")

        raise SystemExit(10)
