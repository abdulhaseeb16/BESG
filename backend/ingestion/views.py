from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import ActivityRecord, IngestionBatch, ReviewEvent, SourceSystem, Tenant
from .parsers import import_concur_json, import_sap_csv, import_utility_csv, load_sample_concur_payload
from .serializers import ActivityRecordSerializer, ActivityUpdateSerializer, IngestionBatchSerializer, SourceSystemSerializer, TenantSerializer


@api_view(["GET"])
def api_root(request):
    return Response(
        {
            "message": "Breathe ESG ingestion review API",
            "endpoints": {
                "me": "/api/me/",
                "tenants": "/api/tenants/",
                "sources": "/api/sources/",
                "activities": "/api/activities/",
                "batches": "/api/batches/",
                "summary": "/api/summary/",
            },
        }
    )


@api_view(["GET"])
def current_user(request):
    if request.user.is_authenticated:
        display_name = request.user.get_full_name() or request.user.email or request.user.username
        email = request.user.email
    else:
        demo_user = get_user_model().objects.filter(username="analyst@breathe.demo").first()
        display_name = demo_user.get_full_name() if demo_user else "Demo Analyst"
        email = demo_user.email if demo_user else "analyst@breathe.demo"
    initials = "".join(part[0] for part in display_name.split()[:2]).upper() or "A"
    return Response(
        {
            "display_name": display_name,
            "email": email,
            "initials": initials,
            "is_authenticated": request.user.is_authenticated,
        }
    )


class TenantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer


class SourceSystemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SourceSystemSerializer

    def get_queryset(self):
        queryset = SourceSystem.objects.select_related("tenant")
        tenant_id = self.request.query_params.get("tenant")
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        return queryset


class IngestionBatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngestionBatchSerializer

    def get_queryset(self):
        queryset = IngestionBatch.objects.select_related("tenant", "source")
        tenant_id = self.request.query_params.get("tenant")
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        return queryset

    @action(detail=False, methods=["post"], url_path="upload-sap")
    def upload_sap(self, request):
        return self._upload_csv(request, SourceSystem.SAP, import_sap_csv)

    @action(detail=False, methods=["post"], url_path="upload-utility")
    def upload_utility(self, request):
        return self._upload_csv(request, SourceSystem.UTILITY, import_utility_csv)

    @action(detail=False, methods=["post"], url_path="import-concur")
    def import_concur(self, request):
        tenant = get_tenant(request)
        source = SourceSystem.objects.get(tenant=tenant, kind=SourceSystem.CONCUR)
        batch = IngestionBatch.objects.create(tenant=tenant, source=source, original_filename="mock_concur_itineraries.json")
        payload_path = settings.BASE_DIR / "sample_data" / "concur_itineraries.json"
        activities = import_concur_json(batch, load_sample_concur_payload(payload_path))
        return Response({"batch": IngestionBatchSerializer(batch).data, "activity_count": len(activities)})

    def _upload_csv(self, request, source_kind, parser):
        tenant = get_tenant(request)
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "CSV file is required as form field 'file'."}, status=status.HTTP_400_BAD_REQUEST)
        source = SourceSystem.objects.get(tenant=tenant, kind=source_kind)
        batch = IngestionBatch.objects.create(tenant=tenant, source=source, original_filename=upload.name)
        activities = parser(batch, upload)
        return Response({"batch": IngestionBatchSerializer(batch).data, "activity_count": len(activities)})


class ActivityRecordViewSet(viewsets.ModelViewSet):
    queryset = ActivityRecord.objects.select_related("tenant", "source", "batch", "facility", "raw_record").prefetch_related("events")

    def get_serializer_class(self):
        if self.action in ["partial_update", "update"]:
            return ActivityUpdateSerializer
        return ActivityRecordSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params
        if params.get("tenant"):
            queryset = queryset.filter(tenant_id=params["tenant"])
        if params.get("source"):
            queryset = queryset.filter(source__kind=params["source"])
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        if params.get("scope"):
            queryset = queryset.filter(scope=params["scope"])
        if params.get("flag"):
            matching_ids = [activity.id for activity in queryset.only("id", "flags") if params["flag"] in activity.flags]
            queryset = queryset.filter(id__in=matching_ids)
        if params.get("search"):
            search = params["search"]
            queryset = queryset.filter(Q(source_row_id__icontains=search) | Q(description__icontains=search))
        return queryset

    def perform_update(self, serializer):
        before = ActivityRecordSerializer(self.get_object()).data
        activity = serializer.save()
        ReviewEvent.objects.create(
            tenant=activity.tenant,
            activity=activity,
            event_type=ReviewEvent.EDITED,
            actor=self.request.user if self.request.user.is_authenticated else None,
            before=before,
            after=ActivityRecordSerializer(activity).data,
            note="Analyst edited normalized fields",
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        activity = self.get_object()
        if activity.status == ActivityRecord.FAILED:
            return Response({"detail": "Failed rows must be corrected before approval."}, status=status.HTTP_400_BAD_REQUEST)
        before = ActivityRecordSerializer(activity).data
        activity.approve(request.user)
        ReviewEvent.objects.create(
            tenant=activity.tenant,
            activity=activity,
            event_type=ReviewEvent.APPROVED,
            actor=request.user if request.user.is_authenticated else None,
            before=before,
            after=ActivityRecordSerializer(activity).data,
            note=request.data.get("note", "Approved for audit"),
        )
        return Response(ActivityRecordSerializer(activity).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        activity = self.get_object()
        if activity.is_locked:
            return Response({"detail": "Approved records are locked for audit."}, status=status.HTTP_400_BAD_REQUEST)
        before = ActivityRecordSerializer(activity).data
        activity.status = ActivityRecord.REJECTED
        activity.save(update_fields=["status", "updated_at"])
        ReviewEvent.objects.create(
            tenant=activity.tenant,
            activity=activity,
            event_type=ReviewEvent.REJECTED,
            actor=request.user if request.user.is_authenticated else None,
            before=before,
            after=ActivityRecordSerializer(activity).data,
            note=request.data.get("note", "Rejected by analyst"),
        )
        return Response(ActivityRecordSerializer(activity).data)


@api_view(["GET"])
def summary(request):
    tenant = get_tenant(request)
    activities = ActivityRecord.objects.filter(tenant=tenant)
    by_status = {row["status"]: row["count"] for row in activities.values("status").annotate(count=Count("id"))}
    by_source = {row["source__kind"]: row["count"] for row in activities.values("source__kind").annotate(count=Count("id"))}
    return Response(
        {
            "tenant": TenantSerializer(tenant).data,
            "total": activities.count(),
            "pending": by_status.get(ActivityRecord.PENDING, 0),
            "approved": by_status.get(ActivityRecord.APPROVED, 0),
            "rejected": by_status.get(ActivityRecord.REJECTED, 0),
            "failed": by_status.get(ActivityRecord.FAILED, 0),
            "suspicious": sum(1 for activity in activities.only("flags") if activity.flags),
            "locked": activities.exclude(locked_at__isnull=True).count(),
            "by_source": by_source,
        }
    )


@api_view(["POST"])
def seed_samples(request):
    from django.core.management import call_command

    call_command("seed_demo")
    return Response({"detail": "Demo tenant, sources, factors, and sample rows are ready."})


def get_tenant(request):
    tenant_id = request.data.get("tenant") if hasattr(request, "data") else None
    tenant_id = tenant_id or request.query_params.get("tenant")
    if tenant_id:
        return Tenant.objects.get(id=tenant_id)
    return Tenant.objects.order_by("id").first()
