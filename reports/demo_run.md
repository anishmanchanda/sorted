# Sorted demo run (synthetic simulation)

`make demo` replays 6 simulated months of synthetic bills in seconds to show how the share of local code grows; no real user data or history. Dates are generated so the simulated timeline ends on the run date (23 Oct 2026); the simulation lives in `data/demo.db`, separate from the live bot's database.

LLM routes: small=cerebras/gpt-oss-120b, strong=openai/gpt-5.4. Compile after 3 accepted traces; shadow runs = 1 (demo setting; default 2). Costs are estimates from BRAIN_PRICES.

```text
Generated 81 synthetic messages (emails, SMS, PDFs) for Sim months 1-6.

=== Sim month 1 of 6 (synthetic) ===
  24 Apr email airtel.com               LLM       bill_due                   Airtel ₹1,178.82 due 13 May            [open]
  24 Apr sms   AIRTEL                   LLM       bill_due                   Airtel ₹1,178.82 due 13 May            [duplicate]
  26 Apr sms   HDFCBK                   -                                                                           [OTP dropped before storage]
  28 Apr email spotify.com              LLM       subscription_receipt       Spotify ₹119.00 due 28 May             [open]
  28 Apr email bsesdelhi.com            LLM       bill_due                   BSES Rajdhani ₹959.00 due 13 May       [open]
  02 May email myntra.com               LLM       ignore                                                            [ignored]
  03 May email licindia.in              LLM       premium_due                LIC ₹4,215.00 due 21 May               [open]
  03 May email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 08 May              [open]
  05 May email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹25,264.52 due 25 May        [open]
  05 May sms   HDFCBK                   LLM       bill_due                   HDFC Bank ₹25,264.52 due 25 May        [duplicate]
  11 May email account.netflix.com      LLM       subscription_receipt       Netflix ₹499.00 due 10 Jun             [open]
  ⏰ 07 May 09:00 reminder fired by the scheduler (no LLM): Apollo Clinic appointment on 08 May.
  ⏰ 10 May 09:00 reminder fired by the scheduler (no LLM): Airtel bill ₹1,178.82 is due on 13 May. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 10 May 09:00 reminder fired by the scheduler (no LLM): BSES Rajdhani bill ₹959.00 is due on 13 May. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 18 May 09:00 reminder fired by the scheduler (no LLM): LIC premium ₹4,215.00 is due on 21 May. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 22 May 09:00 reminder fired by the scheduler (no LLM): HDFC Bank bill ₹25,264.52 is due on 25 May. Reply 'paid' when done, or 'snooze 1h'.
  [ml] retrained the local classifier on 10 LLM-labelled messages (0 sender rules)
  -- 10 messages, 0 handled by local code, 10 LLM calls, privacy score 0%

=== Sim month 2 of 6 (synthetic) ===
  24 May email airtel.com               LLM       bill_due                   Airtel Xstream Fiber ₹1,178.82 due 12 Jun [open]
  24 May sms   AIRTEL                   LLM       bill_due                   Airtel ₹1,178.82 due 12 Jun            [duplicate]
  25 May sms   JIOMRT                   LLM       ignore                                                            [ignored]
  28 May email spotify.com              LLM       subscription_receipt       Spotify ₹119.00 due 28 Jun             [open]
  28 May email bsesdelhi.com            LLM       bill_due                   BSES Rajdhani ₹2,051.00 due 12 Jun     [open]
  02 Jun email licindia.in              LLM       premium_due                LIC ₹4,215.00 due 20 Jun               [open]
  03 Jun email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 08 Jun              [open]
  03 Jun pdf   pdf                      LLM       document_expiry            Transport Department ₹100.00 due 03 Dec [document]
  04 Jun email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹15,425.79 due 24 Jun        [open]
  04 Jun sms   HDFCBK                   LLM       bill_due                   HDFC Bank ₹15,425.79 due 24 Jun        [duplicate]
  09 Jun sms   AMAZON                   -                                                                           [OTP dropped before storage]
  10 Jun email account.netflix.com      LLM       subscription_receipt       Netflix ₹499.00 due 11 Jul             [open]
  14 Jun email swiggy.in                LLM       ignore                                                            [ignored]
  ⏰ 07 Jun 09:00 reminder fired by the scheduler (no LLM): Apollo Clinic appointment on 08 Jun.
  ⏰ 09 Jun 09:00 reminder fired by the scheduler (no LLM): Airtel Xstream Fiber bill ₹1,178.82 is due on 12 Jun. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 09 Jun 09:00 reminder fired by the scheduler (no LLM): BSES Rajdhani bill ₹2,051.00 is due on 12 Jun. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 17 Jun 09:00 reminder fired by the scheduler (no LLM): LIC premium ₹4,215.00 is due on 20 Jun. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 21 Jun 09:00 reminder fired by the scheduler (no LLM): HDFC Bank bill ₹15,425.79 is due on 24 Jun. Reply 'paid' when done, or 'snooze 1h'.
  [ml] retrained the local classifier on 22 LLM-labelled messages (9 sender rules)
  -- 12 messages, 0 handled by local code, 12 LLM calls, privacy score 0%

=== Sim month 3 of 6 (synthetic) ===
  24 Jun email airtel.com               LLM       bill_due                   Airtel Xstream Fiber ₹1,178.82 due 13 Jul [open]
  24 Jun sms   AIRTEL                   LLM       bill_due                   Airtel ₹1,178.82 due 13 Jul            [duplicate]
  25 Jun pdf   pdf                      LLM       insurance_renewal          ICICI LOMBARD ₹15,342.00 due 12 Nov    [open]
  28 Jun email spotify.com              LLM       subscription_receipt       Spotify ₹119.00 due 28 Jul             [open]
  28 Jun email bsesdelhi.com            LLM       bill_due                   BSES Rajdhani ₹3,559.00 due 13 Jul     [open]
  01 Jul email spotify.com              LLM       subscription_price_change  Spotify ₹139.00 due 28 Jul             [price_change]
      ↳ rule fired: subscription_price_increase
      💬 chat alert to you: Spotify is raising your price from ₹119 to ₹139 on 28 Jul 2026. Reply KEEP or CANCEL-HELP.
  03 Jul email licindia.in              LLM       premium_due                LIC ₹4,215.00 due 21 Jul               [open]
  04 Jul email secure-payments-update.c RULE      ignore                                                            [ignored]
  05 Jul email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹27,884.72 due 25 Jul        [open]
  05 Jul sms   HDFCBK                   LLM       bill_due                   HDFC Bank ₹27,884.72 due 25 Jul        [duplicate]
  05 Jul email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 10 Jul              [open]
  07 Jul sms   AIRTEL                   LLM       ignore                                                            [ignored]
  11 Jul email account.netflix.com      LLM       subscription_receipt       Netflix ₹499.00 due 10 Aug             [open]
  11 Jul email sharmaassociates.in      LLM       meeting_request            Sharma Associates  due 19 Jul          [proposed]
      💬 chat alert to you: 📅 Meeting request from Ankit Verma (Sharma Associates)
About: flat lease renewal
They proposed: Sun 19 Jul, 4:00 PM

Do you want to meet? Pick a time:
[✅ Sun 19 Jul, 4:00 PM]  [🕐 Another time]  [❌ Decline]
  13 Jul email icicilombard.com         LLM       insurance_renewal          ICICI Lombard ₹14,860.00 due 12 Nov    [flagged]
  ⏰ 09 Jul 09:00 reminder fired by the scheduler (no LLM): Apollo Clinic appointment on 10 Jul.
  ⏰ 10 Jul 09:00 reminder fired by the scheduler (no LLM): Airtel Xstream Fiber bill ₹1,178.82 is due on 13 Jul. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 10 Jul 09:00 reminder fired by the scheduler (no LLM): BSES Rajdhani bill ₹3,559.00 is due on 13 Jul. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 18 Jul 09:00 reminder fired by the scheduler (no LLM): LIC premium ₹4,215.00 is due on 21 Jul. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 22 Jul 09:00 reminder fired by the scheduler (no LLM): HDFC Bank bill ₹27,884.72 is due on 25 Jul. Reply 'paid' when done, or 'snooze 1h'.
  [compiler] airtel_com_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1065 tokens)
  [approval] auto-approved for demo: airtel_com_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] sms_airtel_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 882 tokens)
  [approval] auto-approved for demo: sms_airtel_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] spotify_com_subscription_receipt v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1011 tokens)
  [approval] auto-approved for demo: spotify_com_subscription_receipt v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] bsesdelhi_com_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1157 tokens)
  [approval] auto-approved for demo: bsesdelhi_com_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] licindia_in_premium_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1093 tokens)
  [approval] auto-approved for demo: licindia_in_premium_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] apolloclinic_com_meeting v1: candidate (2 visible + 1 held-out cases, held-out pass 0%, 3552 tokens) — example 1: expected {"type": "meeting", "provider": "Apollo Clinic", "currency": "INR", "due_date": "2026-06-08", "event_time": "10:30", "person": "Sunita Sharm
  [compiler] hdfcbank_net_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1103 tokens)
  [approval] auto-approved for demo: hdfcbank_net_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] sms_hdfcbk_bill_due v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 912 tokens)
  [approval] auto-approved for demo: sms_hdfcbk_bill_due v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] account_netflix_com_subscription_receipt v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 951 tokens)
  [approval] auto-approved for demo: account_netflix_com_subscription_receipt v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [ml] retrained the local classifier on 36 LLM-labelled messages (9 sender rules)
  -- 15 messages, 1 handled by local code, 23 LLM calls, privacy score 7%

=== Sim month 4 of 6 (synthetic) ===
  24 Jul email airtel.com               LLM       bill_due                   Airtel Xstream Fiber ₹1,414.82 due 12 Aug [open]
      ↳ ability:airtel_com_bill_due@v1 shadow match 1/1 -> active
  24 Jul sms   AIRTEL                   LLM       bill_due                   Airtel ₹1,414.82 due 12 Aug            [duplicate]
      ↳ ability:sms_airtel_bill_due@v1 shadow match 1/1 -> active
  28 Jul email spotify.com              LLM       subscription_receipt       Spotify ₹139.00 due 28 Aug             [open]
      ↳ ability:spotify_com_subscription_receipt@v1 shadow match 1/1 -> active
  28 Jul email bsesdelhi.com            LLM       bill_due                   BSES Rajdhani ₹1,596.00 due 12 Aug     [open]
      ↳ ability:bsesdelhi_com_bill_due@v1 shadow match 1/1 -> active
  01 Aug sms   SBIINB                   -                                                                           [OTP dropped before storage]
  02 Aug email licindia.in              LLM       premium_due                LIC ₹4,215.00 due 20 Aug               [open]
      ↳ ability:licindia_in_premium_due@v1 shadow match 1/1 -> active
  02 Aug email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 07 Aug              [open]
  04 Aug email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹32,088.85 due 24 Aug        [open]
      ↳ ability:hdfcbank_net_bill_due@v1 shadow match 1/1 -> active
  04 Aug sms   HDFCBK                   LLM       bill_due                   HDFC Bank ₹32,088.85 due 24 Aug        [duplicate]
      ↳ ability:sms_hdfcbk_bill_due@v1 shadow match 1/1 -> active
  10 Aug email account.netflix.com      LLM       subscription_receipt       Netflix ₹499.00 due 10 Sep             [open]
      ↳ ability:account_netflix_com_subscription_receipt@v1 shadow match 1/1 -> active
  12 Aug email account.netflix.com      LLM       subscription_price_change  Netflix ₹649.00 due 10 Sep             [price_change]
      ↳ rule fired: subscription_price_increase
      💬 chat alert to you: Netflix is raising your price from ₹499 to ₹649 on 10 Sep 2026. Reply KEEP or CANCEL-HELP.
  13 Aug email icicilombard.com         LLM       insurance_renewal          ICICI Lombard ₹14,860.00 due 12 Nov    [duplicate]
  23 Aug email amazon.in                LLM       ignore                                                            [ignored]
      ↳ local classifier unsure (ignore 0.45 < 0.7) -> LLM
  ⏰ 26 Jul 09:00 reminder fired by the scheduler (no LLM): Spotify price rises to ₹139 on 28 Jul 2026. Keep it or cancel before then.
  ⏰ 06 Aug 09:00 reminder fired by the scheduler (no LLM): Apollo Clinic appointment on 07 Aug.
  ⏰ 09 Aug 09:00 reminder fired by the scheduler (no LLM): Airtel Xstream Fiber bill ₹1,414.82 is due on 12 Aug. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 09 Aug 09:00 reminder fired by the scheduler (no LLM): BSES Rajdhani bill ₹1,596.00 is due on 12 Aug. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 17 Aug 09:00 reminder fired by the scheduler (no LLM): LIC premium ₹4,215.00 is due on 20 Aug. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 21 Aug 09:00 reminder fired by the scheduler (no LLM): HDFC Bank bill ₹32,088.85 is due on 24 Aug. Reply 'paid' when done, or 'snooze 1h'.
  [compiler] apolloclinic_com_meeting v1: candidate (3 visible + 1 held-out cases, held-out pass 0%, 4206 tokens) — example 1: expected {"type": "meeting", "provider": "Apollo Clinic", "currency": "INR", "due_date": "2026-05-08", "event_time": "10:30", "person": "Sunita Sharm
  [ml] retrained the local classifier on 48 LLM-labelled messages (10 sender rules)
  -- 12 messages, 0 handled by local code, 13 LLM calls, privacy score 0%

=== Sim month 5 of 6 (synthetic) ===
  24 Aug email airtel.com               LOCAL v1  bill_due                   Airtel Xstream Fiber ₹1,178.82 due 12 Sep [open]
      ↳ local code
  24 Aug sms   AIRTEL                   LOCAL v1  bill_due                   Airtel ₹1,178.82 due 12 Sep            [duplicate]
      ↳ local code
  24 Aug email dpsrkpuram.edu.in        LLM       meeting_request            Delhi Public School  due 31 Aug        [proposed]
      💬 chat alert to you: 📅 Meeting request from Mrs. Kavita Rao (Delhi Public School)
About: mid-term progress
They proposed: Mon 31 Aug, 10:00 AM

Do you want to meet? Pick a time:
[✅ Mon 31 Aug, 10:00 AM]  [🕐 Another time]  [❌ Decline]
  26 Aug email hdfcbank.net             LLM       ignore                                                            [ignored]
  28 Aug email spotify.com              LOCAL v1  subscription_receipt       Spotify ₹139.00 due 28 Sep             [open]
      ↳ local code
  28 Aug email bsesdelhi.com            LOCAL v1  bill_due                   BSES Rajdhani ₹965.50 due 12 Sep       [open]
      ↳ local code
  02 Sep email licindia.in              LOCAL v1  premium_due                LIC ₹4,215.00 due 20 Sep               [open]
      ↳ local code
  03 Sep email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 08 Sep              [open]
  04 Sep email hdfcbank.net             LOCAL v1  bill_due                   HDFC Bank ₹19,391.89 due 24 Sep        [open]
      ↳ local code
  04 Sep sms   HDFCBK                   LOCAL v1  bill_due                   HDFC Bank ₹19,391.89 due 24 Sep        [duplicate]
      ↳ local code
  10 Sep email account.netflix.com      LOCAL v1  subscription_receipt       Netflix ₹649.00 due 11 Oct             [open]
      ↳ local code
  13 Sep email icicilombard.com         LLM       insurance_renewal          ICICI Lombard ₹14,860.00 due 12 Nov    [duplicate]
  17 Sep sms   ICICIP                   LLM       ignore                                                            [ignored]
      ↳ local classifier unsure (ignore 0.33 < 0.7) -> LLM
  ⏰ 07 Sep 09:00 reminder fired by the scheduler (no LLM): Apollo Clinic appointment on 08 Sep.
  ⏰ 08 Sep 09:00 reminder fired by the scheduler (no LLM): Netflix price rises to ₹649 on 10 Sep 2026. Keep it or cancel before then.
  ⏰ 09 Sep 09:00 reminder fired by the scheduler (no LLM): Airtel Xstream Fiber bill ₹1,178.82 is due on 12 Sep. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 09 Sep 09:00 reminder fired by the scheduler (no LLM): BSES Rajdhani bill ₹965.50 is due on 12 Sep. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 17 Sep 09:00 reminder fired by the scheduler (no LLM): LIC premium ₹4,215.00 is due on 20 Sep. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 21 Sep 09:00 reminder fired by the scheduler (no LLM): HDFC Bank bill ₹19,391.89 is due on 24 Sep. Reply 'paid' when done, or 'snooze 1h'.
  [compiler] apolloclinic_com_meeting v1: tested (3 visible + 2 held-out cases, held-out pass 100%, 4076 tokens)
  [approval] auto-approved for demo: apolloclinic_com_meeting v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [compiler] icicilombard_com_insurance_renewal v1: tested (2 visible + 1 held-out cases, held-out pass 100%, 1170 tokens)
  [approval] auto-approved for demo: icicilombard_com_insurance_renewal v1 -> shadow (in real use: Telegram /approve or `brain approve`)
  [ml] retrained the local classifier on 53 LLM-labelled messages (10 sender rules)
  -- 13 messages, 8 handled by local code, 7 LLM calls, privacy score 62%

=== Sim month 6 of 6 (synthetic) ===
  24 Sep email airtel.com               LOCAL v1  bill_due                   Airtel Xstream Fiber ₹1,178.82 due 13 Oct [open]
      ↳ local code
  24 Sep sms   AIRTEL                   LOCAL v1  bill_due                   Airtel ₹1,178.82 due 13 Oct            [duplicate]
      ↳ local code
  24 Sep sms   AIRTEL                   -                                                                           [OTP dropped before storage]
  25 Sep email youtube.com              LLM       subscription_price_change  YouTube ₹149.00 due 04 Nov             [price_change]
      ↳ rule fired: subscription_price_increase
      💬 chat alert to you: YouTube is raising your price from ₹129 to ₹149 on 04 Nov 2026. Reply KEEP or CANCEL-HELP.
  26 Sep email guptaca.in               LLM       meeting_request            Gupta & Co. Chartered Accountants  due 02 Oct [proposed]
      💬 chat alert to you: 📅 Meeting request from Neha Gupta (Gupta & Co. Chartered Accountants)
About: second advance tax instalment and capital gains discussion
They proposed: Fri 2 Oct, 6:30 PM

Do you want to meet? Pick a time:
[✅ Fri 2 Oct, 6:30 PM]  [🕐 Another time]  [❌ Decline]
  28 Sep email spotify.com              LOCAL v1  subscription_receipt       Spotify ₹139.00 due 28 Oct             [open]
      ↳ local code
  28 Sep email bsesdelhi.com            LOCAL v1  bill_due                   BSES Rajdhani ₹1,758.50 due 13 Oct     [open]
      ↳ local code
  30 Sep pdf   pdf                      LLM       bill_due                   BSES Rajdhani ₹1,758.50 due 13 Oct     [duplicate]
  03 Oct email licindia.in              LOCAL v1  premium_due                LIC ₹4,215.00 due 21 Oct               [open]
      ↳ local code
  05 Oct email hdfcbank.net             LLM       bill_due                   HDFC Bank ₹13,903.23 due 25 Oct        [open]
      ↳ ability:hdfcbank_net_bill_due@v1 failed (ValueError: Missing Total Amount Due label) -> degraded, LLM fallback
  05 Oct sms   HDFCBK                   LOCAL v1  bill_due                   HDFC Bank ₹13,903.23 due 25 Oct        [duplicate]
      ↳ local code
  05 Oct email apolloclinic.com         LLM       meeting                    Apollo Clinic  due 10 Oct              [open]
      ↳ ability:apolloclinic_com_meeting@v1 shadow match 1/1 -> active
  06 Oct email icicilombard.com         LLM       insurance_renewal          ICICI Lombard ₹14,860.00 due 12 Nov    [duplicate]
      ↳ ability:icicilombard_com_insurance_renewal@v1 shadow match 1/1 -> active
  11 Oct email account.netflix.com      LOCAL v1  subscription_receipt       Netflix ₹649.00 due 10 Nov             [open]
      ↳ local code
  18 Oct email acmeinfra.in             LLM       meeting_request            Acme Infra  due 29 Oct                 [proposed]
      💬 chat alert to you: 📅 Meeting request from Ravi Kumar (Acme Infra)
About: kitchen renovation site visit
They proposed: Thu 29 Oct, 11:00 AM

Do you want to meet? Pick a time:
[✅ Thu 29 Oct, 11:00 AM]  [🕐 Another time]  [❌ Decline]
  19 Oct email clovedental.in           LLM       meeting                    Clove Dental  due 26 Oct               [open]
  ⏰ 09 Oct 09:00 reminder fired by the scheduler (no LLM): Apollo Clinic appointment on 10 Oct.
  ⏰ 10 Oct 09:00 reminder fired by the scheduler (no LLM): Airtel Xstream Fiber bill ₹1,178.82 is due on 13 Oct. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 10 Oct 09:00 reminder fired by the scheduler (no LLM): BSES Rajdhani bill ₹1,758.50 is due on 13 Oct. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 18 Oct 09:00 reminder fired by the scheduler (no LLM): LIC premium ₹4,215.00 is due on 21 Oct. Reply 'paid' when done, or 'snooze 1h'.
  ⏰ 22 Oct 09:00 reminder fired by the scheduler (no LLM): HDFC Bank bill ₹13,903.23 is due on 25 Oct. Reply 'paid' when done, or 'snooze 1h'.
  [compiler] hdfcbank_net_bill_due v2: tested (3 visible + 2 held-out cases, held-out pass 100%, 1606 tokens)
  [approval] auto-approved for demo: hdfcbank_net_bill_due v2 -> shadow (in real use: Telegram /approve or `brain approve`)
  [ml] retrained the local classifier on 61 LLM-labelled messages (10 sender rules)
  -- 15 messages, 7 handled by local code, 9 LLM calls, privacy score 47%
```

## Abilities

| ability | version | status | runs | failures | last error |
|---|---|---|---|---|---|
| account_netflix_com_subscription_receipt | v1 | active | 3 | 0 |  |
| airtel_com_bill_due | v1 | active | 3 | 0 |  |
| apolloclinic_com_meeting | v1 | active | 1 | 0 |  |
| bsesdelhi_com_bill_due | v1 | active | 3 | 0 |  |
| hdfcbank_net_bill_due | v1 | degraded | 3 | 1 | ValueError: Missing Total Amount Due label |
| hdfcbank_net_bill_due | v2 | shadow | 0 | 0 |  |
| icicilombard_com_insurance_renewal | v1 | active | 1 | 0 |  |
| licindia_in_premium_due | v1 | active | 3 | 0 |  |
| sms_airtel_bill_due | v1 | active | 3 | 0 |  |
| sms_hdfcbk_bill_due | v1 | active | 3 | 0 |  |
| spotify_com_subscription_receipt | v1 | active | 3 | 0 |  |

Generated code and its tests: `abilities/<name>/v<n>/` (run them with `uv run pytest abilities`).

## Reminders still scheduled after the simulation (all in the future; fire with no LLM)

- 25 Oct 2026 09:00 — Clove Dental appointment on 26 Oct.
- 02 Nov 2026 09:00 — YouTube price rises to ₹149 on 04 Nov 2026. Keep it or cancel before then.
- 05 Nov 2026 09:00 — ICICI LOMBARD renewal ₹15,342.00 is due on 12 Nov. Reply 'paid' when done, or 'snooze 1h'.

## TinyFish (web)

Agent API run (replayed from tests/fixtures/tinyfish/) on https://help.netflix.com/en/node/24926: `{'provider': 'Netflix', 'plan': 'Standard', 'price': 19.99, 'currency': 'USD'}`, stored as a `portal` trace so the task can graduate like any other. (TinyFish proxies have no India exit, so the public page shows US pricing.)

## Privacy score and cost per simulated month

| period | messages | local code | LLM calls | tokens | privacy score | cost / message (USD) |
|---|---|---|---|---|---|---|
| Sim month 1 | 10 | 0 | 10 | 14009 | 0% | 0.00063 |
| Sim month 2 | 12 | 0 | 12 | 16101 | 0% | 0.00060 |
| Sim month 3 | 15 | 1 | 23 | 28663 | 7% | 0.00556 |
| Sim month 4 | 12 | 0 | 13 | 20334 | 0% | 0.00249 |
| Sim month 5 | 13 | 8 | 7 | 12944 | 62% | 0.00252 |
| Sim month 6 | 15 | 7 | 9 | 13499 | 47% | 0.00115 |

## Extraction accuracy (`make eval`)

Labelled samples: 81 (`data/eval/labels.jsonl`)

| handler | type | provider | amount | due_date |
|---|---|---|---|---|
| all | 100.0% (77/77) | 100.0% (69/69) | 98.6% (68/69) | 100.0% (69/69) |
| llm | 100.0% (61/61) | 100.0% (54/54) | 98.1% (53/54) | 100.0% (54/54) |
| compiled | 100.0% (15/15) | 100.0% (15/15) | 100.0% (15/15) | 100.0% (15/15) |
| rule | 100.0% (1/1) | - | - | - |
| ability:account_netflix_com_subscription_receipt@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:airtel_com_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:bsesdelhi_com_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:hdfcbank_net_bill_due@v1 | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) |
| ability:licindia_in_premium_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:sms_airtel_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:sms_hdfcbk_bill_due@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| ability:spotify_com_subscription_receipt@v1 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| rule:injection_guard | 100.0% (1/1) | - | - | - |


## Chat (answers from the simulated state only)

> What do I need to pay in the next two weeks?

2 payments due in the next 2 weeks (₹14,042.23 in total):
• Sun 25 Oct · HDFC Bank bill ₹13,903.23
• Wed 28 Oct · Spotify subscription ₹139.00

LLM calls this run: 0 live, 78 replayed from `data/llm_cache/`.
