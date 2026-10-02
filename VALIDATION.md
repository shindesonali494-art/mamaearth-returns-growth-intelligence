# Validation Record

End-to-end validation passed after regenerating the SQLite seed loader with explicit SQL NULL handling.

- SQL row counts: customers=45, products=16, orders=180
- Report (a): total_orders=180, total_revenue=99860.20, avg_order_value=554.78
- Report (b): COUNT(*)=180, COUNT(rating)=165, difference=15
- Zero-order customer: [('C045', 'Vihaan')]
- Findings: {
  "cleaned_total_revenue_inr": 97358.3,
  "raw_total_revenue_inr": 99860.2,
  "duplicate_reconciliation_delta_inr": 2501.9,
  "return_rate_by_payment": {
    "CARD": 14.7,
    "COD": 44.4,
    "UPI": 18.9
  },
  "highest_risk_segment": {
    "payment_method": "COD",
    "city_tier": 2,
    "return_rate_pct": 54.5
  },
  "true_peak_month": {
    "month": "2026-03",
    "revenue_inr": 20318.9
  },
  "outlier_inflated_month": {
    "month": "2026-01",
    "apparent_revenue_inr": 29582.1,
    "corrected_revenue_inr": 11637.1
  }
}
- Visualization files generated successfully.
- Offline narrator generated successfully and passed its numeric accuracy checker.
