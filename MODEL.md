# Data Model

## Core Shape

The model separates source truth from normalized review data:

- `Tenant` represents a client company. Every operational table is tenant-scoped.
- `Facility` maps confusing source identifiers such as SAP plant codes and utility meter numbers to a known site.
- `SourceSystem` identifies where data came from: SAP, utility export, or Concur.
- `IngestionBatch` records one upload or API pull, including counts by status.
- `RawRecord` stores the untouched source row or API segment as JSON.
- `ActivityRecord` stores the canonical row analysts review.
- `ReviewEvent` stores every analyst action or system import event.
- `EmissionFactor` stores small demo factors used for illustrative kgCO2e estimates.

This lets the app answer: which source produced this row, when it was imported, how it was interpreted, whether it was edited, who approved it, and what raw source data backs it up.

## Normalized Activity Records

`ActivityRecord` contains source row id, activity dates, facility, Scope 1/2/3 categorization, activity type, original quantity/unit, normalized quantity/unit, spend/currency where relevant, factor key, estimated kgCO2e, flags, status, and lock metadata.

Rows are not overwritten blindly. The raw payload stays intact, while the canonical payload records the normalized interpretation. If a reviewer edits a pending row, a `ReviewEvent` captures before/after details.

## Multi-Tenancy

Tenancy is explicit at the model level, not inferred from filenames or users. Source systems, facilities, batches, raw records, activity records, review events, and factors all carry a tenant. API queries filter by tenant id when provided. In a production system this would be enforced from the authenticated user's organization membership.

## Scope Mapping

- SAP fuel rows map to Scope 1 because the company combusts purchased fuel.
- Utility electricity rows map to Scope 2 using location-based eGRID-style factors.
- Procurement spend rows map to Scope 3 Category 1.
- Flights, hotels, and ground travel map to Scope 3 Category 6.

The factors are deliberately small demo factors, not an auditor-grade emissions library.

## Approval Locking

Approval marks an activity row as locked. Locked rows cannot be edited through the normal update endpoint. This mirrors audit expectations: post-approval changes should be traceable as explicit review events or new records, not silent mutations.

