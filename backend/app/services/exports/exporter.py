import datetime as dt
from pathlib import Path
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

from app.core.config import settings

def export_plan_fact_xlsx(data: dict, out_path: Path):
    # data: {"fact": [{"period":..., "value":...}], "plan": [...]}
    df_fact = pd.DataFrame(data["fact"]).rename(columns={"period":"period","value":"fact"})
    df_plan = pd.DataFrame(data["plan"]).rename(columns={"period":"period","value":"plan"})
    df = pd.merge(df_plan, df_fact, on="period", how="outer").fillna(0)
    df["variance"]=df["fact"]-df["plan"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name="plan_fact")
    return out_path

def export_kpi_pdf(kpi: dict, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    y = height - 20*mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20*mm, y, "KPI Report")
    y -= 10*mm
    c.setFont("Helvetica", 11)
    lines = [
        f"Project ID: {kpi['project_id']}",
        f"Period: {kpi['date_from']} — {kpi['date_to']}",
        f"Fact qty: {kpi['fact_qty']:.2f}",
        f"Plan qty: {kpi['plan_qty']:.2f}",
        f"Progress: {kpi['progress_pct']:.2f} %",
        f"Manhours: {kpi['manhours']:.2f}",
        f"Productivity: {kpi['productivity']:.4f}" if kpi.get("productivity") is not None else "Productivity: —",
    ]
    for ln in lines:
        c.drawString(20*mm, y, ln)
        y -= 7*mm
    c.showPage()
    c.save()
    return out_path

def default_export_path(prefix: str, ext: str) -> Path:
    ts = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return Path(settings.EXPORT_DIR) / f"{prefix}_{ts}.{ext}"
