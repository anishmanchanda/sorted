from brain.eval import evaluate, load_labels, provider_match, sample_id, score_one


def test_labels_cover_required_senders():
    labels = load_labels()
    assert len(labels) >= 70
    types = {lab["type"] for lab in labels.values()}
    assert {"bill_due", "premium_due", "insurance_renewal", "subscription_receipt",
            "subscription_price_change", "meeting", "ignore"} <= types
    assert any(lab.get("injection") for lab in labels.values())
    assert any(lab.get("layout") == "v2" for lab in labels.values())


def test_scoring():
    gold = {"type": "bill_due", "provider": "HDFC Bank", "amount": 18432.5, "due_date": "2026-05-02"}
    good = {"type": "bill_due", "provider": "HDFC Bank Credit Card", "amount": "18432.50", "due_date": "2026-05-02"}
    assert all(score_one(good, gold).values())
    bad = {**good, "amount": 18432.0, "due_date": "2026-05-03"}
    assert score_one(bad, gold) == {"type": True, "provider": True, "amount": False, "due_date": False}
    assert score_one({"type": "ignore"}, {"type": "ignore"}) == {"type": True}
    assert provider_match("Delhi Transport Department", "Transport Dept, Govt of NCT of Delhi")
    assert not provider_match("Airtel", "HDFC Bank")


def test_evaluate_groups_by_handler():
    labels = {"a": {"type": "ignore"}, "b": {"type": "ignore"}}
    res = evaluate([("llm", "a", {"type": "ignore"}), ("ability:x@v1", "b", {"type": "bill_due"})], labels)
    assert res["llm"]["type"] == [True] and res["compiled"]["type"] == [False] and len(res["all"]["type"]) == 2
    assert sample_id("data/samples/sms/sms.jsonl#sms_2026-04_hdfc") == "sms_2026-04_hdfc"
    assert sample_id("data/samples/email/2026-04_bses.eml") == "2026-04_bses"
