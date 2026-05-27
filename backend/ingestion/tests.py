from decimal import Decimal

from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .management.commands.seed_demo import Command
from .models import ActivityRecord, IngestionBatch, SourceSystem, Tenant
from .parsers import import_sap_csv, normalize_unit


class ParserTests(TestCase):
    def setUp(self):
        Command().handle()
        self.tenant = Tenant.objects.get(slug="acme-manufacturing")

    def test_unit_conversion_from_gallons_to_litres(self):
        quantity, unit = normalize_unit(Decimal("10"), "GAL")
        self.assertEqual(unit, "L")
        self.assertEqual(quantity, Decimal("37.854"))

    def test_sap_parser_maps_fuel_and_procurement(self):
        fuel = ActivityRecord.objects.get(source_row_id="4900002311-1")
        procurement = ActivityRecord.objects.get(source_row_id="4900002313-1")
        self.assertEqual(fuel.scope, "scope_1")
        self.assertEqual(fuel.normalized_unit, "L")
        self.assertEqual(procurement.scope, "scope_3")
        self.assertEqual(procurement.scope_category, "category_1_purchased_goods")

    def test_duplicate_source_row_is_flagged(self):
        source = SourceSystem.objects.get(tenant=self.tenant, kind=SourceSystem.SAP)
        batch = IngestionBatch.objects.create(tenant=self.tenant, source=source, original_filename="dup.csv")
        csv = b"MaterialDocument,MaterialDocumentItem,PostingDate,Plant,MaterialDescription,Quantity,Unit,AmountInCompanyCodeCurrency,Currency\n4900002311,1,2026-01-08,1000,Diesel fuel,100,L,120,USD\n"
        import_sap_csv(batch, ContentFile(csv))
        duplicate = ActivityRecord.objects.filter(batch=batch).first()
        self.assertIn("duplicate_source_row", duplicate.flags)

    def test_approval_locks_record(self):
        record = ActivityRecord.objects.filter(status=ActivityRecord.PENDING).first()
        record.approve()
        record.refresh_from_db()
        self.assertTrue(record.is_locked)
        self.assertEqual(record.status, ActivityRecord.APPROVED)


class ApiTests(TestCase):
    def setUp(self):
        Command().handle()
        self.client = APIClient()

    def test_summary_returns_counts(self):
        response = self.client.get("/api/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data["total"], 0)
        self.assertIn("suspicious", response.data)

    def test_filters_records_by_status(self):
        response = self.client.get("/api/activities/?status=failed")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(row["status"] == "failed" for row in response.data))

    def test_approve_endpoint_locks_pending_record(self):
        record = ActivityRecord.objects.filter(status=ActivityRecord.PENDING).first()
        response = self.client.post(f"/api/activities/{record.id}/approve/", {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_locked"])

    def test_locked_record_cannot_be_patched(self):
        record = ActivityRecord.objects.filter(status=ActivityRecord.PENDING).first()
        record.approve()
        response = self.client.patch(f"/api/activities/{record.id}/", {"description": "changed"}, format="json")
        self.assertEqual(response.status_code, 400)
