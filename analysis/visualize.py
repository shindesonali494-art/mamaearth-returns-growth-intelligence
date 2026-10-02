from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "visualizations"

def main():
    OUT.mkdir(exist_ok=True)

    orders = pd.read_csv(DATA / "orders.csv")
    products = pd.read_csv(DATA / "products.csv")
    customers = pd.read_csv(DATA / "customers.csv")

    orders["payment_method"] = orders["payment_method"].str.strip().str.upper()
    key = [
        "customer_id", "product_id", "order_date", "quantity",
        "discount_pct", "payment_method", "rating", "returned"
    ]
    orders = orders.loc[~orders.duplicated(subset=key, keep="first")].copy()
    orders["discount_pct"] = orders["discount_pct"].fillna(0)
    orders["rating"] = orders["rating"].fillna(orders["rating"].median())

    merged = (orders.merge(products, on="product_id", validate="many_to_one")
                    .merge(customers, on="customer_id", validate="many_to_one"))
    merged["order_value"] = merged["quantity"] * merged["price"] * (1 - merged["discount_pct"]/100)
    merged["is_outlier"] = ~merged["quantity"].between(
        merged["quantity"].quantile(.25) - 1.5*(merged["quantity"].quantile(.75)-merged["quantity"].quantile(.25)),
        merged["quantity"].quantile(.75) + 1.5*(merged["quantity"].quantile(.75)-merged["quantity"].quantile(.25))
    )
    rates = (orders.groupby("payment_method")["returned"].mean()*100).sort_values(ascending=False)

    ax = rates.plot(kind="bar")
    ax.set_title("COD Returns at 44.4% — 3x Card")
    ax.set_xlabel("Payment Method")
    ax.set_ylabel("Return Rate (%)")
    ax.set_xticklabels(rates.index, rotation=0)
    for i, v in enumerate(rates):
        ax.text(i, v + 1, f"{v:.1f}%", ha="center")
    plt.tight_layout()
    plt.savefig(OUT / "return_rate_by_payment.png", dpi=160)
    plt.close()

    merged["order_date"] = pd.to_datetime(merged["order_date"])
    merged["year_month"] = merged["order_date"].dt.to_period("M").astype(str)
    monthly = (merged.loc[~merged["is_outlier"]]
               .groupby("year_month")["order_value"].sum())
    ax = monthly.plot(kind="line", marker="o")
    peak = monthly.idxmax()
    ax.set_title(f"Outlier-Corrected Monthly Revenue — Peak: {peak}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue (INR)")
    ax.set_xticks(range(len(monthly)))
    ax.set_xticklabels(monthly.index, rotation=45)
    plt.tight_layout()
    plt.savefig(OUT / "monthly_revenue_trend.png", dpi=160)
    plt.close()
    print("Created visualization files in:", OUT)

if __name__ == "__main__":
    main()
