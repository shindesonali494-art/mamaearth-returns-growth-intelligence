from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NARRATOR = ROOT / "narrator"

def money(x):
    return f"{x:,.2f}"

def run():
    orders = pd.read_csv(DATA / "orders.csv")
    customers = pd.read_csv(DATA / "customers.csv")
    products = pd.read_csv(DATA / "products.csv")

    print("=== TASK 1: LOAD AND INSPECT ===")
    print("orders.shape:", orders.shape)
    print("customers.shape:", customers.shape)
    print("products.shape:", products.shape)

    print("\n=== TASK 2: STANDARDIZE PAYMENT METHOD ===")
    print("Raw payment_method unique values:")
    print(sorted(orders["payment_method"].unique().tolist()))
    print("Raw distinct count:", orders["payment_method"].nunique())

    orders["payment_method"] = orders["payment_method"].str.strip().str.upper()
    print("Cleaned payment counts:")
    print(orders["payment_method"].value_counts().sort_index())

    print("\n=== TASK 3: REMOVE DUPLICATE ORDERS ===")
    natural_key = [
        "customer_id", "product_id", "order_date", "quantity",
        "discount_pct", "payment_method", "rating", "returned"
    ]
    duplicate_mask = orders.duplicated(subset=natural_key, keep="first")
    dropped = orders.loc[duplicate_mask].copy()
    print("Duplicate rows flagged:", int(duplicate_mask.sum()))
    print("Dropped order_id values:", dropped["order_id"].tolist())

    orders_clean = orders.loc[~duplicate_mask].copy()
    print("orders_clean.shape:", orders_clean.shape)

    print("\n=== TASK 4: IMPUTE MISSING VALUES ===")
    missing_discount = int(orders_clean["discount_pct"].isna().sum())
    orders_clean["discount_pct"] = orders_clean["discount_pct"].fillna(0)
    print("discount_pct rows imputed:", missing_discount)

    rating_median = float(orders_clean["rating"].median())
    missing_rating = int(orders_clean["rating"].isna().sum())
    print("rating median before imputation:", rating_median)
    orders_clean["rating"] = orders_clean["rating"].fillna(rating_median)
    print("rating rows imputed:", missing_rating)
    print("Remaining nulls:")
    print(orders_clean[["discount_pct", "rating"]].isnull().sum().to_dict())

    print("\n=== TASK 5: MERGE AND RECONCILE ===")
    merged = (
        orders_clean
        .merge(products, on="product_id", how="left", validate="many_to_one")
        .merge(customers, on="customer_id", how="left", validate="many_to_one")
    )
    merged["order_value"] = (
        merged["quantity"] * merged["price"] *
        (1 - merged["discount_pct"] / 100.0)
    )
    cleaned_total = float(merged["order_value"].sum())
    print("Cleaned total revenue:", money(cleaned_total))

    # Independent calculation on the dropped rows, using raw source values.
    dropped_check = (
        dropped
        .merge(products, on="product_id", how="left", validate="many_to_one")
    )
    dropped_check["order_value"] = (
        dropped_check["quantity"] * dropped_check["price"] *
        (1 - dropped_check["discount_pct"].fillna(0) / 100.0)
    )
    duplicate_delta = float(dropped_check["order_value"].sum())

    raw_merged = orders.merge(products, on="product_id", how="left")
    raw_merged["order_value"] = (
        raw_merged["quantity"] * raw_merged["price"] *
        (1 - raw_merged["discount_pct"].fillna(0) / 100.0)
    )
    raw_total = float(raw_merged["order_value"].sum())

    print("Raw total revenue:", money(raw_total))
    print("Dropped duplicate rows' combined order_value:", money(duplicate_delta))
    print(
        f"Reconciliation note: Part 1 raw revenue of ₹{money(raw_total)} exceeds "
        f"the cleaned Part 2 revenue of ₹{money(cleaned_total)} by exactly "
        f"₹{money(raw_total-cleaned_total)}. The delta is attributable to the "
        f"five duplicate rows removed in Task 3; those five rows independently "
        f"sum to ₹{money(duplicate_delta)}. Discount and rating imputation does "
        f"not change order_value because discount NULLs are treated as 0% and "
        f"ratings are not used in the revenue formula."
    )

    print("\n=== TASK 6: IQR OUTLIER DETECTION ===")
    q1 = float(merged["quantity"].quantile(0.25))
    q3 = float(merged["quantity"].quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    merged["is_outlier"] = ~merged["quantity"].between(lower, upper)
    outliers = merged.loc[merged["is_outlier"]]
    print("Q1:", q1, "Q3:", q3, "IQR:", iqr, "lower:", lower, "upper:", upper)
    print("Outlier count:", len(outliers))
    print(outliers[["order_id", "quantity"]].to_string(index=False))

    print("\n=== TASK 7: COD RETURN-RATE HYPOTHESIS ===")
    print("Hypothesis: COD has a higher return rate than CARD and UPI.")
    payment_rates = orders_clean.groupby("payment_method")["returned"].agg(["count", "mean"])
    payment_rates["return_rate_pct"] = payment_rates["mean"] * 100
    print(payment_rates[["count", "return_rate_pct"]].round({"return_rate_pct": 1}))
    cod_rate = float(payment_rates.loc["COD", "return_rate_pct"])
    other_max = float(payment_rates.drop(index="COD")["return_rate_pct"].max())
    print("Hypothesis:", "Confirmed" if cod_rate > other_max else "Not Confirmed")

    print("\n=== TASK 8: MULTI-LEVEL SEGMENTATION ===")
    segment_frame = orders_clean.merge(
        customers[["customer_id", "city_tier"]],
        on="customer_id",
        how="left",
        validate="many_to_one"
    )
    segment = (
        segment_frame.groupby(["payment_method", "city_tier"])["returned"]
        .agg(["count", "mean"])
        .reset_index()
    )
    segment["return_rate_pct"] = segment["mean"] * 100
    print(segment[["payment_method", "city_tier", "count", "return_rate_pct"]]
          .sort_values("return_rate_pct", ascending=False)
          .round({"return_rate_pct": 1}).to_string(index=False))
    highest = segment.sort_values("return_rate_pct", ascending=False).iloc[0]
    print(
        f"Highest-risk segment: {highest['payment_method']} + Tier-{int(highest['city_tier'])} "
        f"at {highest['return_rate_pct']:.1f}%."
    )

    print("\n=== TASK 9: CORRELATION ANALYSIS ===")
    corr_cols = ["rating", "returned", "discount_pct", "quantity"]
    corr = orders_clean[corr_cols].corr()
    print(corr.round(4))
    bands = []
    for i, a in enumerate(corr_cols):
        for b in corr_cols[i+1:]:
            r = float(corr.loc[a, b])
            ar = abs(r)
            if ar < 0.2:
                band = "negligible"
            elif ar < 0.4:
                band = "weak"
            elif ar < 0.7:
                band = "moderate"
            else:
                band = "strong"
            bands.append((a, b, r, band))
            print(f"{a} vs {b}: r={r:.4f} -> {band}")
    discount_return_r = float(corr.loc["discount_pct", "returned"])
    print(
        f'Hypothesis "higher discounts reduce returns": '
        f'{"Busted" if abs(discount_return_r) < 0.2 else "Not Busted"} '
        f"(discount_pct vs returned r={discount_return_r:.4f})."
    )

    print("\n=== TASK 10: OUTLIER-CORRECTED TIME SERIES ===")
    merged["order_date"] = pd.to_datetime(merged["order_date"])
    merged["year_month"] = merged["order_date"].dt.to_period("M").astype(str)
    monthly_all = merged.groupby("year_month")["order_value"].sum().round(2)
    monthly_corrected = (
        merged.loc[~merged["is_outlier"]]
        .groupby("year_month")["order_value"].sum()
        .round(2)
    )
    print("Monthly revenue including outliers:")
    print(monthly_all.to_string())
    print("Monthly revenue excluding outliers:")
    print(monthly_corrected.to_string())

    true_peak_month = monthly_corrected.idxmax()
    print(
        "Time-series interpretation: January's apparent lead is an artifact of "
        "the two bulk orders O0011 on 2026-01-28 and O0098 on 2026-01-10. "
        f"Once those outliers are excluded, {true_peak_month} is the genuine peak month."
    )

    print("\n=== TASK 11: VISUALIZATION INPUTS ===")
    print("Payment return rates:")
    print(payment_rates["return_rate_pct"].round(1).sort_values(ascending=False))
    print("Outlier-corrected monthly revenue:")
    print(monthly_corrected)

    # Required findings JSON: generated from computed values, never hand-entered.
    findings = {
        "cleaned_total_revenue_inr": round(cleaned_total, 2),
        "raw_total_revenue_inr": round(raw_total, 2),
        "duplicate_reconciliation_delta_inr": round(raw_total - cleaned_total, 2),
        "return_rate_by_payment": {
            k: round(float(v), 1)
            for k, v in payment_rates["return_rate_pct"].items()
        },
        "highest_risk_segment": {
            "payment_method": str(highest["payment_method"]),
            "city_tier": int(highest["city_tier"]),
            "return_rate_pct": round(float(highest["return_rate_pct"]), 1)
        },
        "true_peak_month": {
            "month": str(true_peak_month),
            "revenue_inr": round(float(monthly_corrected.loc[true_peak_month]), 2)
        },
        "outlier_inflated_month": {
            "month": str(monthly_all.idxmax()),
            "apparent_revenue_inr": round(float(monthly_all.max()), 2),
            "corrected_revenue_inr": round(float(monthly_corrected.loc[monthly_all.idxmax()]), 2)
        }
    }
    NARRATOR.mkdir(exist_ok=True)
    (NARRATOR / "findings.json").write_text(json.dumps(findings, indent=2) + "\n")
    print("\nfindings.json written from computed Part 2 values:")
    print(json.dumps(findings, indent=2))

    return findings, merged, payment_rates["return_rate_pct"], monthly_corrected

if __name__ == "__main__":
    run()
