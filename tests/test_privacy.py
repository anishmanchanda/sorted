from brain.filters import is_otp, looks_like_injection
from brain.redact import redact


def test_redaction_masks_identifiers_but_keeps_amounts_and_dates():
    text = ("Card 4111 1111 1111 4821, a/c 3000123456, policy 912345678, mobile 98100 00001, +91 98765-43210, "
            "mail rohan@example.in. Total Rs.18,432.50 due 02/05/2026, units 526, ref 20260415T103000.")
    out = redact(text)
    assert "XXXX XXXX XXXX 4821" in out and "4111" not in out
    assert "XXXXXX3456" in out and "3000123456" not in out
    assert "XXXXX5678" in out
    assert out.count("[phone]") == 2 and "[email]" in out
    assert "18,432.50" in out and "02/05/2026" in out and "526" in out and "20260415T103000" in out


def test_redaction_is_idempotent():
    once = redact("Card 4111-1111-1111-4821 and 9810000001")
    assert redact(once) == once


def test_otp_filter(fixtures):
    assert is_otp("482913 is your OTP for HDFC Bank NetBanking login. Do not share it.")
    assert is_otp("Use verification code 553201 to log in to Airtel Thanks app.")
    assert is_otp("Dear Customer, OTP for transaction of Rs 2,500.00 at FLIPKART is 771234. Valid for 5 mins.")
    otp = [m for m in fixtures if "otp" in m.raw_path]
    assert len(otp) == 4 and all(is_otp(m.body) for m in otp)
    others = [m for m in fixtures if "otp" not in m.raw_path]
    assert not [m.raw_path for m in others if is_otp(f"{m.subject}\n{m.body}")]


def test_injection_detector(fixtures):
    flagged = [m.raw_path for m in fixtures if looks_like_injection(m.redacted_text())]
    assert flagged == ["data/samples/email/m3_injection.eml"]


def test_redaction_masks_upi_ids():
    out = redact("Pay ramesh.k@okhdfcbank or 9876543210@ybl. Paid to netflix@icici. Mail rohan@example.in")
    assert "ramesh" not in out and "9876543210" not in out and "netflix@icici" not in out
    assert out.count("[upi]") == 3 and "[email]" in out
    assert redact(out) == out


def test_telegram_owner_rejects_bad_values(monkeypatch, tmp_path):
    import pytest

    from brain import telegram_bot

    owner_file = tmp_path / "telegram_owner"
    monkeypatch.setattr(telegram_bot, "OWNER_FILE", owner_file)
    monkeypatch.delenv("TELEGRAM_OWNER_ID", raising=False)
    monkeypatch.setattr(telegram_bot.config, "env", lambda k, d=None: None)
    assert telegram_bot.owner() is None
    owner_file.write_text("12345\n", encoding="utf-8")
    assert telegram_bot.owner() == 12345
    owner_file.write_text("", encoding="utf-8")  # a half-written file must not reopen the bot to anyone
    with pytest.raises(SystemExit):
        telegram_bot.owner()
    bad_env = {"TELEGRAM_OWNER_ID": "not-a-number"}
    monkeypatch.setattr(telegram_bot.config, "env", lambda k, d=None: bad_env.get(k))
    with pytest.raises(SystemExit):
        telegram_bot.owner()
