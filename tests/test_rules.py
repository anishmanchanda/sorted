from datetime import date, datetime

from sqlalchemy import select

from brain import db, notify, rules, scheduler
from brain.validate import Extraction


def _setup(price: float):
    with db.Session() as s:
        src = db.SourceRecord(kind="email", sender="Netflix <info@account.netflix.com>", body_hash=f"h{price}",
                              received_at=datetime(2026, 7, 20))
        s.add(src)
        s.flush()
        s.add(db.Subscription(service="Netflix", price=price, source_id=src.id))
        s.commit()
        return src.id


CHANGE = Extraction(type="subscription_price_change", provider="Netflix", service="Netflix", old_price=499,
                    new_price=649, amount=649, due_date=date(2026, 8, 18))


def test_price_increase_rule_updates_state_reminds_and_alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(notify, "SINKS", [sent.append])
    src_id = _setup(499)
    with db.Session() as s:
        fired, effects = rules.apply(s, s.get(db.SourceRecord, src_id), CHANGE)
        s.commit()
    assert fired == ["subscription_price_increase"] and len(effects) == 2
    for effect in effects:
        effect()
    with db.Session() as s:
        sub = s.scalar(select(db.Subscription))
        assert float(sub.price) == 649 and sub.effective_date == date(2026, 8, 18)
    assert sent == ["Netflix is raising your price from ₹499 to ₹649 on 18 Aug 2026. Reply KEEP or CANCEL-HELP."]
    job = scheduler.get().get_job("rule:Netflix:2026-08-18:2")
    assert job.kwargs["text"].startswith("Netflix price rises to ₹649 on 18 Aug 2026")
    assert job.trigger.run_date.replace(tzinfo=None) == datetime(2026, 8, 16, 9, 0)


def test_no_alert_when_price_does_not_rise(monkeypatch):
    sent = []
    monkeypatch.setattr(notify, "SINKS", [sent.append])
    src_id = _setup(649)
    with db.Session() as s:
        fired, effects = rules.apply(s, s.get(db.SourceRecord, src_id), CHANGE)
    assert fired == ["subscription_price_update"] and effects == [] and sent == []


def test_condition_grammar():
    assert rules.holds("new_price > stored_price", {"new_price": 2, "stored_price": 1})
    assert not rules.holds("new_price > stored_price", {"new_price": 2})  # missing value never fires
    assert rules.holds("stock <= 5", {"stock": 5})
