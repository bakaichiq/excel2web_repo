import datetime as dt
from app.services.etl.importer import _distribute_qty_to_months

def test_distribution_spans_months():
    start=dt.date(2025,1,20)
    finish=dt.date(2025,2,10)
    rows=_distribute_qty_to_months(start,finish,22.0)
    assert len(rows)==2
    m1,q1=rows[0]
    m2,q2=rows[1]
    assert m1==dt.date(2025,1,1)
    assert m2==dt.date(2025,2,1)
    # 22 days total => 1 per day
    assert abs(q1-12.0)<1e-6
    assert abs(q2-10.0)<1e-6
