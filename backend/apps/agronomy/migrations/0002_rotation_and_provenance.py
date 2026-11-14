# Additive Phase 5.3 recommendation storage and Phase 5.1 provenance alignment.
# Existing agronomy data is preserved; no table or row is dropped.
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("agronomy", "0001_initial"),
        ("farms", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="agriculturaldataset", name="identifier",
            field=models.CharField(max_length=160),
        ),
        migrations.AddField(model_name="agriculturaldataset", name="creators", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="agriculturaldataset", name="publication_date", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="agriculturaldataset", name="record_updated_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="agriculturaldataset", name="license_url", field=models.URLField(blank=True, max_length=500)),
        migrations.AddField(model_name="agriculturaldataset", name="temporal_coverage_start", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="agriculturaldataset", name="temporal_coverage_end", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="agriculturaldataset", name="spatial_resolution", field=models.CharField(blank=True, max_length=160)),
        migrations.AddField(model_name="agriculturaldataset", name="temporal_resolution", field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name="agriculturaldataset", name="retrieved_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddConstraint(
            model_name="agriculturaldataset",
            constraint=models.UniqueConstraint(fields=("identifier", "version"), name="uniq_ag_dataset_identifier_version"),
        ),
        migrations.AddConstraint(
            model_name="agriculturaldataset",
            constraint=models.CheckConstraint(condition=models.Q(("temporal_coverage_end__isnull", True)) | models.Q(("temporal_coverage_start__isnull", True)) | models.Q(("temporal_coverage_start__lte", models.F("temporal_coverage_end"))), name="ag_dataset_temporal_coverage_ordered"),
        ),
        migrations.AddField(model_name="datasetimport", name="mapping_version", field=models.CharField(default="1", max_length=80)),
        migrations.CreateModel(
            name="DatasetResource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("resource_identifier", models.CharField(max_length=255)),
                ("title", models.CharField(max_length=300)),
                ("access_url", models.URLField(max_length=1000)),
                ("file_format", models.CharField(blank=True, max_length=80)),
                ("size_bytes", models.PositiveBigIntegerField(blank=True, null=True)),
                ("checksum", models.CharField(blank=True, max_length=128)),
                ("license", models.CharField(blank=True, max_length=300)),
                ("license_url", models.URLField(blank=True, max_length=500)),
                ("attribution", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("dataset", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="resources", to="agronomy.agriculturaldataset")),
            ], options={"ordering": ["dataset_id", "resource_identifier"]},
        ),
        migrations.AddField(
            model_name="datasetimport", name="resource",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="imports", to="agronomy.datasetresource"),
        ),
        migrations.AddConstraint(
            model_name="datasetresource",
            constraint=models.UniqueConstraint(fields=("dataset", "resource_identifier"), name="uniq_ag_dataset_resource_id"),
        ),
        migrations.RemoveConstraint(model_name="datasetimport", name="uniq_ag_dataset_import_checksum"),
        migrations.AddConstraint(
            model_name="datasetimport",
            constraint=models.UniqueConstraint(condition=models.Q(("resource__isnull", True)), fields=("dataset", "source_checksum", "mapping_version"), name="uniq_ag_import_checksum_without_resource"),
        ),
        migrations.AddConstraint(
            model_name="datasetimport",
            constraint=models.UniqueConstraint(condition=models.Q(("resource__isnull", False)), fields=("dataset", "resource", "source_checksum", "mapping_version"), name="uniq_ag_import_checksum_with_resource"),
        ),
        migrations.AddField(model_name="cropcharacteristic", name="normalized_text", field=models.TextField(blank=True, null=True)),
        migrations.AddField(model_name="cropcharacteristic", name="normalized_boolean", field=models.BooleanField(blank=True, null=True)),
        migrations.AddField(model_name="cropcharacteristic", name="original_dataset_title", field=models.CharField(default="", max_length=300)),
        migrations.AddField(model_name="cropcharacteristic", name="original_dataset_landing_page_url", field=models.URLField(blank=True, default="", max_length=500)),
        migrations.AddField(model_name="cropcharacteristic", name="source_resource_identifier", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="cropcharacteristic", name="source_resource_url", field=models.URLField(blank=True, max_length=1000)),
        migrations.AddConstraint(
            model_name="cropcharacteristic",
            constraint=models.CheckConstraint(condition=(models.Q(("value_type", "NUMBER"), ("normalized_text__isnull", True), ("normalized_boolean__isnull", True)) | models.Q(("value_type", "TEXT"), ("normalized_value__isnull", True), ("normalized_boolean__isnull", True)) | models.Q(("value_type", "BOOLEAN"), ("normalized_value__isnull", True), ("normalized_text__isnull", True))), name="ag_trait_single_normalized_value_type"),
        ),
        migrations.CreateModel(
            name="RotationRecommendation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("engine_version", models.CharField(max_length=40)),
                ("input_snapshot", models.JSONField()),
                ("input_sha256", models.CharField(max_length=64)),
                ("assessment", models.JSONField()),
                ("status", models.CharField(choices=[("OPTIONS_AVAILABLE", "Options available"), ("INSUFFICIENT_EVIDENCE", "Insufficient evidence")], max_length=32)),
                ("generated_at", models.DateTimeField(auto_now_add=True)),
                ("farm", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rotation_recommendations", to="farms.farm")),
                ("requested_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="rotation_recommendations", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["-generated_at", "-id"]},
        ),
        migrations.AddIndex(model_name="rotationrecommendation", index=models.Index(fields=["farm", "-generated_at"], name="rotation_farm_generated_idx")),
    ]
