# Generated manually from the Phase 5.1/5.2 agronomy models because migration
# generation is intentionally non-destructive and requires the project runtime.

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AgriculturalDataset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("identifier", models.CharField(max_length=160)),
                ("title", models.CharField(max_length=300)), ("publisher", models.CharField(max_length=200)),
                ("version", models.CharField(blank=True, max_length=100)),
                ("landing_page_url", models.URLField(max_length=500)), ("doi", models.CharField(blank=True, max_length=255)),
                ("license", models.CharField(blank=True, max_length=300)), ("attribution", models.TextField(blank=True)),
                ("geographic_scope", models.CharField(blank=True, max_length=300)),
                ("status", models.CharField(choices=[("PROPOSED", "Proposed (not importable)"), ("APPROVED", "Approved for import"), ("RETIRED", "Retired")], default="PROPOSED", max_length=16)),
                ("approved_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ], options={"ordering": ["identifier", "version"]},
        ),
        migrations.CreateModel(
            name="Crop",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=80, unique=True)), ("name", models.CharField(max_length=160)),
                ("scientific_name", models.CharField(blank=True, max_length=200)), ("crop_family", models.CharField(blank=True, max_length=160)),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ], options={"ordering": ["name", "code"]},
        ),
        migrations.CreateModel(
            name="DatasetImport",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("source_file_name", models.CharField(blank=True, max_length=255)), ("source_checksum", models.CharField(max_length=128)),
                ("status", models.CharField(choices=[("RUNNING", "Running"), ("SUCCEEDED", "Succeeded"), ("PARTIAL", "Partially succeeded"), ("FAILED", "Failed"), ("SKIPPED", "Already imported")], default="RUNNING", max_length=16)),
                ("total_records", models.PositiveIntegerField(default=0)), ("imported_records", models.PositiveIntegerField(default=0)),
                ("skipped_records", models.PositiveIntegerField(default=0)), ("failed_records", models.PositiveIntegerField(default=0)),
                ("errors", models.JSONField(default=list)), ("started_at", models.DateTimeField(auto_now_add=True)), ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("dataset", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="imports", to="agronomy.agriculturaldataset")),
            ], options={"ordering": ["-started_at", "-id"]},
        ),
        migrations.CreateModel(
            name="CropCharacteristic",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_crop_identifier", models.CharField(max_length=160)), ("cultivar_or_variety", models.CharField(blank=True, max_length=200)),
                ("characteristic_name", models.CharField(max_length=160)),
                ("value_type", models.CharField(choices=[("NUMBER", "Number"), ("TEXT", "Text"), ("BOOLEAN", "Boolean")], max_length=12)),
                ("original_value", models.TextField(blank=True, null=True)), ("original_unit", models.CharField(blank=True, max_length=80)),
                ("normalized_value", models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)), ("normalized_unit", models.CharField(blank=True, max_length=80)),
                ("temporal_applicability", models.CharField(blank=True, max_length=300)), ("geographic_scope", models.CharField(blank=True, max_length=300)),
                ("geographic_applicability", models.CharField(choices=[("DIRECT", "Direct Egypt/Gharbia evidence"), ("GENERAL", "Global or general crop information"), ("TRANSFERABLE_LIMITED", "Transferable with limitations"), ("US_SPECIFIC", "U.S.-specific evidence"), ("UNKNOWN", "Unknown applicability")], default="UNKNOWN", max_length=24)),
                ("source_record_identifier", models.CharField(max_length=255)), ("source_record_url", models.URLField(blank=True, max_length=500)),
                ("evidence_reference", models.TextField(blank=True)),
                ("validation_status", models.CharField(choices=[("VALID", "Validated"), ("REVIEW_REQUIRED", "Requires review"), ("REJECTED", "Rejected")], default="REVIEW_REQUIRED", max_length=20)),
                ("imported_at", models.DateTimeField(auto_now_add=True)),
                ("original_dataset_identifier", models.CharField(max_length=160)),
                ("original_publisher", models.CharField(max_length=200)),
                ("original_dataset_version", models.CharField(blank=True, max_length=100)),
                ("source_doi", models.CharField(blank=True, max_length=255)),
                ("source_license", models.CharField(blank=True, max_length=300)),
                ("source_attribution", models.TextField(blank=True)),
                ("crop", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="characteristics", to="agronomy.crop")),
                ("dataset", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="characteristics", to="agronomy.agriculturaldataset")),
                ("dataset_import", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="characteristics", to="agronomy.datasetimport")),
            ], options={"ordering": ["crop_id", "characteristic_name", "id"]},
        ),
        migrations.AddConstraint(model_name="datasetimport", constraint=models.UniqueConstraint(fields=("dataset", "source_checksum"), name="uniq_ag_dataset_import_checksum")),
        migrations.AddConstraint(model_name="cropcharacteristic", constraint=models.UniqueConstraint(fields=("dataset", "source_record_identifier", "characteristic_name"), name="uniq_ag_trait_source_record_name")),
        migrations.AddConstraint(model_name="cropcharacteristic", constraint=models.CheckConstraint(condition=models.Q(("normalized_value__isnull", True)) | ~models.Q(("normalized_unit", "")), name="ag_trait_normalized_value_has_unit")),
        migrations.AddIndex(model_name="cropcharacteristic", index=models.Index(fields=["crop", "characteristic_name"], name="ag_trait_crop_name_idx")),
        migrations.AddIndex(model_name="cropcharacteristic", index=models.Index(fields=["dataset", "validation_status"], name="ag_trait_dataset_status_idx")),
    ]
