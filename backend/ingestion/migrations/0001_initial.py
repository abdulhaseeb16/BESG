# Generated for the Breathe ESG prototype.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tenant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Facility",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("code", models.CharField(max_length=40)),
                ("plant_codes", models.JSONField(blank=True, default=list)),
                ("meter_numbers", models.JSONField(blank=True, default=list)),
                ("egrid_region", models.CharField(blank=True, max_length=24)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="facilities", to="ingestion.tenant")),
            ],
            options={"unique_together": {("tenant", "code")}},
        ),
        migrations.CreateModel(
            name="SourceSystem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("kind", models.CharField(choices=[("sap", "SAP"), ("utility", "Utility"), ("concur", "Concur")], max_length=24)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sources", to="ingestion.tenant")),
            ],
            options={"unique_together": {("tenant", "kind", "name")}},
        ),
        migrations.CreateModel(
            name="EmissionFactor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=80)),
                ("activity_type", models.CharField(max_length=80)),
                ("unit", models.CharField(max_length=32)),
                ("kg_co2e_per_unit", models.DecimalField(decimal_places=6, max_digits=12)),
                ("scope", models.CharField(max_length=16)),
                ("scope_category", models.CharField(blank=True, max_length=80)),
                ("region", models.CharField(blank=True, max_length=40)),
                ("source_note", models.CharField(blank=True, max_length=255)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="factors", to="ingestion.tenant")),
            ],
            options={"unique_together": {("tenant", "key")}},
        ),
        migrations.CreateModel(
            name="IngestionBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("original_filename", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(default="completed", max_length=24)),
                ("imported_count", models.PositiveIntegerField(default=0)),
                ("failed_count", models.PositiveIntegerField(default=0)),
                ("suspicious_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="batches", to="ingestion.sourcesystem")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="batches", to="ingestion.tenant")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="RawRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_row_id", models.CharField(max_length=160)),
                ("raw_payload", models.JSONField()),
                ("parse_status", models.CharField(default="parsed", max_length=24)),
                ("errors", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="raw_records", to="ingestion.ingestionbatch")),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="raw_records", to="ingestion.sourcesystem")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="raw_records", to="ingestion.tenant")),
            ],
        ),
        migrations.CreateModel(
            name="ActivityRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_row_id", models.CharField(max_length=160)),
                ("activity_date", models.DateField(blank=True, null=True)),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("scope", models.CharField(max_length=16)),
                ("scope_category", models.CharField(blank=True, max_length=80)),
                ("activity_type", models.CharField(max_length=80)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("quantity", models.DecimalField(blank=True, decimal_places=3, max_digits=14, null=True)),
                ("unit", models.CharField(blank=True, max_length=32)),
                ("normalized_quantity", models.DecimalField(blank=True, decimal_places=3, max_digits=14, null=True)),
                ("normalized_unit", models.CharField(blank=True, max_length=32)),
                ("spend_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("currency", models.CharField(blank=True, max_length=8)),
                ("emission_factor_key", models.CharField(blank=True, max_length=80)),
                ("estimated_kg_co2e", models.DecimalField(blank=True, decimal_places=3, max_digits=14, null=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("failed", "Failed")], default="pending", max_length=24)),
                ("flags", models.JSONField(blank=True, default=list)),
                ("canonical_payload", models.JSONField(blank=True, default=dict)),
                ("locked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="activities", to="ingestion.ingestionbatch")),
                ("facility", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activities", to="ingestion.facility")),
                ("locked_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("raw_record", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="activity", to="ingestion.rawrecord")),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="activities", to="ingestion.sourcesystem")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="activities", to="ingestion.tenant")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ReviewEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("imported", "Imported"), ("edited", "Edited"), ("approved", "Approved"), ("rejected", "Rejected")], max_length=24)),
                ("note", models.TextField(blank=True)),
                ("before", models.JSONField(blank=True, default=dict)),
                ("after", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("activity", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="ingestion.activityrecord")),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="review_events", to="ingestion.tenant")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddIndex(model_name="rawrecord", index=models.Index(fields=["tenant", "source", "source_row_id"], name="ingestion_r_tenant__8596c4_idx")),
        migrations.AddIndex(model_name="activityrecord", index=models.Index(fields=["tenant", "source", "source_row_id"], name="ingestion_a_tenant__6272ff_idx")),
    ]
