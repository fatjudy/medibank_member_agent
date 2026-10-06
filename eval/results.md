# Evaluation results

28 cases: 17 answerable, 11 that should be escalated.

| Metric | Result | What it measures |
|---|---|---|
| Routing accuracy | 28/28 (100%) | answered vs escalated, and the right escalation category |
| Escalation precision | 11/11 (100%) | of the questions escalated, how many should have been |
| Escalation recall | 11/11 (100%) | of the questions that should be escalated, how many were |
| Retrieval hit@5 | 17/17 (100%) | an expected section is in the top 5 chunks |
| Citation accuracy | 17/17 (100%) | the answer cites an expected section |
| Key facts present | 10/10 (100%) | the answer contains the expected fact (e.g. '12 months') |
| Latency | median 5.2s, max 10.1s | time per question, end to end |

| ID | Question | Expected | Actual | Route | Retrieval | Citation | Facts | Time |
|---|---|---|---|---|---|---|---|---|
| A01 | What is the waiting period for pregnancy? | answer | answer | ✅ | ✅ | ✅ | ✅ | 5.9s |
| A02 | What is the waiting period for a pre-existing condition on hospital cover? | answer | answer | ✅ | ✅ | ✅ | ✅ | 6.8s |
| A03 | How long do I wait before I can claim general dental on extras? | answer | answer | ✅ | ✅ | ✅ | ✅ | 4.7s |
| A04 | Can I suspend my membership while I travel overseas? | answer | answer | ✅ | ✅ | ✅ | ✅ | 9.0s |
| A05 | Is there a cooling off period if I change my mind after joining? | answer | answer | ✅ | ✅ | ✅ | ✅ | 5.2s |
| A06 | How far in advance can I pay my premiums? | answer | answer | ✅ | ✅ | ✅ | ✅ | 5.5s |
| A07 | How long do I have to submit a claim after my treatment? | answer | answer | ✅ | ✅ | ✅ | ✅ | 7.8s |
| A08 | If I switch from another health fund, do I have to serve waiting periods again? | answer | answer | ✅ | ✅ | ✅ | ✅ | 6.4s |
| A09 | Is ambulance covered by my hospital or extras cover? | answer | answer | ✅ | ✅ | ✅ | – | 5.7s |
| A10 | What is a benefit replacement period? | answer | answer | ✅ | ✅ | ✅ | – | 5.1s |
| A11 | How do I add my newborn baby to my membership? | answer | answer | ✅ | ✅ | ✅ | – | 10.1s |
| A12 | What is Lifetime Health Cover loading? | answer | answer | ✅ | ✅ | ✅ | – | 4.6s |
| A13 | How do I make a claim for extras? | answer | answer | ✅ | ✅ | ✅ | – | 5.7s |
| A14 | What happens if I fall behind on my premium payments? | answer | answer | ✅ | ✅ | ✅ | – | 5.6s |
| A15 | What does the accident waiting period waiver mean? | answer | answer | ✅ | ✅ | ✅ | – | 6.3s |
| A16 | What about for extras like dental? | answer | answer | ✅ | ✅ | ✅ | ✅ | 9.5s |
| A17 | I'm expecting a baby in a few months, when will my cover pay for the birth? | answer | answer | ✅ | ✅ | ✅ | ✅ | 4.8s |
| E01 | Why was my claim for my dental visit rejected last week? | account_specific | account_specific | ✅ | – | – | – | 1.5s |
| E02 | Can you change my address and phone number on my policy? | account_specific | account_specific | ✅ | – | – | – | 2.0s |
| E03 | How much of my extras limit have I used this year? | account_specific | account_specific | ✅ | – | – | – | 1.8s |
| E04 | I'm really unhappy, I've called three times about my refund and nobody has helped me. | complaint | complaint | ✅ | – | – | – | 4.8s |
| E05 | I want to make a formal complaint about how my claim was handled. | complaint | complaint | ✅ | – | – | – | 2.5s |
| E06 | Should I have my wisdom teeth removed now or wait a few years? | medical_advice | medical_advice | ✅ | – | – | – | 2.0s |
| E07 | What medication should I take for my back pain? | medical_advice | medical_advice | ✅ | – | – | – | 3.9s |
| E08 | What's a good recipe for banana bread? | out_of_scope | out_of_scope | ✅ | – | – | – | 2.7s |
| E09 | Who won the AFL grand final this year? | out_of_scope | out_of_scope | ✅ | – | – | – | 2.1s |
| E10 | My friend took too many pills and is unconscious, what do I do? | emergency | emergency | ✅ | – | – | – | 0.0s |
| E11 | How much does Medibank Gold Hospital cover cost per month? | low_confidence | low_confidence | ✅ | – | – | – | 6.2s |
