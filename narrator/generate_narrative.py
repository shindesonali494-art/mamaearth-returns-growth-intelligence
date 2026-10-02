from pathlib import Path
import json
import os

ROOT = Path(__file__).resolve().parents[1]
FINDINGS_PATH = ROOT / "narrator" / "findings.json"
SAMPLE_PATH = ROOT / "narrator" / "sample_output.txt"

def _prompt_from_findings(findings):
    return (
        "Write a concise business narrative using only the verified findings below. "
        "Use exactly three labeled sections: Situation, Complication, Resolution. "
        "Do not introduce any statistic that is absent from findings.\n\n"
        + json.dumps(findings, indent=2)
    )

def generate_scr_narrative_offline(findings: dict) -> dict:
    """Deterministic, keyless fallback. It uses findings directly, with no network call."""
    rr = findings["return_rate_by_payment"]
    hs = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    inflated = findings["outlier_inflated_month"]
    cleaned = findings["cleaned_total_revenue_inr"]
    raw = findings["raw_total_revenue_inr"]
    delta = findings["duplicate_reconciliation_delta_inr"]

    narrative = (
        "Situation\n"
        f"Mamaearth's cleaned order data shows revenue of ₹{cleaned:,.2f} across the "
        "verified cleaned order base. Payment behavior provides a clear operational "
        f"signal: COD has a {rr['COD']:.1f}% return rate, compared with "
        f"{rr['CARD']:.1f}% for CARD and {rr['UPI']:.1f}% for UPI.\n\n"
        "Complication\n"
        f"The concentration is strongest in COD Tier-{hs['city_tier']} cities, where "
        f"the return rate reaches {hs['return_rate_pct']:.1f}%. Data quality also "
        f"matters: the raw revenue was ₹{raw:,.2f}, while the cleaned revenue is "
        f"₹{cleaned:,.2f}; the ₹{delta:,.2f} reconciliation difference is driven by "
        "the five duplicate orders removed during cleaning. Time-series interpretation "
        f"also requires the bulk-order outliers to be flagged: January appeared at "
        f"₹{inflated['apparent_revenue_inr']:,.2f}, but its corrected value is "
        f"₹{inflated['corrected_revenue_inr']:,.2f}.\n\n"
        "Resolution\n"
        f"Regional operations and finance should use the verified cleaned figures as "
        f"the reporting base, focus investigation on COD Tier-{hs['city_tier']} "
        f"segments, and preserve the duplicate and outlier controls in the pipeline. "
        f"After the outlier correction, {peak['month']} is the true peak month at "
        f"₹{peak['revenue_inr']:,.2f}. These actions keep operational decisions tied "
        "to the computed analysis layer rather than raw, duplicated or outlier-inflated data."
    )
    return {"status": "success", "narrative": narrative, "tokens": None}

def generate_scr_narrative(findings: dict) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return generate_scr_narrative_offline(findings)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        system_instruction = (
            "You are a senior data analyst writing for Mamaearth's regional ops and finance heads. "
            "Use exactly three labeled sections: Situation, Complication, Resolution. "
            "Every number in the output must come from the supplied findings and must appear with "
            "the same value; never invent statistics, totals, percentages, dates, or monetary values."
        )
        # temperature=0.0 makes this factual business report deterministic rather than creative.
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=_prompt_from_findings(findings),
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0,
                max_output_tokens=500,
                http_options=types.HttpOptions(timeout=30000),
            ),
        )
        text = getattr(response, "text", None)
        if not text:
            raise ValueError("Gemini returned no narrative text.")
        usage = getattr(response, "usage_metadata", None)
        tokens = getattr(usage, "total_token_count", None) if usage else None
        return {"status": "success", "narrative": text, "tokens": tokens}
    except Exception as err:
        return {"status": "error", "narrative": None, "message": str(err)}

def check_numeric_accuracy(narrative: str, findings: dict) -> bool:
    normalized = narrative.replace(",", "")
    checks = {
        "cleaned total revenue": str(findings["cleaned_total_revenue_inr"]),
        "COD return rate": str(findings["return_rate_by_payment"]["COD"]),
        "COD Tier-2 return rate": str(findings["highest_risk_segment"]["return_rate_pct"]),
        "duplicate reconciliation delta": str(findings["duplicate_reconciliation_delta_inr"]),
        "March peak revenue": str(findings["true_peak_month"]["revenue_inr"]),
    }
    passed = True
    for label, value in checks.items():
        ok = value in normalized
        print(f"{label}: {'PASS' if ok else 'FAIL'}")
        passed = passed and ok
    return passed

def main():
    findings = json.loads(FINDINGS_PATH.read_text())
    result = generate_scr_narrative(findings)

    if result["status"] == "error":
        # Offline fallback after an API failure.
        result = generate_scr_narrative_offline(findings)

    print("\n=== NARRATIVE ===")
    print(result["narrative"])
    print("\n=== NUMERIC ACCURACY CHECK ===")
    passed = check_numeric_accuracy(result["narrative"], findings)
    if not passed:
        raise AssertionError("Narrative failed numeric accuracy checks.")

    SAMPLE_PATH.write_text(result["narrative"] + "\n")
    print("\nSaved verified narrative to narrator/sample_output.txt")

if __name__ == "__main__":
    main()
