# Secrets Rotation Plan: [Project Name]

## Metadata

| Field          | Value                                    |
|----------------|------------------------------------------|
| Date           | [YYYY-MM-DD]                             |
| Owner          | [DevOps Lead / Security Engineer]        |
| Related Links  | [Secrets policy, environment matrix, ADR]|
| Status         | Draft / Reviewed / Approved              |

---

## 1. Secrets Inventory

*List every secret that requires rotation. Never record actual secret values in this document.*

| Secret Identifier        | Type              | Current Location(s)          | Environments     | Owner         | Rotation Frequency | Last Rotated  |
|--------------------------|-------------------|------------------------------|------------------|---------------|--------------------|---------------|
| [DATABASE_PASSWORD]      | [Password]        | [Vault path / env var]       | [All]            | [Name/Team]   | [90 days]          | [YYYY-MM-DD]  |
| [API_KEY_PAYMENT_SVC]    | [API key]         | [Vault path / env var]       | [Staging, Prod]  | [Name/Team]   | [180 days]         | [YYYY-MM-DD]  |
| [TLS_CERT]               | [Certificate]     | [Cert manager]               | [Staging, Prod]  | [Name/Team]   | [Auto / 365 days]  | [YYYY-MM-DD]  |
| [SIGNING_KEY]            | [Symmetric key]   | [Vault path]                 | [Prod]           | [Name/Team]   | [365 days]         | [YYYY-MM-DD]  |
| [Add rows as needed]     |                   |                              |                  |               |                    |               |

---

## 2. Rotation Procedure

*For each secret (or class of secrets), document the step-by-step rotation process.*

### 2.1 [Secret Identifier / Class]

*Describe the rotation steps specific to this secret type.*

**Pre-rotation checklist:**
- [ ] Rotation window scheduled and communicated
- [ ] Dependent services identified (see Section 3)
- [ ] Rollback procedure reviewed
- [ ] Monitoring dashboards open during rotation

**Rotation steps:**
1. Generate the new secret value using [approved method / tool].
2. Store the new value in [secret storage location].
3. Update the secret reference in [environment/config/deployment].
4. Deploy or restart dependent services to pick up the new value.
5. Verify dependent services authenticate successfully with the new secret.
6. Revoke or disable the old secret value.
7. Confirm the old value no longer grants access.
8. Update the "Last Rotated" date in the inventory above.

**Estimated duration:** [N minutes]

---

## 3. Dependent Services

*Map each secret to the services that consume it. Rotation will affect these.*

| Secret Identifier        | Dependent Service(s)                | Impact if Rotation Fails          |
|--------------------------|-------------------------------------|-----------------------------------|
| [DATABASE_PASSWORD]      | [App server, background workers]    | [Service cannot connect to DB]    |
| [API_KEY_PAYMENT_SVC]    | [Payment processing module]         | [Payment calls fail]              |
| [TLS_CERT]               | [Load balancer, API gateway]        | [TLS handshake failures]          |
| [Add rows as needed]     |                                     |                                   |

---

## 4. Post-Rotation Testing

*Verify the rotation succeeded without breaking anything.*

- [ ] Dependent services start and pass health checks
- [ ] Authentication/authorization flows succeed end-to-end
- [ ] No elevated error rates in monitoring dashboards
- [ ] Integration tests pass against the rotated environment
- [ ] Old secret value confirmed revoked (manual test if possible)

---

## 5. Rollback If Rotation Fails

*If the new secret causes failures, restore the previous value.*

1. Re-deploy the old secret value from [backup location / previous Vault version].
2. Restart or redeploy dependent services.
3. Verify services recover and health checks pass.
4. Investigate root cause before re-attempting rotation.
5. Document the failure in [incident tracker / post-mortem].

**Maximum time to rollback:** [N minutes]

---

## 6. Rotation Schedule

*Maintain a calendar of upcoming rotations.*

| Secret Identifier        | Last Rotated   | Next Rotation Due | Owner         | Reminder Set |
|--------------------------|----------------|--------------------|---------------|--------------|
| [DATABASE_PASSWORD]      | [YYYY-MM-DD]  | [YYYY-MM-DD]       | [Name/Team]   | [ ]          |
| [API_KEY_PAYMENT_SVC]    | [YYYY-MM-DD]  | [YYYY-MM-DD]       | [Name/Team]   | [ ]          |
| [TLS_CERT]               | [YYYY-MM-DD]  | [YYYY-MM-DD]       | [Name/Team]   | [ ]          |
| [Add rows as needed]     |                |                    |               |              |

---

## Definition of Done

- [ ] All secrets requiring rotation are inventoried
- [ ] Rotation procedure documented for each secret type
- [ ] Dependent services mapped for every secret
- [ ] Post-rotation test plan defined
- [ ] Rollback procedure documented and reviewed
- [ ] Rotation schedule established with reminders configured
- [ ] Plan reviewed and approved by security and operations leads
