# ----------------------------------------------------------------------------
# eval_retrieval.py ADDITIONS - Security Trade-off / Decision notes
# ----------------------------------------------------------------------------
# Append these to your existing eval query list. The shape below matches what
# your eval prints (vault label, natural-language query, expected note key).
# ADAPT the field names/structure to your actual EVAL_QUERIES schema - paste
# eval_retrieval.py if you want me to wire these in exactly rather than by hand.
#
# These are deliberately DECISION-PHRASED ("X vs Y", "should I use...") because
# that is the query class the new hybrid (3a) retriever now handles well, and
# it is exactly how a BSA/architect would ask. Expected = the new cluster note.
#
# vault = "The-Architects-Codex" for all (cluster lives there).
# ----------------------------------------------------------------------------

NEW_EVAL_QUERIES = [
    # core six
    ("The-Architects-Codex",
     "should I use mTLS or JWT for service-to-service authentication",
     "Trade-off-Decisions/mTLS-vs-JWT"),

    ("The-Architects-Codex",
     "do I still need a WAF if I already have an API gateway",
     "Trade-off-Decisions/WAF-vs-API-Gateway"),

    ("The-Architects-Codex",
     "tokenization vs encryption for card data and reducing PCI scope",
     "Trade-off-Decisions/Tokenization-vs-Encryption"),

    ("The-Architects-Codex",
     "OAuth client credentials versus mTLS for service to service authorization",
     "Trade-off-Decisions/OAuth-vs-mTLS-Service-to-Service"),

    ("The-Architects-Codex",
     "symmetric vs asymmetric cryptography and the post quantum impact",
     "Trade-off-Decisions/Symmetric-vs-Asymmetric-Cryptography"),

    ("The-Architects-Codex",
     "RBAC or ABAC for banking authorization with segregation of duties",
     "Trade-off-Decisions/RBAC-vs-ABAC"),

    # optional four (include the matching ones if you keep these notes)
    ("The-Architects-Codex",
     "how do I apply defense in depth in a payment hub and kubernetes",
     "Trade-off-Decisions/Defense-in-Depth-Layered-Controls"),

    ("The-Architects-Codex",
     "how to secure an Azure cloud landing zone for a bank",
     "Trade-off-Decisions/Cloud-Landing-Zone-Security"),

    ("The-Architects-Codex",
     "what are the six functions of the NIST cybersecurity framework",
     "Trade-off-Decisions/NIST-Cybersecurity-Framework-CSF-2"),

    ("The-Architects-Codex",
     "compare STRIDE PASTA and other threat modeling methodologies",
     "Trade-off-Decisions/Threat-Modeling-Methodologies-Compared"),
]
