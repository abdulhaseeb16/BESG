# Sources

## SAP Fuel and Procurement

Researched format: SAP S/4HANA material document API/export shape with document header and item concepts. The prototype uses CSV because analysts often receive extracts rather than live SAP credentials during onboarding.

Source: https://help.sap.com/docs/SAP_S4HANA_CLOUD/3f57e7df4a114edabffe8b2d581a59ed/d4c919581bc30a02e10000000a44147b.html

Sample data includes document ids, item ids, posting dates, plant codes, material descriptions, quantities, units, spend, currency, and purchase orders. German aliases are included because SAP installations often localize labels.

Would break in production: unmapped material masters, custom movement types, multiple company codes, nonstandard units, and missing plant lookup data.

## Utility Electricity

Researched format: Green Button-style electricity usage exports and business utility bill concepts.

Sources:

- https://green-button.github.io/faq/
- https://www.energy.gov/sites/default/files/2024-04/understanding-your-utility-bill.pdf
- https://www.epa.gov/egrid

Sample data includes meter numbers, service periods, kWh, demand kW, tariff labels, account numbers, and eGRID regions. This reflects the fact that utility billing periods rarely map perfectly to calendar months.

Would break in production: PDF-only bills, interval readings, changed meter numbers, overlapping corrected bills, market-based renewable energy instruments, and supplier-specific factors.

## Corporate Travel

Researched format: SAP Concur itinerary/travel API concepts.

Source: https://developer.concur.com/api-reference/travel/itinerary-v4/v4.itinerary.html

Sample data includes flights, hotels, and ground transport. Flight rows include airport codes because distance is not always directly supplied; the prototype flags missing distance instead of pretending it can calculate every route.

Would break in production: real OAuth, cancellations, flight class, multi-passenger trips, code-shares, missing airport metadata, and travel platform schema differences.

