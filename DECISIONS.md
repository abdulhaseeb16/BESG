# Decisions

## SAP

I chose a SAP S/4HANA material-document style export rather than trying to integrate directly with SAP. The sample columns mirror material document item concepts: document id, item id, posting date, plant, material, quantity, unit, amount, currency, and purchase order.

Handled subset:

- Fuel material movements with inconsistent units such as `L`, `GAL`, and German aliases.
- Procurement rows with spend and currency.
- English and German column headers.
- Plant code lookup to facilities.

Ignored:

- Real SAP OAuth, OData pagination, IDoc parsing, batch classification, and full material master enrichment.

PM question: should procurement emissions use supplier-specific factors, category-average spend factors, or product-level lifecycle factors?

## Utility Electricity

I chose a portal/export workflow flattened from Green Button-style utility data because facilities teams commonly pull bills or portal exports. The sample includes meter number, billing period, kWh, demand kW, tariff, and eGRID region.

Handled subset:

- Monthly billing-period rows.
- Billing periods that do not align perfectly to calendar months.
- Meter-to-facility lookup.
- Negative/zero usage and overlapping-period warnings.

Ignored:

- PDF bill extraction, interval data, taxes/fees, coincident peak demand logic, and supplier-specific market-based instruments.

PM question: do analysts need meter-level audit evidence, account-level invoices, or both?

## Corporate Travel

I chose a mocked Concur itinerary import because travel platforms usually expose trips and segments rather than one clean emissions row. The mock import includes air, hotel, and ground segments.

Handled subset:

- Flights with origin/destination airport codes and optional distance.
- Hotels as room nights.
- Ground transport with km/mi units.

Ignored:

- Real Concur OAuth, employee identity, class-of-service factors, radiative forcing, multi-leg fare reconciliation, and cancellation handling.

PM question: should travel estimates be recalculated by Breathe ESG or trusted from the travel platform if provided?

## Review Workflow

Rows begin as pending, failed, or suspicious. Analysts can reject or approve rows. Approval locks the row. Suspicious flags remain visible even when the row is approved, because approval means the analyst accepted the evidence, not that the source row was clean.

