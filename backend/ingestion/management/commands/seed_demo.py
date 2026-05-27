from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from ingestion.models import ActivityRecord, EmissionFactor, Facility, IngestionBatch, RawRecord, ReviewEvent, SourceSystem, Tenant
from ingestion.parsers import import_concur_json, import_sap_csv, import_utility_csv, load_sample_concur_payload


class Command(BaseCommand):
    help = "Seed demo tenant, reference data, and realistic sample imports."

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(name="Acme Manufacturing India", slug="acme-manufacturing")
        User = get_user_model()
        User.objects.update_or_create(
            username="analyst@breathe.demo",
            defaults={"email": "analyst@breathe.demo", "is_staff": True, "is_superuser": True},
        )
        user = User.objects.get(username="analyst@breathe.demo")
        user.set_password("breathe-demo")
        user.save()

        Facility.objects.update_or_create(
            tenant=tenant,
            code="BLR-PLANT",
            defaults={
                "name": "Bengaluru Assembly Plant",
                "plant_codes": ["1000", "BLR1"],
                "meter_numbers": ["KA-8821-MTR", "KA-8822-MTR"],
                "egrid_region": "SRVC",
            },
        )
        Facility.objects.update_or_create(
            tenant=tenant,
            code="PUN-WH",
            defaults={
                "name": "Pune Distribution Warehouse",
                "plant_codes": ["2000", "PUN2"],
                "meter_numbers": ["MH-4401-MTR"],
                "egrid_region": "SRVC",
            },
        )

        for name, kind in [
            ("SAP S/4HANA Material Documents", SourceSystem.SAP),
            ("Utility Green Button Export", SourceSystem.UTILITY),
            ("SAP Concur Itinerary Mock", SourceSystem.CONCUR),
        ]:
            SourceSystem.objects.update_or_create(tenant=tenant, kind=kind, name=name)

        factors = [
            ("diesel_litre", "fuel_combustion", "L", "2.680000", "scope_1", "stationary_or_mobile_fuel", "", "Demo diesel factor"),
            ("procurement_usd", "procurement_spend", "USD", "0.420000", "scope_3", "category_1_purchased_goods", "", "Demo spend factor"),
            ("electricity_srvc", "electricity", "kWh", "0.710000", "scope_2", "purchased_electricity_location_based", "SRVC", "Demo eGRID-style factor"),
            ("electricity_default", "electricity", "kWh", "0.650000", "scope_2", "purchased_electricity_location_based", "", "Fallback electricity factor"),
            ("flight_passenger_km", "business_travel_flight", "passenger_km", "0.115000", "scope_3", "category_6_business_travel", "", "Demo flight factor"),
            ("hotel_room_night", "business_travel_hotel", "room_night", "24.000000", "scope_3", "category_6_business_travel", "", "Demo hotel factor"),
            ("ground_transport_km", "business_travel_ground", "km", "0.180000", "scope_3", "category_6_business_travel", "", "Demo ground factor"),
        ]
        for key, activity_type, unit, value, scope, category, region, note in factors:
            EmissionFactor.objects.update_or_create(
                tenant=tenant,
                key=key,
                defaults={
                    "activity_type": activity_type,
                    "unit": unit,
                    "kg_co2e_per_unit": value,
                    "scope": scope,
                    "scope_category": category,
                    "region": region,
                    "source_note": note,
                },
            )

        ActivityRecord.objects.filter(tenant=tenant).delete()
        RawRecord.objects.filter(tenant=tenant).delete()
        IngestionBatch.objects.filter(tenant=tenant).delete()
        ReviewEvent.objects.filter(tenant=tenant).delete()

        sample_dir = Path(__file__).resolve().parents[3] / "sample_data"
        sap_source = SourceSystem.objects.get(tenant=tenant, kind=SourceSystem.SAP)
        utility_source = SourceSystem.objects.get(tenant=tenant, kind=SourceSystem.UTILITY)
        concur_source = SourceSystem.objects.get(tenant=tenant, kind=SourceSystem.CONCUR)

        sap_batch = IngestionBatch.objects.create(tenant=tenant, source=sap_source, original_filename="sap_material_documents.csv")
        import_sap_csv(sap_batch, ContentFile((sample_dir / "sap_material_documents.csv").read_bytes()))

        utility_batch = IngestionBatch.objects.create(tenant=tenant, source=utility_source, original_filename="utility_green_button_flat.csv")
        import_utility_csv(utility_batch, ContentFile((sample_dir / "utility_green_button_flat.csv").read_bytes()))

        concur_batch = IngestionBatch.objects.create(tenant=tenant, source=concur_source, original_filename="concur_itineraries.json")
        import_concur_json(concur_batch, load_sample_concur_payload(sample_dir / "concur_itineraries.json"))

        self.stdout.write(self.style.SUCCESS("Seeded demo data for analyst@breathe.demo / breathe-demo"))

