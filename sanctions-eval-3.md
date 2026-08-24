# Retrieval Evaluation — Second Brain RAG

**Test queries:** 12 across 15 vaults  
**Top-1 accuracy:** 6/12 (50%)  
**Top-K accuracy:** 8/12 (67%)

| Vault | Query | Expected note | Result | Top sim |
|---|---|---|---|---|
| [A] The-Architects-Codex | What breaks when sanctions screening runs before message translation? | …Sanctions-Screening-in-ISO-20022-Payment-Flows | PASS (rank 1) | 0.767 |
| [A] The-Architects-Codex | How do I check whether our ownership and control assessment is real or just vendor data? | …Canada-Sanctions-Framework-SEMA-JVCFOA-UN-Act | FAIL (wrong notes) | 0.662 |
| [A] The-Architects-Codex | What goes wrong when SDN and SSI entries are loaded into a single list? | …OFAC-Sanctions-Programs-and-the-50-Percent-Rule | FAIL (wrong notes) | 0.637 |
| [A] The-Architects-Codex | How can I verify that every screening system is using the same list version? | …Sanctions-Screening-Controls-and-Tuning | PASS (rank 2) | 0.644 |
| [A] The-Architects-Codex | What is the failure where one corridor is fixed but the root cause stays live elsewhere? | …Sanctions-Program-Governance-and-Enforcement | FAIL (wrong notes) | 0.624 |
| [A] The-Architects-Codex | How do I test that a general licence suppression rule stops when the licence expires? | …OFAC-Sanctions-Programs-and-the-50-Percent-Rule | FAIL (wrong notes) | 0.590 |
| [B] The-Architects-Codex | Does the OFAC 50 percent rule aggregate ownership across blocked persons? | …OFAC-Sanctions-Programs-and-the-50-Percent-Rule | PASS (rank 1) | 0.882 |
| [B] The-Architects-Codex | What is the deemed ownership rule under SEMA and the JVCFOA? | …Canada-Sanctions-Framework-SEMA-JVCFOA-UN-Act | PASS (rank 1) | 0.826 |
| [B] The-Architects-Codex | How does AIS manipulation work in maritime sanctions evasion? | …Sanctions-Evasion-Typologies | PASS (rank 1) | 0.763 |
| [B] The-Architects-Codex | What is the UK reporting deadline for informing OFSI of a designated person? | …EU-and-UK-Sanctions-Frameworks | PASS (rank 1) | 0.737 |
| [B] The-Architects-Codex | What is the difference between blocking and rejecting a payment? | …OFAC-Sanctions-Programs-and-the-50-Percent-Rule | PASS (rank 1) | 0.739 |
| [B] The-Architects-Codex | Why does ISO 20022 structured party data improve sanctions screening precision? | …Sanctions-Screening-in-ISO-20022-Payment-Flows | PASS (rank 4) | 0.797 |
