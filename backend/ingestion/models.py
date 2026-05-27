from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


class Tenant(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Facility(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="facilities")
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=40)
    plant_codes = models.JSONField(default=list, blank=True)
    meter_numbers = models.JSONField(default=list, blank=True)
    egrid_region = models.CharField(max_length=24, blank=True)

    class Meta:
        unique_together = ("tenant", "code")

    def __str__(self):
        return f"{self.tenant.slug}:{self.code}"


class SourceSystem(models.Model):
    SAP = "sap"
    UTILITY = "utility"
    CONCUR = "concur"
    KIND_CHOICES = [(SAP, "SAP"), (UTILITY, "Utility"), (CONCUR, "Concur")]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="sources")
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=24, choices=KIND_CHOICES)

    class Meta:
        unique_together = ("tenant", "kind", "name")

    def __str__(self):
        return f"{self.tenant.slug}:{self.kind}"


class IngestionBatch(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="batches")
    source = models.ForeignKey(SourceSystem, on_delete=models.CASCADE, related_name="batches")
    original_filename = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=24, default="completed")
    imported_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    suspicious_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class RawRecord(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="raw_records")
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name="raw_records")
    source = models.ForeignKey(SourceSystem, on_delete=models.CASCADE, related_name="raw_records")
    source_row_id = models.CharField(max_length=160)
    raw_payload = models.JSONField()
    parse_status = models.CharField(max_length=24, default="parsed")
    errors = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["tenant", "source", "source_row_id"])]


class EmissionFactor(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="factors")
    key = models.CharField(max_length=80)
    activity_type = models.CharField(max_length=80)
    unit = models.CharField(max_length=32)
    kg_co2e_per_unit = models.DecimalField(max_digits=12, decimal_places=6)
    scope = models.CharField(max_length=16)
    scope_category = models.CharField(max_length=80, blank=True)
    region = models.CharField(max_length=40, blank=True)
    source_note = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("tenant", "key")


class ActivityRecord(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (FAILED, "Failed"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="activities")
    source = models.ForeignKey(SourceSystem, on_delete=models.PROTECT, related_name="activities")
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name="activities")
    raw_record = models.OneToOneField(RawRecord, on_delete=models.CASCADE, related_name="activity")
    facility = models.ForeignKey(Facility, null=True, blank=True, on_delete=models.SET_NULL, related_name="activities")
    source_row_id = models.CharField(max_length=160)
    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    scope = models.CharField(max_length=16)
    scope_category = models.CharField(max_length=80, blank=True)
    activity_type = models.CharField(max_length=80)
    description = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    unit = models.CharField(max_length=32, blank=True)
    normalized_quantity = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    normalized_unit = models.CharField(max_length=32, blank=True)
    spend_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, blank=True)
    emission_factor_key = models.CharField(max_length=80, blank=True)
    estimated_kg_co2e = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=PENDING)
    flags = models.JSONField(default=list, blank=True)
    canonical_payload = models.JSONField(default=dict, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(get_user_model(), null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "source", "source_row_id"])]

    @property
    def is_locked(self):
        return self.locked_at is not None

    def approve(self, user=None):
        self.status = self.APPROVED
        self.locked_at = timezone.now()
        if user and getattr(user, "is_authenticated", False):
            self.locked_by = user
        self.save(update_fields=["status", "locked_at", "locked_by", "updated_at"])


class ReviewEvent(models.Model):
    IMPORTED = "imported"
    EDITED = "edited"
    APPROVED = "approved"
    REJECTED = "rejected"
    EVENT_CHOICES = [(IMPORTED, "Imported"), (EDITED, "Edited"), (APPROVED, "Approved"), (REJECTED, "Rejected")]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="review_events")
    activity = models.ForeignKey(ActivityRecord, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=24, choices=EVENT_CHOICES)
    actor = models.ForeignKey(get_user_model(), null=True, blank=True, on_delete=models.SET_NULL)
    note = models.TextField(blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
