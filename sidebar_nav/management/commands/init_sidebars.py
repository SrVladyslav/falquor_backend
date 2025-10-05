import json
import hashlib
from dataclasses import dataclass
from typing import Iterable

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import now

from importlib.resources import files
from sidebar_nav.models.base import SidebarManifest


@dataclass
class SeedFile:
    path: str  # ruta relativa dentro del paquete
    name: str  # nombre que quieres en DB (humano)
    scope: str  # "GLOBAL", "WORKSPACE", etc.
    version: str  # "v1", "v0.0.1"...


SEEDS: Iterable[SeedFile] = [
    SeedFile(
        path="seed/manifests/default_global_v1.json",
        name="DEFAULT_MANIFEST",
        scope="GLOBAL",
        version="v1",
    ),
]


def compute_checksum(data: dict) -> str:
    """Stable SHA256 over the canonical JSON (sorted keys)."""
    blob = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class Command(BaseCommand):
    help = "Init/Upsert default Sidebar manifests from seed files."

    def handle(self, *args, **kwargs):
        created, updated, skipped = 0, 0, 0

        for seed in SEEDS:
            created_one, updated_one, skipped_one = self._upsert_one(seed)
            created += created_one
            updated += updated_one
            skipped += skipped_one

        self.stdout.write(
            self.style.SUCCESS(
                f"Sidebar manifests -> created: {created}, updated: {updated}, skipped: {skipped}"
            )
        )

    @transaction.atomic
    def _upsert_one(self, seed: SeedFile):
        """
        Upsert by (name, scope). If checksum matches, skip.
        If content changed (checksum diff), update manifest+version+checksum.
        """
        pkg_root = files("sidebar_nav")  # paquete base de la app
        json_path = pkg_root / seed.path
        if not json_path.exists():
            raise FileNotFoundError(f"Seed file not found: {seed.path}")

        data = json.loads(json_path.read_text(encoding="utf-8"))
        print("Seed data: ", data)
        # Normalize/patch meta
        data.setdefault("meta", {})
        data["meta"]["version"] = seed.version
        data["meta"]["updatedAt"] = now().isoformat()

        checksum = compute_checksum(data)

        obj, created = SidebarManifest.objects.get_or_create(
            name=seed.name,
            scope=seed.scope,  # SidebarManifest.scope si es CharField
            defaults={
                "manifest": data,
                "version": seed.version,
                "priority": 10,
                "is_active": True,
                "checksum": checksum,
            },
        )

        if created:
            # rellena manifestId con el pk si quieres
            data["meta"]["manifestId"] = str(obj.pk)
            obj.manifest = data
            obj.checksum = compute_checksum(data)
            obj.save(update_fields=["manifest", "checksum"])
            self.stdout.write(
                self.style.WARNING(f" ✓ Created manifest: {seed.name} ({seed.scope})")
            )
            return 1, 0, 0

        # Update branch: compare checksum to detect changes
        if obj.checksum != checksum:
            # Update content, version & checksum
            data["meta"]["manifestId"] = str(obj.pk)
            obj.manifest = data
            obj.version = seed.version
            obj.checksum = compute_checksum(data)
            obj.is_active = True
            obj.save(update_fields=["manifest", "version", "checksum", "is_active"])
            self.stdout.write(
                self.style.WARNING(f" ↺ Updated manifest: {seed.name} ({seed.scope})")
            )
            return 0, 1, 0

        self.stdout.write(f"• Skipped (no changes): {seed.name} ({seed.scope})")
        return 0, 0, 1
