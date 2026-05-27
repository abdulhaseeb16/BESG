from rest_framework import serializers

from .models import ActivityRecord, Facility, IngestionBatch, RawRecord, ReviewEvent, SourceSystem, Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "slug"]


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ["id", "name", "code", "plant_codes", "meter_numbers", "egrid_region"]


class SourceSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceSystem
        fields = ["id", "name", "kind"]


class IngestionBatchSerializer(serializers.ModelSerializer):
    source = SourceSystemSerializer(read_only=True)
    tenant = TenantSerializer(read_only=True)

    class Meta:
        model = IngestionBatch
        fields = [
            "id",
            "tenant",
            "source",
            "original_filename",
            "status",
            "imported_count",
            "failed_count",
            "suspicious_count",
            "created_at",
        ]


class RawRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRecord
        fields = ["source_row_id", "raw_payload", "parse_status", "errors", "created_at"]


class ReviewEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = ReviewEvent
        fields = ["id", "event_type", "actor_email", "note", "before", "after", "created_at"]


class ActivityRecordSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)
    source = SourceSystemSerializer(read_only=True)
    facility = FacilitySerializer(read_only=True)
    raw_record = RawRecordSerializer(read_only=True)
    events = ReviewEventSerializer(many=True, read_only=True)
    is_locked = serializers.BooleanField(read_only=True)

    class Meta:
        model = ActivityRecord
        fields = [
            "id",
            "tenant",
            "source",
            "batch_id",
            "raw_record",
            "facility",
            "source_row_id",
            "activity_date",
            "period_start",
            "period_end",
            "scope",
            "scope_category",
            "activity_type",
            "description",
            "quantity",
            "unit",
            "normalized_quantity",
            "normalized_unit",
            "spend_amount",
            "currency",
            "emission_factor_key",
            "estimated_kg_co2e",
            "status",
            "flags",
            "canonical_payload",
            "locked_at",
            "is_locked",
            "created_at",
            "updated_at",
            "events",
        ]


class ActivityUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityRecord
        fields = ["description", "normalized_quantity", "normalized_unit", "estimated_kg_co2e", "flags", "status"]

    def validate(self, attrs):
        if self.instance and self.instance.is_locked:
            raise serializers.ValidationError("Approved records are locked for audit and cannot be edited.")
        return attrs

