from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ActivityRecordViewSet, IngestionBatchViewSet, SourceSystemViewSet, TenantViewSet, api_root, current_user, seed_samples, summary

router = DefaultRouter()
router.register("tenants", TenantViewSet, basename="tenant")
router.register("sources", SourceSystemViewSet, basename="source")
router.register("batches", IngestionBatchViewSet, basename="batch")
router.register("activities", ActivityRecordViewSet, basename="activity")

urlpatterns = [
    path("", api_root),
    path("me/", current_user),
    path("summary/", summary),
    path("seed-samples/", seed_samples),
    path("", include(router.urls)),
]
