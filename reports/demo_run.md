# Sorted demo run

Generated 2026-10-14 15:18 by `make demo`. LLM routes: small=cerebras/gpt-oss-120b, strong=openai/gpt-5.4. Compile after 3 accepted traces; shadow runs = 1 (demo setting; default 2). Costs are estimates from BRAIN_PRICES.

```text

=== Month 1 · April 2026 ===
  01 Apr email airtel.com               LLM       bill_due                   Airtel Xstream Fiber ₹1,178.82 due 20 Apr [open]
  01 Apr sms   AIRTEL                   LLM       bill_due                   Airtel ₹1,178.82 due 20 Apr            [duplicate]
  03 Apr sms   HDFCBK                   -                                                                           [OTP dropped before storage]
  05 Apr email spotify.com              LLM       subscription_receipt       Spotify ₹119.00 due 05 May             [open]
  05 Apr email bsesdelhi.com            LLM       bill_due                   BSES Rajdhani ₹959.00 due 20 Apr       [open]
  09 Apr email myntra.com               LLM       ignore                                                            [ignored]
  10 Apr email licindia.in              LLM       premium_due                LIC ₹4,215.00 due 28 Apr               [open]
  10 Apr email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 15 Apr              [open]
  12 Apr email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹25,264.52 due 02 May        [open]
  12 Apr sms   HDFCBK                   LLM       bill_due                   HDFC Bank ₹25,264.52 due 02 May        [duplicate]
  18 Apr email account.netflix.com      LLM       subscription_receipt       Netflix ₹499.00 due 18 May             [open]
  [ml] retrained the local classifier on 10 LLM-labelled messages (0 sender rules)
  -- 10 messages, 0 handled by local code, 10 LLM calls, privacy score 0%

=== Month 2 · May 2026 ===
  01 May email airtel.com               LLM       bill_due                   Airtel Xstream Fiber ₹1,178.82 due 20 May [open]
  01 May sms   AIRTEL                   LLM       bill_due                   Airtel ₹1,178.82 due 20 May            [duplicate]
  02 May sms   JIOMRT                   LLM       ignore                                                            [ignored]
  05 May email spotify.com              LLM       subscription_receipt       Spotify ₹119.00 due 05 Jun             [open]
  05 May email bsesdelhi.com            LLM       bill_due                   BSES Rajdhani ₹2,051.00 due 20 May     [open]
  10 May email licindia.in              LLM       premium_due                LIC ₹4,215.00 due 28 May               [open]
  11 May email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 16 May              [open]
  11 May pdf   pdf                      LLM       document_expiry            Transport Department  due 10 Nov       [document]
  12 May email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹15,425.79 due 01 Jun        [open]
  12 May sms   HDFCBK                   LLM       bill_due                   HDFC Bank ₹15,425.79 due 01 Jun        [duplicate]
  17 May sms   AMAZON                   -                                                                           [OTP dropped before storage]
  18 May email account.netflix.com      LLM       subscription_receipt       Netflix ₹499.00 due 18 Jun             [open]
  22 May email swiggy.in                LLM       ignore                                                            [ignored]
  [ml] retrained the local classifier on 22 LLM-labelled messages (9 sender rules)
  -- 12 messages, 0 handled by local code, 12 LLM calls, privacy score 0%

=== Month 3 · June 2026 ===
  01 Jun email airtel.com               LLM       bill_due                   Airtel ₹1,178.82 due 20 Jun            [open]
  01 Jun sms   AIRTEL                   LLM       bill_due                   Airtel ₹1,178.82 due 20 Jun            [duplicate]
  02 Jun pdf   pdf                      LLM       insurance_renewal          ICICI LOMBARD ₹15,342.00 due 20 Sep    [open]
  05 Jun email spotify.com              LLM       subscription_receipt       Spotify ₹119.00 due 05 Jul             [open]
  05 Jun email bsesdelhi.com            LLM       bill_due                   BSES Rajdhani ₹3,559.00 due 20 Jun     [open]
  08 Jun email spotify.com              LLM       subscription_price_change  Spotify ₹139.00 due 05 Jul             [price_change]
      ↳ rule fired: subscription_price_increase
      💬 chat alert to you: Spotify is raising your price from ₹119 to ₹139 on 05 Jul 2026. Reply KEEP or CANCEL-HELP.
  10 Jun email licindia.in              LLM       premium_due                LIC ₹4,215.00 due 28 Jun               [open]
  11 Jun email secure-payments-update.c RULE      ignore                                                            [ignored]
  12 Jun email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹27,884.72 due 02 Jul        [open]
  12 Jun sms   HDFCBK                   LLM       bill_due                   HDFC Bank ₹27,884.72 due 02 Jul        [duplicate]
  12 Jun email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 17 Jun              [open]
  14 Jun sms   AIRTEL                   LLM       ignore                                                            [ignored]
  18 Jun email account.netflix.com      LLM       subscription_receipt       Netflix ₹499.00 due 18 Jul             [open]
  20 Jun email icicilombard.com         LLM       insurance_renewal          ICICI Lombard ₹14,860.00 due 20 Sep    [flagged]
  [compiler] airtel_com_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 999 tokens)
  [approval] auto-approved for demo: airtel_com_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] sms_airtel_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 900 tokens)
  [approval] auto-approved for demo: sms_airtel_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] spotify_com_subscription_receipt v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1013 tokens)
  [approval] auto-approved for demo: spotify_com_subscription_receipt v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] bsesdelhi_com_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1173 tokens)
  [approval] auto-approved for demo: bsesdelhi_com_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] licindia_in_premium_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1043 tokens)
  [approval] auto-approved for demo: licindia_in_premium_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] apolloclinic_com_meeting v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 3475 tokens)
  [approval] auto-approved for demo: apolloclinic_com_meeting v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] hdfcbank_net_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1117 tokens)
  [approval] auto-approved for demo: hdfcbank_net_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] sms_hdfcbk_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 900 tokens)
  [approval] auto-approved for demo: sms_hdfcbk_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] account_netflix_com_subscription_receipt v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1026 tokens)
  [approval] auto-approved for demo: account_netflix_com_subscription_receipt v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [ml] retrained the local classifier on 35 LLM-labelled messages (9 sender rules)
  -- 14 messages, 1 handled by local code, 22 LLM calls, privacy score 7%

=== Month 4 · July 2026 ===
  01 Jul email airtel.com               LLM       bill_due                   Airtel ₹1,414.82 due 20 Jul            [open]
      ↳ ability:airtel_com_bill_due@v1 shadow match 1/1 -> active
  01 Jul sms   AIRTEL                   LLM       bill_due                   Airtel ₹1,414.82 due 20 Jul            [duplicate]
      ↳ ability:sms_airtel_bill_due@v1 shadow match 1/1 -> active
  05 Jul email spotify.com              LLM       subscription_receipt       Spotify ₹139.00 due 05 Aug             [open]
      ↳ ability:spotify_com_subscription_receipt@v1 shadow match 1/1 -> active
  05 Jul email bsesdelhi.com            LLM       bill_due                   BSES Rajdhani ₹1,596.00 due 20 Jul     [open]
      ↳ ability:bsesdelhi_com_bill_due@v1 shadow match 1/1 -> active
  09 Jul sms   SBIINB                   -                                                                           [OTP dropped before storage]
  10 Jul email licindia.in              LLM       premium_due                LIC ₹4,215.00 due 28 Jul               [open]
      ↳ ability:licindia_in_premium_due@v1 shadow match 1/1 -> active
  10 Jul email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 15 Jul              [open]
      ↳ ability:apolloclinic_com_meeting@v1 shadow match 1/1 -> active
  12 Jul email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹32,088.85 due 01 Aug        [open]
      ↳ ability:hdfcbank_net_bill_due@v1 shadow match 1/1 -> active
  12 Jul sms   HDFCBK                   LLM       bill_due                   HDFC Bank ₹32,088.85 due 01 Aug        [duplicate]
      ↳ ability:sms_hdfcbk_bill_due@v1 shadow match 1/1 -> active
  18 Jul email account.netflix.com      LLM       subscription_receipt       Netflix ₹499.00 due 18 Aug             [open]
      ↳ ability:account_netflix_com_subscription_receipt@v1 shadow match 1/1 -> active
  20 Jul email account.netflix.com      LLM       subscription_price_change  Netflix ₹649.00 due 18 Aug             [price_change]
      ↳ rule fired: subscription_price_increase
      💬 chat alert to you: Netflix is raising your price from ₹499 to ₹649 on 18 Aug 2026. Reply KEEP or CANCEL-HELP.
  21 Jul email icicilombard.com         LLM       insurance_renewal          ICICI Lombard ₹14,860.00 due 20 Sep    [duplicate]
  31 Jul email amazon.in                LLM       ignore                                                            [ignored]
      ↳ local classifier unsure (ignore 0.49 < 0.7) -> LLM
  [ml] retrained the local classifier on 47 LLM-labelled messages (10 sender rules)
  -- 12 messages, 0 handled by local code, 12 LLM calls, privacy score 0%

=== Month 5 · August 2026 ===
  01 Aug email airtel.com               LOCAL v1  bill_due                   Airtel Xstream Fiber ₹1,178.82 due 20 Aug [open]
      ↳ local code
  01 Aug sms   AIRTEL                   LOCAL v1  bill_due                   Airtel ₹1,178.82 due 20 Aug            [duplicate]
      ↳ local code
  03 Aug email hdfcbank.net             LLM       ignore                                                            [ignored]
  05 Aug email spotify.com              LOCAL v1  subscription_receipt       Spotify ₹139.00 due 05 Sep             [open]
      ↳ local code
  05 Aug email bsesdelhi.com            LOCAL v1  bill_due                   BSES Rajdhani ₹965.50 due 20 Aug       [open]
      ↳ local code
  10 Aug email licindia.in              LOCAL v1  premium_due                LIC ₹4,215.00 due 28 Aug               [open]
      ↳ local code
  11 Aug email apolloclinic.com         LOCAL v1  meeting                    Apollo Clinic  due 16 Aug              [open]
      ↳ local code
  12 Aug email hdfcbank.net             LOCAL v1  bill_due                   HDFC Bank ₹19,391.89 due 01 Sep        [open]
      ↳ local code
  12 Aug sms   HDFCBK                   LOCAL v1  bill_due                   HDFC Bank ₹19,391.89 due 01 Sep        [duplicate]
      ↳ local code
  18 Aug email account.netflix.com      LOCAL v1  subscription_receipt       Netflix ₹649.00 due 18 Sep             [open]
      ↳ local code
  21 Aug email icicilombard.com         LLM       insurance_renewal          ICICI Lombard ₹14,860.00 due 20 Sep    [duplicate]
  25 Aug sms   ICICIP                   LLM       ignore                                                            [ignored]
  [compiler] icicilombard_com_insurance_renewal v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1087 tokens)
  [approval] auto-approved for demo: icicilombard_com_insurance_renewal v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [ml] retrained the local classifier on 50 LLM-labelled messages (10 sender rules)
  -- 12 messages, 9 handled by local code, 4 LLM calls, privacy score 75%

=== Month 6 · September 2026 ===
  01 Sep email airtel.com               LOCAL v1  bill_due                   Airtel Xstream Fiber ₹1,178.82 due 20 Sep [open]
      ↳ local code
  01 Sep sms   AIRTEL                   LOCAL v1  bill_due                   Airtel ₹1,178.82 due 20 Sep            [duplicate]
      ↳ local code
  01 Sep sms   AIRTEL                   -                                                                           [OTP dropped before storage]
  02 Sep email youtube.com              LLM       subscription_price_change  YouTube ₹149.00 due 01 Oct             [price_change]
      ↳ rule fired: subscription_price_increase
      💬 chat alert to you: YouTube is raising your price from ₹129 to ₹149 on 01 Oct 2026. Reply KEEP or CANCEL-HELP.
  05 Sep email spotify.com              LOCAL v1  subscription_receipt       Spotify ₹139.00 due 05 Oct             [open]
      ↳ local code
  05 Sep email bsesdelhi.com            LOCAL v1  bill_due                   BSES Rajdhani ₹1,758.50 due 20 Sep     [open]
      ↳ local code
  07 Sep pdf   pdf                      LLM       bill_due                   BSES Rajdhani ₹1,758.50 due 20 Sep     [duplicate]
  10 Sep email licindia.in              LOCAL v1  premium_due                LIC ₹4,215.00 due 28 Sep               [open]
      ↳ local code
  12 Sep email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹13,903.23 due 02 Oct        [open]
      ↳ ability:hdfcbank_net_bill_due@v1 failed (ValueError: Missing Payment Due Date) -> degraded, LLM fallback
  12 Sep sms   HDFCBK                   LOCAL v1  bill_due                   HDFC Bank ₹13,903.23 due 02 Oct        [duplicate]
      ↳ local code
  12 Sep email apolloclinic.com         LOCAL v1  meeting                    Apollo Clinic  due 17 Sep              [open]
      ↳ local code
  13 Sep email icicilombard.com         LLM       insurance_renewal          ICICI Lombard ₹14,860.00 due 20 Sep    [duplicate]
      ↳ ability:icicilombard_com_insurance_renewal@v1 shadow match 1/1 -> active
  18 Sep email account.netflix.com      LOCAL v1  subscription_receipt       Netflix ₹649.00 due 18 Oct             [open]
      ↳ local code
  [compiler] hdfcbank_net_bill_due v2: tested (3 visible + 2 held-out cases, held-out pass 100%, 1727 tokens)
  [approval] auto-approved for demo: hdfcbank_net_bill_due v2 -> shadow (in real use: Telegram /approve or `brain approve`)
  [ml] retrained the local classifier on 54 LLM-labelled messages (10 sender rules)
  -- 12 messages, 8 handled by local code, 5 LLM calls, privacy score 67%
```

## Abilities

| ability | version | status | runs | failures | last error |
|---|---|---|---|---|---|
| account_netflix_com_subscription_receipt | v1 | active | 3 | 0 |  |
| airtel_com_bill_due | v1 | active | 3 | 0 |  |
| apolloclinic_com_meeting | v1 | active | 3 | 0 |  |
| bsesdelhi_com_bill_due | v1 | active | 3 | 0 |  |
| hdfcbank_net_bill_due | v1 | degraded | 3 | 1 | ValueError: Missing Payment Due Date |
| hdfcbank_net_bill_due | v2 | shadow | 0 | 0 |  |
| icicilombard_com_insurance_renewal | v1 | active | 1 | 0 |  |
| licindia_in_premium_due | v1 | active | 3 | 0 |  |
| sms_airtel_bill_due | v1 | active | 3 | 0 |  |
| sms_hdfcbk_bill_due | v1 | active | 3 | 0 |  |
| spotify_com_subscription_receipt | v1 | active | 3 | 0 |  |

Generated code and its tests: `abilities/<name>/v<n>/` (run them with `uv run pytest abilities`).

## Reminders scheduled (fire with no LLM)

- 03 Jul 2026 09:00 — Spotify price rises to ₹139 on 05 Jul 2026. Keep it or cancel before then.
- 16 Aug 2026 09:00 — Netflix price rises to ₹649 on 18 Aug 2026. Keep it or cancel before then.
- 29 Sep 2026 09:00 — YouTube price rises to ₹149 on 01 Oct 2026. Keep it or cancel before then.

## TinyFish (web)

Agent API run (replayed from tests/fixtures/tinyfish/) on https://help.netflix.com/en/node/24926: `{'provider': 'Netflix', 'plan': 'Standard', 'price': 19.99, 'currency': 'USD'}`, stored as a `portal` trace so the task can graduate like any other. (TinyFish proxies have no India exit, so the public page shows US pricing.)

## Privacy score and cost per simulated month

| month | messages | local code | LLM calls | tokens | privacy score | cost / message (USD) |
|---|---|---|---|---|---|---|
| 2026-04 | 10 | 0 | 10 | 9962 | 0% | 0.00045 |
| 2026-05 | 12 | 0 | 12 | 12999 | 0% | 0.00050 |
| 2026-06 | 14 | 1 | 22 | 24552 | 7% | 0.00576 |
| 2026-07 | 12 | 0 | 12 | 11662 | 0% | 0.00044 |
| 2026-08 | 12 | 9 | 4 | 3806 | 75% | 0.00068 |
| 2026-09 | 12 | 8 | 5 | 5867 | 67% | 0.00129 |

## Extraction accuracy (`make eval`)

Labelled samples: 76 (`data/eval/labels.jsonl`)

| handler | type | provider | amount | due_date |
|---|---|---|---|---|
| all | 100.0% (72/72) | 100.0% (64/64) | 100.0% (64/64) | 100.0% (64/64) |
| llm | 100.0% (54/54) | 100.0% (47/47) | 100.0% (47/47) | 100.0% (47/47) |
| compiled | 100.0% (17/17) | 100.0% (17/17) | 100.0% (17/17) | 100.0% (17/17) |
| rule | 100.0% (1/1) | - | - | - |
| ability:account_netflix_com_subscription_receipt@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:airtel_com_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:apolloclinic_com_meeting@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:bsesdelhi_com_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:hdfcbank_net_bill_due@v1 | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) |
| ability:licindia_in_premium_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:sms_airtel_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:sms_hdfcbk_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:spotify_com_subscription_receipt@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| rule:injection_guard | 100.0% (1/1) | - | - | - |


## Chat (answers from state only, today = 30 Sep 2026)

> What do I need to pay in the first half of October?

Pay HDFC Bank bill ₹13,903.23 on 2 Oct (id 42) and Spotify subscription ₹139 on 5 Oct (id 39).

LLM calls this run: 0 live, 67 replayed from `data/llm_cache/`.
