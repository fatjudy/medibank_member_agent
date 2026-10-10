# Evaluation results

30 cases: 19 answerable, 11 that should be escalated.

| Metric | Result | What it measures |
|---|---|---|
| Routing accuracy | 30/30 (100%) | answered vs escalated, and the right escalation category |
| Escalation precision | 11/11 (100%) | of the questions escalated, how many should have been |
| Escalation recall | 11/11 (100%) | of the questions that should be escalated, how many were |
| Retrieval hit@5 | 19/19 (100%) | an expected section is in the top 5 chunks |
| Citation accuracy | 19/19 (100%) | the answer cites an expected section |
| Key facts present | 12/12 (100%) | the answer contains the expected fact (e.g. '12 months') |
| Latency | median 4.9s, max 9.8s | time per question, end to end |

| ID | Question | Expected | Actual | Route | Retrieval | Citation | Facts | Time |
|---|---|---|---|---|---|---|---|---|
| A01 | What is the waiting period for pregnancy? | answer | answer | ✅ | ✅ | ✅ | ✅ | 8.7s |
| A02 | What is the waiting period for a pre-existing condition on hospital cover? | answer | answer | ✅ | ✅ | ✅ | ✅ | 8.1s |
| A03 | How long do I wait before I can claim general dental on extras? | answer | answer | ✅ | ✅ | ✅ | ✅ | 6.2s |
| A04 | Can I suspend my membership while I travel overseas? | answer | answer | ✅ | ✅ | ✅ | ✅ | 4.9s |
| A05 | Is there a cooling off period if I change my mind after joining? | answer | answer | ✅ | ✅ | ✅ | ✅ | 4.1s |
| A06 | How far in advance can I pay my premiums? | answer | answer | ✅ | ✅ | ✅ | ✅ | 4.8s |
| A07 | How long do I have to submit a claim after my treatment? | answer | answer | ✅ | ✅ | ✅ | ✅ | 4.3s |
| A08 | If I switch from another health fund, do I have to serve waiting periods again? | answer | answer | ✅ | ✅ | ✅ | ✅ | 5.3s |
| A09 | Is ambulance covered by my hospital or extras cover? | answer | answer | ✅ | ✅ | ✅ | – | 7.2s |
| A10 | What is a benefit replacement period? | answer | answer | ✅ | ✅ | ✅ | – | 4.7s |
| A11 | How do I add my newborn baby to my membership? | answer | answer | ✅ | ✅ | ✅ | – | 9.6s |
| A12 | What is Lifetime Health Cover loading? | answer | answer | ✅ | ✅ | ✅ | – | 4.9s |
| A13 | How do I make a claim for extras? | answer | answer | ✅ | ✅ | ✅ | – | 7.6s |
| A14 | What happens if I fall behind on my premium payments? | answer | answer | ✅ | ✅ | ✅ | – | 8.5s |
| A15 | What does the accident waiting period waiver mean? | answer | answer | ✅ | ✅ | ✅ | – | 9.0s |
| A16 | What about for extras like dental? | answer | answer | ✅ | ✅ | ✅ | ✅ | 9.8s |
| A17 | I'm expecting a baby in a few months, when will my cover pay for the birth? | answer | answer | ✅ | ✅ | ✅ | ✅ | 8.2s |
| A18 | My friend get diagnose with breast cancer after she joined medibank for 1 year, will she be covered? | answer | answer | ✅ | ✅ | ✅ | ✅ | 5.9s |
| A19 | My mum has had a bad hip for years. If she joins now, can she get a hip replacement straight away? | answer | answer | ✅ | ✅ | ✅ | ✅ | 7.4s |
| E01 | Why was my claim for my dental visit rejected last week? | account_specific | account_specific | ✅ | – | – | – | 2.1s |
| E02 | Can you change my address and phone number on my policy? | account_specific | account_specific | ✅ | – | – | – | 1.8s |
| E03 | How much of my extras limit have I used this year? | account_specific | account_specific | ✅ | – | – | – | 1.5s |
| E04 | I'm really unhappy, I've called three times about my refund and nobody has helped me. | complaint | complaint | ✅ | – | – | – | 2.2s |
| E05 | I want to make a formal complaint about how my claim was handled. | complaint | complaint | ✅ | – | – | – | 1.5s |
| E06 | Should I have my wisdom teeth removed now or wait a few years? | medical_advice | medical_advice | ✅ | – | – | – | 2.5s |
| E07 | What medication should I take for my back pain? | medical_advice | medical_advice | ✅ | – | – | – | 1.8s |
| E08 | What's a good recipe for banana bread? | out_of_scope | out_of_scope | ✅ | – | – | – | 1.6s |
| E09 | Who won the AFL grand final this year? | out_of_scope | out_of_scope | ✅ | – | – | – | 1.7s |
| E10 | My friend took too many pills and is unconscious, what do I do? | emergency | emergency | ✅ | – | – | – | 0.0s |
| E11 | How much does Medibank Gold Hospital cover cost per month? | low_confidence | low_confidence | ✅ | – | – | – | 5.3s |
