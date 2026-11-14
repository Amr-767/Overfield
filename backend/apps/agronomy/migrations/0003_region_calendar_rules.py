# Additive regional calendar and reviewed rotation-rule models.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("agronomy", "0002_rotation_and_provenance")]

    operations = [
        migrations.CreateModel(
            name="RegionAgronomyProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("region_code", models.CharField(max_length=80)),
                ("country_code", models.CharField(blank=True, max_length=2)),
                ("timezone", models.CharField(default="UTC", max_length=64)),
                ("season_cycle_start_month_day", models.CharField(blank=True, max_length=5)),
                ("calendar_version", models.CharField(max_length=80)),
                ("status", models.CharField(choices=[("PROPOSED", "Proposed (not importable)"), ("APPROVED", "Approved for import"), ("RETIRED", "Retired")], default="PROPOSED", max_length=16)),
                ("source_title", models.CharField(blank=True, max_length=300)),
                ("source_publisher", models.CharField(blank=True, max_length=200)),
                ("source_url", models.URLField(blank=True, max_length=500)),
                ("evidence_reference", models.TextField(blank=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
            ], options={"ordering": ["region_code", "calendar_version"]},
        ),
        migrations.AddConstraint(
            model_name="regionagronomyprofile",
            constraint=models.UniqueConstraint(fields=("region_code", "calendar_version"), name="uniq_region_calendar_version"),
        ),
        migrations.CreateModel(
            name="RegionSeason",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("season_code", models.CharField(max_length=80)),
                ("label", models.CharField(max_length=120)),
                ("sequence", models.PositiveSmallIntegerField()),
                ("start_month_day", models.CharField(max_length=5)),
                ("end_month_day", models.CharField(max_length=5)),
                ("evidence_reference", models.TextField()),
                ("source_url", models.URLField(max_length=500)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="seasons", to="agronomy.regionagronomyprofile")),
            ], options={"ordering": ["sequence", "id"]},
        ),
        migrations.AddConstraint(model_name="regionseason", constraint=models.UniqueConstraint(fields=("profile", "season_code"), name="uniq_region_season_code")),
        migrations.CreateModel(
            name="RegionSeasonCrop",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("planting_window", models.CharField(blank=True, max_length=120)),
                ("harvest_window", models.CharField(blank=True, max_length=120)),
                ("evidence_reference", models.TextField()),
                ("source_url", models.URLField(max_length=500)),
                ("crop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="region_seasons", to="agronomy.crop")),
                ("season", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="crop_windows", to="agronomy.regionseason")),
            ],
        ),
        migrations.AddConstraint(model_name="regionseasoncrop", constraint=models.UniqueConstraint(fields=("season", "crop"), name="uniq_season_crop_window")),
        migrations.CreateModel(
            name="CropRotationRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("identifier", models.CharField(max_length=100)),
                ("rule_type", models.CharField(choices=[("FORBID_ADJACENT_CROP", "Forbid crop in adjacent slots")], max_length=40)),
                ("description", models.TextField()),
                ("source_title", models.CharField(max_length=300)),
                ("source_url", models.URLField(max_length=500)),
                ("evidence_reference", models.TextField()),
                ("approved", models.BooleanField(default=False)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("crop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rotation_rules", to="agronomy.crop")),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rotation_rules", to="agronomy.regionagronomyprofile")),
            ],
        ),
        migrations.AddConstraint(model_name="croprotationrule", constraint=models.UniqueConstraint(fields=("profile", "identifier"), name="uniq_rotation_rule_identifier")),
    ]
