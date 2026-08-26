# Working-question evaluation

_Run 2026-08-26 14:28_ · 40 questions

Rate each row by hand. **Answer**: 1-5. **Cards**: `add` (told me something the prose did not), `echo` (restated the question or the prose), `absent` (no practitioner layer surfaced).

| # | Category | Type | Question | Top sim | how_layer | Echo | Answer | Cards | Note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | payments | conceptual | What actually breaks if we truncate a party name during MX to MT translation? | 0.768 | - |  |  |  |  |
| 2 | payments | procedural | What do I need to ask the vendor about their CBPR+ usage guideline conformance? | 0.721 | rank 2 | 0.72 |  |  |  |
| 3 | payments | diagnostic | A pacs.008 was NAK'd at the network. Where do I start looking? | 0.694 | - |  |  |  |  |
| 4 | payments | conceptual | How is a UETR generated and preserved across a cover payment pair? | 0.790 | - |  |  |  |  |
| 5 | payments | procedural | How do I write the requirement for structured address handling before the November milestone? | 0.717 | - |  |  |  |  |
| 6 | payments | diagnostic | Payments are settling but our reconciliation shows breaks. What are the usual causes? | 0.751 | - |  |  |  |  |
| 7 | payments | conceptual | What is the difference between ACSP and ACSC in a pacs.002 and why does it matter? | 0.710 | - |  |  |  |  |
| 8 | payments | procedural | What should the BSA own in a payment hub cutover plan? | 0.745 | - |  |  |  |  |
| 9 | canada-rails | conceptual | How does intraday liquidity get managed against LYNX settlement? | 0.841 | rank 1 | 0.785 |  |  |  |
| 10 | canada-rails | diagnostic | We missed the LYNX cut-off. What happens to the payment and what do we tell the client? | 0.774 | - |  |  |  |  |
| 11 | canada-rails | procedural | How do I specify the routing rules between RTM, UPM and CDM? | 0.719 | - |  |  |  |  |
| 12 | canada-rails | conceptual | What is RTR and how does it differ from LYNX in liability terms? | 0.764 | - |  |  |  |  |
| 13 | canada-rails | diagnostic | What goes wrong when a bank treats RTR like a batch rail? | 0.734 | rank 1 | 0.703 |  |  |  |
| 14 | fincrime | conceptual | What is the difference between blocking and rejecting a payment? | 0.755 | - |  |  |  |  |
| 15 | fincrime | diagnostic | What breaks when sanctions screening sits before message translation? | 0.757 | rank 5 | 0.696 |  |  |  |
| 16 | fincrime | procedural | How do I check whether our ownership and control assessment is real or just vendor data? | 0.680 | - |  |  |  |  |
| 17 | fincrime | conceptual | Does the OFAC 50 percent rule aggregate across different sanctions programs? | 0.784 | - |  |  |  |  |
| 18 | fincrime | diagnostic | Our screening alert volume dropped after migration. Is that good news? | 0.688 | - |  |  |  |  |
| 19 | fincrime | procedural | What do I ask in a sanctions screening design review? | 0.745 | - |  |  |  |  |
| 20 | security | conceptual | How does ISO 27001 Annex A map onto a payment screening system? | 0.726 | - |  |  |  |  |
| 21 | security | procedural | How do I evidence that a control is operating, not just designed? | 0.724 | rank 1 | 0.689 |  |  |  |
| 22 | security | diagnostic | An auditor says our SoA is inconsistent with our risk assessment. What did we likely get wrong? | 0.719 | - |  |  |  |  |
| 23 | security | conceptual | What changed between ISO 27001:2013 and 2022 that actually affects an audit? | 0.796 | - |  |  |  |  |
| 24 | security | procedural | What do I need in place before a Stage 2 audit? | 0.772 | rank 5 | 0.666 |  |  |  |
| 25 | security | diagnostic | What are the common reasons a nonconformity gets classified as major rather than minor? | 0.676 | - |  |  |  |  |
| 26 | crypto | conceptual | Why does harvest-now-decrypt-later change the timeline for a payments estate? | 0.699 | - |  |  |  |  |
| 27 | crypto | procedural | How do I build a cryptographic inventory when nobody knows where the keys are? | 0.709 | - |  |  |  |  |
| 28 | crypto | diagnostic | What breaks first when you swap in a post-quantum KEM on an existing TLS path? | 0.783 | - |  |  |  |  |
| 29 | crypto | conceptual | What is crypto-agility in practice, beyond the slogan? | 0.770 | rank 4 | 0.669 |  |  |  |
| 30 | ai-governance | conceptual | What does the EU AI Act actually require for a high-risk system? | 0.838 | - |  |  |  |  |
| 31 | ai-governance | procedural | How do I write acceptance criteria for an AI fraud-scoring model in payments? | 0.747 | - |  |  |  |  |
| 32 | ai-governance | diagnostic | What goes wrong when a model risk framework is applied to an LLM feature? | 0.732 | - |  |  |  |  |
| 33 | ai-governance | conceptual | How does NIST AI RMF Govern differ from Manage in practice? | 0.815 | - |  |  |  |  |
| 34 | ai-governance | procedural | What evidence would an auditor want for an AI system in a regulated bank? | 0.756 | - |  |  |  |  |
| 35 | architecture | conceptual | When is event-driven the wrong choice for a payment flow? | 0.780 | - |  |  |  |  |
| 36 | architecture | diagnostic | What are the failure modes of an idempotency key implemented on the wrong boundary? | 0.714 | - |  |  |  |  |
| 37 | architecture | procedural | How do I document a system for a C4 review that a regulator will also read? | 0.749 | - |  |  |  |  |
| 38 | architecture | conceptual | What does mTLS actually buy you inside a service mesh that TLS does not? | 0.777 | - |  |  |  |  |
| 39 | architecture | diagnostic | Why do reconciliation architectures usually fail at the matching key rather than the pipeline? | 0.718 | - |  |  |  |  |
| 40 | architecture | procedural | How do I specify operational resilience requirements that map to OSFI E-21? | 0.810 | rank 1 | 0.709 |  |  |  |

## What to do with this

- **Answer 1-2** -> the vault has a content gap. Write the note.
- **Cards `echo`** -> the practitioner layer restates instead of adding. This is the same defect as the formulaic `design` fields: repair, do not extend.
- **Cards `absent` on a procedural question** -> routing or retrieval issue, not a content issue.
- **Refused** -> either a real gap or the similarity gate is too tight. Check which before changing the threshold.
