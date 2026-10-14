from brain.ml.classifier import EmailClassifier, Example
from brain.ml.train import held_out_report, labelled_examples, train
from brain.orchestrator import Orchestrator


def _ex(sender, subject, text, label, kind="email"):
    return Example(kind, sender, subject, text, label)


def test_rule_layer_for_known_sender_and_tfidf_for_unknown():
    exs = [_ex("Netflix <info@account.netflix.com>", "Your Netflix payment receipt", "Amount 499 next billing",
               "subscription_receipt")] * 2 + [
        _ex("Netflix <info@account.netflix.com>", "An update to your Netflix membership price", "price change",
            "subscription_price_change")] * 2 + [
        _ex(f"Shop{i} <offers@shop{i}.in>", f"Mega sale {i}", "Flat 60% off sale offer. Shop now. Unsubscribe.",
            "ignore") for i in range(4)]
    clf = EmailClassifier().fit(exs)
    assert clf.predict("email", "Netflix <info@account.netflix.com>", "Your Netflix payment receipt", "x") == \
        ("subscription_receipt", 1.0, "rule")
    label, conf, layer = clf.predict("email", "New <deals@newshop.in>", "Festival sale",
                                     "Flat 70% off festival sale offer. Shop now. Unsubscribe.")
    assert (label, layer) == ("ignore", "tfidf") and 0 < conf <= 1


def test_held_out_accuracy_and_confident_predictions_are_reliable():
    r = held_out_report(seed=7)
    assert r["test"] >= 20 and r["accuracy"] >= 0.8
    assert r["confident_accuracy"] >= 0.95  # mistakes stay below the threshold and go to the LLM


def test_confident_ignore_skips_llm_and_unsure_goes_to_llm(fixtures, label_llm, monkeypatch):
    train(labelled_examples(), save=False)
    promo = next(m for m in fixtures if "myntra" in m.raw_path)
    out = Orchestrator(llm=label_llm).ingest(promo)
    assert out["handler"].startswith("ml:") and out["type"] == "ignore" and label_llm.calls == []
    monkeypatch.setenv("BRAIN_CLASSIFIER_THRESHOLD", "1.01")  # nothing is confident enough
    swiggy = next(m for m in fixtures if "swiggy" in m.raw_path)
    assert Orchestrator(llm=label_llm).ingest(swiggy)["handler"] == "llm" and len(label_llm.calls) == 1
