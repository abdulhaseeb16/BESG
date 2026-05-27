import csv
import io
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .models import ActivityRecord, EmissionFactor, Facility, RawRecord, ReviewEvent

HEADER_ALIASES = {
    "materialdocument": "material_document",
    "materialbeleg": "material_document",
    "document": "material_document",
    "materialdocumentitem": "item",
    "position": "item",
    "postingdate": "posting_date",
    "buchungsdatum": "posting_date",
    "plant": "plant",
    "werk": "plant",
    "material": "material",
    "materialdescription": "material_description",
    "materialkurztext": "material_description",
    "quantity": "quantity",
    "menge": "quantity",
    "unit": "unit",
    "meins": "unit",
    "amountincompanycodecurrency": "amount",
    "betrag": "amount",
    "currency": "currency",
    "waehrung": "currency",
    "purchaseorder": "purchase_order",
    "accountnumber": "account_number",
    "meternumber": "meter_number",
    "usagepoint": "usage_point",
    "startdate": "start_date",
    "enddate": "end_date",
    "kwh": "kwh",
    "demandkw": "demand_kw",
    "tariff": "tariff",
    "egridregion": "egrid_region",
}

UNIT_ALIASES = {
    "l": ("L", Decimal("1")),
    "liter": ("L", Decimal("1")),
    "litre": ("L", Decimal("1")),
    "gal": ("L", Decimal("3.78541")),
    "gallon": ("L", Decimal("3.78541")),
    "kwh": ("kWh", Decimal("1")),
    "kw": ("kW", Decimal("1")),
    "km": ("km", Decimal("1")),
    "mi": ("km", Decimal("1.60934")),
    "mile": ("km", Decimal("1.60934")),
    "usd": ("USD", Decimal("1")),
    "inr": ("INR", Decimal("1")),
    "room_night": ("room_night", Decimal("1")),
}

AIRPORT_DISTANCE_KM = {
    ("BLR", "DEL"): Decimal("1700"),
    ("DEL", "BOM"): Decimal("1148"),
    ("SFO", "JFK"): Decimal("4150"),
}


def clean_header(value):
    return "".join(ch for ch in value.strip().lower() if ch.isalnum())


def normalize_row(row):
    normalized = {}
    for key, value in row.items():
        normalized[HEADER_ALIASES.get(clean_header(key), clean_header(key))] = value.strip() if isinstance(value, str) else value
    return normalized


def parse_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def parse_date(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def normalize_unit(quantity, unit):
    if quantity is None:
        return None, ""
    unit_key = (unit or "").strip().lower()
    if unit_key not in UNIT_ALIASES:
        return quantity, unit or ""
    normalized_unit, factor = UNIT_ALIASES[unit_key]
    return (quantity * factor).quantize(Decimal("0.001")), normalized_unit


def find_facility_for_plant(tenant, plant):
    if not plant:
        return None
    for facility in Facility.objects.filter(tenant=tenant):
        if facility.code == plant or plant in facility.plant_codes:
            return facility
    return None


def find_facility_for_meter(tenant, meter):
    if not meter:
        return None
    for facility in Facility.objects.filter(tenant=tenant):
        if facility.code == meter or meter in facility.meter_numbers:
            return facility
    return None


def estimate(tenant, factor_key, quantity):
    if quantity is None:
        return None
    factor = EmissionFactor.objects.filter(tenant=tenant, key=factor_key).first()
    if not factor:
        return None
    return (quantity * factor.kg_co2e_per_unit).quantize(Decimal("0.001"))


def duplicate_exists(tenant, source, source_row_id, raw_record_id=None):
    query = ActivityRecord.objects.filter(tenant=tenant, source=source, source_row_id=source_row_id)
    if raw_record_id:
        query = query.exclude(raw_record_id=raw_record_id)
    return query.exists()


def make_raw_record(batch, source_row_id, payload):
    return RawRecord.objects.create(
        tenant=batch.tenant,
        batch=batch,
        source=batch.source,
        source_row_id=source_row_id,
        raw_payload=payload,
    )


def create_activity(raw, **fields):
    activity = ActivityRecord.objects.create(
        tenant=raw.tenant,
        source=raw.source,
        batch=raw.batch,
        raw_record=raw,
        source_row_id=raw.source_row_id,
        **fields,
    )
    ReviewEvent.objects.create(
        tenant=activity.tenant,
        activity=activity,
        event_type=ReviewEvent.IMPORTED,
        note="Imported and normalized by parser",
        after=activity.canonical_payload,
    )
    return activity


def update_batch_counts(batch):
    activities = batch.activities.all()
    batch.imported_count = activities.exclude(status=ActivityRecord.FAILED).count()
    batch.failed_count = activities.filter(status=ActivityRecord.FAILED).count()
    batch.suspicious_count = sum(1 for activity in activities if activity.flags)
    batch.save(update_fields=["imported_count", "failed_count", "suspicious_count"])


def import_sap_csv(batch, uploaded_file):
    text = uploaded_file.read().decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    activities = []
    for index, raw_row in enumerate(rows, start=1):
        row = normalize_row(raw_row)
        source_row_id = f"{row.get('material_document', 'missing')}-{row.get('item', index)}"
        raw = make_raw_record(batch, source_row_id, raw_row)
        flags = []
        quantity = parse_decimal(row.get("quantity"))
        unit = row.get("unit", "")
        normalized_quantity, normalized_unit = normalize_unit(quantity, unit)
        posting_date = parse_date(row.get("posting_date"))
        facility = find_facility_for_plant(batch.tenant, row.get("plant"))
        amount = parse_decimal(row.get("amount"))
        description = row.get("material_description") or row.get("material") or ""
        lower_description = description.lower()

        if not facility:
            flags.append("missing_facility_mapping")
        if not posting_date:
            flags.append("unparseable_date")
        if quantity is None and amount is None:
            flags.append("missing_quantity_or_spend")
        if quantity is not None and (unit or "").lower() not in UNIT_ALIASES:
            flags.append("unknown_unit")
        if duplicate_exists(batch.tenant, batch.source, source_row_id, raw.id):
            flags.append("duplicate_source_row")

        is_fuel = any(token in lower_description for token in ["diesel", "petrol", "gasoline", "fuel", "kraftstoff"])
        if is_fuel:
            activity_type = "fuel_combustion"
            scope = "scope_1"
            scope_category = "stationary_or_mobile_fuel"
            factor_key = "diesel_litre"
            if normalized_quantity and normalized_quantity > Decimal("50000"):
                flags.append("outlier_fuel_volume")
            estimated = estimate(batch.tenant, factor_key, normalized_quantity)
        else:
            activity_type = "procurement_spend"
            scope = "scope_3"
            scope_category = "category_1_purchased_goods"
            factor_key = "procurement_usd"
            normalized_quantity = amount
            normalized_unit = row.get("currency", "USD") or "USD"
            estimated = estimate(batch.tenant, factor_key, amount)
            if amount and amount > Decimal("250000"):
                flags.append("outlier_procurement_spend")

        status = ActivityRecord.FAILED if any(flag in flags for flag in ["missing_quantity_or_spend", "unparseable_date"]) else ActivityRecord.PENDING
        activities.append(
            create_activity(
                raw,
                facility=facility,
                activity_date=posting_date,
                period_start=posting_date,
                period_end=posting_date,
                scope=scope,
                scope_category=scope_category,
                activity_type=activity_type,
                description=description,
                quantity=quantity,
                unit=unit,
                normalized_quantity=normalized_quantity,
                normalized_unit=normalized_unit,
                spend_amount=amount,
                currency=row.get("currency", ""),
                emission_factor_key=factor_key,
                estimated_kg_co2e=estimated,
                status=status,
                flags=flags,
                canonical_payload=row,
            )
        )
    update_batch_counts(batch)
    return activities


def import_utility_csv(batch, uploaded_file):
    text = uploaded_file.read().decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    activities = []
    for index, raw_row in enumerate(rows, start=1):
        row = normalize_row(raw_row)
        source_row_id = f"{row.get('account_number', 'acct')}-{row.get('meter_number', 'meter')}-{row.get('start_date', index)}"
        raw = make_raw_record(batch, source_row_id, raw_row)
        flags = []
        kwh = parse_decimal(row.get("kwh"))
        demand_kw = parse_decimal(row.get("demand_kw"))
        start = parse_date(row.get("start_date"))
        end = parse_date(row.get("end_date"))
        facility = find_facility_for_meter(batch.tenant, row.get("meter_number"))
        region = row.get("egrid_region") or (facility.egrid_region if facility else "")
        factor_key = f"electricity_{region.lower()}" if region else "electricity_default"

        if not facility:
            flags.append("missing_meter_mapping")
        if not start or not end:
            flags.append("unparseable_billing_period")
        if start and end and end <= start:
            flags.append("invalid_billing_period")
        if kwh is None or kwh <= 0:
            flags.append("non_positive_kwh")
        if demand_kw and demand_kw > Decimal("2000"):
            flags.append("outlier_demand_kw")
        if kwh and kwh > Decimal("1000000"):
            flags.append("outlier_electricity_usage")
        if duplicate_exists(batch.tenant, batch.source, source_row_id, raw.id):
            flags.append("duplicate_source_row")
        if facility and start and end:
            overlap = ActivityRecord.objects.filter(
                tenant=batch.tenant,
                source=batch.source,
                facility=facility,
                period_start__lt=end,
                period_end__gt=start,
            ).exists()
            if overlap:
                flags.append("overlapping_billing_period")

        status = ActivityRecord.FAILED if any(flag in flags for flag in ["non_positive_kwh", "unparseable_billing_period", "invalid_billing_period"]) else ActivityRecord.PENDING
        activities.append(
            create_activity(
                raw,
                facility=facility,
                activity_date=end,
                period_start=start,
                period_end=end,
                scope="scope_2",
                scope_category="purchased_electricity_location_based",
                activity_type="electricity",
                description=f"{row.get('tariff', 'Electricity')} meter {row.get('meter_number', '')}",
                quantity=kwh,
                unit="kWh",
                normalized_quantity=kwh,
                normalized_unit="kWh",
                emission_factor_key=factor_key,
                estimated_kg_co2e=estimate(batch.tenant, factor_key, kwh),
                status=status,
                flags=flags,
                canonical_payload={**row, "demand_kw": str(demand_kw) if demand_kw is not None else None},
            )
        )
    update_batch_counts(batch)
    return activities


def import_concur_json(batch, payload):
    activities = []
    for trip in payload.get("trips", []):
        for index, segment in enumerate(trip.get("segments", []), start=1):
            source_row_id = segment.get("id") or f"{trip.get('trip_id')}-{index}"
            raw = make_raw_record(batch, source_row_id, segment)
            flags = []
            segment_type = segment.get("type")
            date = parse_date(segment.get("date") or segment.get("check_in"))
            quantity = parse_decimal(segment.get("distance_km") or segment.get("distance"))
            unit = segment.get("unit", "km")
            normalized_quantity, normalized_unit = normalize_unit(quantity, unit)

            if duplicate_exists(batch.tenant, batch.source, source_row_id, raw.id):
                flags.append("duplicate_source_row")

            if segment_type == "flight":
                activity_type = "business_travel_flight"
                factor_key = "flight_passenger_km"
                if normalized_quantity is None:
                    route = (segment.get("origin"), segment.get("destination"))
                    normalized_quantity = AIRPORT_DISTANCE_KM.get(route)
                    normalized_unit = "passenger_km" if normalized_quantity else ""
                    if normalized_quantity is None:
                        flags.append("missing_flight_distance")
                else:
                    normalized_unit = "passenger_km"
                if normalized_quantity and normalized_quantity > Decimal("15000"):
                    flags.append("outlier_flight_distance")
            elif segment_type == "hotel":
                activity_type = "business_travel_hotel"
                factor_key = "hotel_room_night"
                normalized_quantity = parse_decimal(segment.get("room_nights"))
                normalized_unit = "room_night"
                if not normalized_quantity or normalized_quantity <= 0:
                    flags.append("missing_room_nights")
            else:
                activity_type = "business_travel_ground"
                factor_key = "ground_transport_km"
                if normalized_quantity is None or normalized_quantity <= 0:
                    flags.append("missing_ground_distance")

            status = ActivityRecord.FAILED if any(flag.startswith("missing_") for flag in flags) else ActivityRecord.PENDING
            activities.append(
                create_activity(
                    raw,
                    facility=None,
                    activity_date=date,
                    period_start=date,
                    period_end=parse_date(segment.get("check_out")) or date,
                    scope="scope_3",
                    scope_category="category_6_business_travel",
                    activity_type=activity_type,
                    description=segment.get("description", segment_type or "travel segment"),
                    quantity=quantity,
                    unit=unit,
                    normalized_quantity=normalized_quantity,
                    normalized_unit=normalized_unit,
                    emission_factor_key=factor_key,
                    estimated_kg_co2e=estimate(batch.tenant, factor_key, normalized_quantity),
                    status=status,
                    flags=flags,
                    canonical_payload=segment,
                )
            )
    update_batch_counts(batch)
    return activities


def load_sample_concur_payload(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
