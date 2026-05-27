# Tradeoffs

1. **No real SAP or Concur OAuth integration**

   Real enterprise integrations would require credentials, tenant-specific permissions, pagination, retries, and data contracts. For this prototype, uploaded SAP CSV and mocked Concur JSON show the normalization and review logic without hiding behind integration plumbing.

2. **No PDF bill parsing**

   Utility PDF parsing is brittle and vendor-specific. I chose a Green Button-style flattened export so the prototype can focus on billing periods, meters, kWh, demand, tariffs, and Scope 2 normalization.

3. **No auditor-grade emissions factor engine**

   The app uses a small seeded factor table for illustrative estimates. A production system would need versioned factors, geography rules, units, uncertainty, source citations, factor retirement, and possibly market-based Scope 2 instruments.

