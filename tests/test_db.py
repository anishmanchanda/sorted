from datetime import date, datetime

from brain import db


def test_fact_links_to_source():
    db.init_db()
    with db.Session() as s:
        src = db.SourceRecord(kind="email", sender="a@b.in", body_hash="h1", received_at=datetime(2026, 4, 1))
        s.add(src)
        s.flush()
        s.add(db.Obligation(type="bill", provider="BSES", amount=100, due_date=date(2026, 4, 20), source_id=src.id))
        db.audit(s, "test", "insert", source=src.id)
        s.commit()
        ob = s.query(db.Obligation).one()
        assert ob.source_id == src.id and ob.status == "open"
        assert s.query(db.AuditLog).one().detail == {"source": src.id}
