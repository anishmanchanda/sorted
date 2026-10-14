from datetime import date, datetime

from brain.validate import Extraction, validate

RECEIVED = datetime(2026, 4, 12, 9, 0)


def test_valid_bill_passes():
    ext = Extraction(type="bill_due", provider="HDFC Bank", amount=18432.5, due_date=date(2026, 5, 2))
    assert validate(ext, RECEIVED) == []


def test_rules():
    assert "amount must be > 0" in validate(Extraction(type="bill_due", provider="X", amount=0,
                                                       due_date=date(2026, 5, 2)), RECEIVED)
    assert "provider is empty" in validate(Extraction(type="bill_due", provider=" ", amount=10,
                                                      due_date=date(2026, 5, 2)), RECEIVED)
    assert "due_date missing" in validate(Extraction(type="premium_due", provider="LIC", amount=10), RECEIVED)
    far = validate(Extraction(type="bill_due", provider="X", amount=1, due_date=date(2030, 1, 1)), RECEIVED)
    assert far and "outside" in far[0]
    assert validate(Extraction(type="meeting", provider="Apollo", due_date=date(2026, 4, 15)), RECEIVED) == []
    assert validate(Extraction(type="ignore"), RECEIVED) == []
