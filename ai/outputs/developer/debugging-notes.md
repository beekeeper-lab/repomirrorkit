# Debugging Notes: [Issue Title or Symptom]

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | YYYY-MM-DD                     |
| Owner         | [Developer name]               |
| Related links | [Issue / incident / PR links]  |
| Status        | Draft / Reviewed / Approved    |

*Structured record of a debugging investigation. Fill this in as you investigate so the reasoning is preserved for future reference.*

---

## Issue Reference

- **Issue / Incident:** [Link or ID]
- **Reported by:** [Name or team]
- **Severity:** [Critical / High / Medium / Low]
- **Summary:** [One sentence description of the observed problem]

---

## Reproduction Steps

*Exact steps to reproduce the issue consistently.*

1. [Step 1: e.g., "Send POST /api/v1/resources with payload {...}"]
2. [Step 2: e.g., "Wait 30 seconds for async processing"]
3. [Step 3: e.g., "Query GET /api/v1/resources/:id -- observe 500 error"]

**Reproducibility:** [Always / Intermittent / Once only]

---

## Environment Details

| Attribute          | Value                                |
|--------------------|--------------------------------------|
| Environment        | [e.g., Staging / Production / Local] |
| Service version    | [e.g., v2.3.1 / commit SHA]         |
| Runtime            | [e.g., language version, OS]         |
| Relevant config    | [e.g., feature flags, env vars]      |

---

## Hypotheses

*List candidate root causes before testing them. Number them for reference in the experiments table.*

1. [e.g., "Race condition between async handler and database commit"]
2. [e.g., "Null value in payload field X bypasses validation"]
3. [e.g., "Timeout from downstream service causes retry storm"]

---

## Experiments Conducted

| # | Hypothesis Tested | Experiment / Test Performed             | Result                           |
|---|-------------------|-----------------------------------------|----------------------------------|
| 1 | Hypothesis 1      | [e.g., "Added logging around DB commit"] | [e.g., "Confirmed commit completes before handler returns -- ruled out"] |
| 2 | Hypothesis 2      | [e.g., "Sent payload with null field X"] | [e.g., "Reproduced the 500 error -- confirmed"] |
| 3 | Hypothesis 3      | [e.g., "Checked downstream service logs"]| [e.g., "No timeouts in the window -- ruled out"] |

---

## Root Cause

[Clear statement of the confirmed root cause, with evidence from the experiments above.]

---

## Fix Applied / Proposed

- **Fix description:** [What was changed and why it addresses the root cause]
- **PR / Commit:** [Link to the fix]
- **Verification:** [How the fix was verified, e.g., "Reproduced steps above -- now returns 200"]

---

## Prevention

*How can we prevent this class of issue from recurring?*

- [ ] [e.g., "Add input validation for field X at the API boundary"]
- [ ] [e.g., "Add integration test covering null payload scenario"]
- [ ] [e.g., "Add alerting for elevated 500 rates on this endpoint"]

---

## Lessons Learned

*What did this investigation teach the team?*

- [e.g., "Our validation layer does not cover optional fields that become required downstream."]
- [e.g., "We need structured logging in the async processing path to reduce debugging time."]

---

## Definition of Done

- [ ] Root cause is confirmed with evidence
- [ ] Fix is implemented and verified
- [ ] Prevention measures are identified and tracked as follow-up tasks
- [ ] Lessons learned are documented and shared with the team
