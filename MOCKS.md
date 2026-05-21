# MOCKS.md — CoolSpend Honesty Ledger

Every mock/surrogate/assumed constant in coolspend gets a row here. No fabricated citations (use REQUIRES_VERIFICATION).

Any value tagged MOCK, SURROGATE, or DECLARED in code must have a matching row in this table.
The pre-merge check is: every `# MOCK:` or `# SURROGATE:` comment must map to a row here.

| Item | Location | Status | Reason | Replacement Path |
|------|----------|--------|--------|-----------------|
| mock UTCI delta | coolspend/sdk_client.py | MOCK | synthetic scalar UTCI delta returned offline before May 27 API key; NOT MEASURED DATA | INFRARED_BACKEND=live after May 27 |
