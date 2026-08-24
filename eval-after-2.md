# Retrieval Evaluation — Second Brain RAG

**Test queries:** 21 across 15 vaults  
**Top-1 accuracy:** 14/21 (67%)  
**Top-K accuracy:** 18/21 (86%)

| Vault | Query | Expected note | Result | Top sim |
|---|---|---|---|---|
| Card-Payments-Vault | How does card payment reconciliation work end to end? | …Reconciliation-Pipeline | FAIL (wrong notes) | 0.755 |
| Card-Payments-Vault | What is the difference between the issuer host and the acquirer host? | …Issuer-Acquirer-Hosts | PASS (rank 1) | 0.821 |
| SWIFT-Vault | How does Canada's high value payment system LYNX work? | …LYNX-Canada-HVPS | PASS (rank 4) | 0.820 |
| SWIFT-Vault | What sanctions screening happens on a SWIFT payment? | …Compliance-Screening-SWIFT | PASS (rank 1) | 0.814 |
| Open-Banking-RTR-Vault | Who is liable for APP fraud in open banking? | …Fraud-Including-APP-Fraud | PASS (rank 3) | 0.775 |
| Open-Banking-RTR-Vault | What is Canada's consumer-driven banking framework? | …Canadian-Consumer-Driven-Banking-Framework | PASS (rank 1) | 0.891 |
| AAIR-Vault | What does the EU AI Act require for high-risk AI systems? | …EU-AI-Act | PASS (rank 1) | 0.849 |
| AAIR-Vault | Explain the NIST AI RMF map function | …NIST-AI-RMF-Map-Function | PASS (rank 2) | 0.858 |
| Treasury_Vault | How is foreign exchange risk managed in treasury? | …FX-Risk-Management | PASS (rank 1) | 0.752 |
| GenAI-for-Banking | What are the OWASP top 10 risks for large language models? | …OWASP-LLM-Top-10 | PASS (rank 1) | 0.754 |
| GenAI-for-Banking | How do I design a retrieval augmented generation architecture for banking? | …Banking-RAG-Reference-Architecture | FAIL (wrong notes) | 0.815 |
| Modern-Data-Architecture-Vault | What is the difference between a data fabric and a data mesh? | …Data-Fabric-vs-Data-Mesh | PASS (rank 1) | 0.855 |
| Service-Mesh-Vault | How does mutual TLS provide zero trust in a service mesh? | …mTLS-and-Zero-Trust | PASS (rank 1) | 0.812 |
| AWS-Well-Architected | What does the AWS security pillar say about data protection? | …SEC-Data-Protection | PASS (rank 1) | 0.788 |
| Azure Architect Vault | Should I use Azure Virtual WAN or a hub and spoke network? | …Virtual WAN vs Hub-Spoke | PASS (rank 2) | 0.829 |
| CRISC Knowledge Vault | How do I set a key risk indicator threshold? | …KRI Threshold Setting | PASS (rank 1) | 0.681 |
| CBAP Knowledge Vault | How do I write a BRD that survives regulatory scrutiny? | …Writing a BRD That Survives Regulatory Scrutiny | PASS (rank 1) | 0.732 |
| PMP Knowledge Vault | What are the common patterns in financial IT project failures? | …Pattern of Financial IT Failures | PASS (rank 1) | 0.777 |
| ISO27001 Knowledge Vault | How does ISO 27001 map to OSFI B-13? | …OSFI B-13 × ISO 27001 Alignment | PASS (rank 1) | 0.770 |
| The-Architects-Codex | What is the difference between TLS SSL and mTLS? | …TLS-and-mTLS-Deep-Dive | PASS (rank 1) | 0.792 |
| The-Architects-Codex | How do I migrate cryptography to be quantum safe? | …PQC-Migration-and-Crypto-Agility | FAIL (wrong notes) | 0.801 |
