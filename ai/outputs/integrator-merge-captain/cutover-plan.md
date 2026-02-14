# Cutover Plan

## Metadata

| Field         | Value                          |
|---------------|--------------------------------|
| Date          | [YYYY-MM-DD]                   |
| Owner         | [cutover lead]                 |
| Related links | [issue/PR/ADR URLs]            |
| Status        | Draft / Reviewed / Approved    |

## Cutover Overview

- **Cutover date and time:** [YYYY-MM-DD HH:MM timezone]
- **Expected duration:** [estimated total time from start to verification complete]
- **Environment:** [production / staging / other]
- **Change type:** [deployment / migration / infrastructure / combined]

## Participants

| Role                    | Name             | Responsibility                              |
|-------------------------|------------------|---------------------------------------------|
| Cutover lead            | [name]           | Coordinates execution, makes go/no-go calls |
| Engineering             | [name]           | Executes deployment steps                   |
| QA                      | [name]           | Runs verification checks                    |
| Database / Data         | [name]           | Executes migration or data changes          |
| Infrastructure / Ops    | [name]           | Monitors systems, manages infrastructure    |
| Communications          | [name]           | Sends status updates to stakeholders        |

## Pre-Cutover Checklist

*Complete all items before starting the cutover.*

- [ ] Final build artifact verified and tagged
- [ ] All required approvals obtained
- [ ] Rollback procedure reviewed and confirmed feasible
- [ ] Database backup taken and verified
- [ ] Monitoring and alerting configured for cutover period
- [ ] All participants confirmed available for the cutover window
- [ ] Communication sent: cutover is about to begin

## Cutover Steps

*Execute in order. Record actual start time and completion for each step.*

| Step | Action                          | Expected Duration | Owner    | Actual Start | Actual End | Status  |
|------|---------------------------------|-------------------|----------|-------------|------------|---------|
| 1    | [action description]            | [minutes]         | [person] |             |            | Pending |
| 2    | [action description]            | [minutes]         | [person] |             |            | Pending |
| 3    | [action description]            | [minutes]         | [person] |             |            | Pending |
| 4    | [action description]            | [minutes]         | [person] |             |            | Pending |
| 5    | [action description]            | [minutes]         | [person] |             |            | Pending |

## Verification Steps

*Run these checks after cutover completes to confirm success.*

- [ ] Application is reachable and responding
- [ ] Health check endpoints return healthy status
- [ ] Core user workflows tested end to end
- [ ] Data integrity spot-checks passed
- [ ] No elevated error rates in monitoring
- [ ] Performance within acceptable thresholds

## Rollback Triggers

*If any of these conditions occur, initiate rollback immediately.*

- [ ] Application is unreachable for more than [duration]
- [ ] Error rate exceeds [threshold] for more than [duration]
- [ ] Data corruption or data loss detected
- [ ] Critical user workflow is broken with no workaround
- [ ] [Additional project-specific trigger]

## Rollback Procedure

*If rollback is triggered, execute these steps in order.*

1. [Announce rollback to all participants]
2. [Revert deployment to previous version]
3. [Restore database from pre-cutover backup if needed]
4. [Verify rollback: application healthy, data intact]
5. [Notify stakeholders that rollback is complete]
6. [Schedule post-mortem to investigate root cause]

## Communication Plan

| Audience            | Channel          | Timing                    | Message                               |
|---------------------|------------------|---------------------------|---------------------------------------|
| Internal team       | [channel/tool]   | Before cutover starts     | [Cutover beginning, expected duration]|
| Internal team       | [channel/tool]   | After each major step     | [Progress update]                     |
| End users           | [channel/tool]   | Before any downtime       | [Scheduled maintenance notice]        |
| End users           | [channel/tool]   | After cutover complete    | [Service restored / changes live]     |
| Stakeholders        | [channel/tool]   | After verification passes | [Cutover successful, summary]         |

## Post-Cutover Monitoring

- **Monitoring period:** [duration, e.g., 24 hours after cutover]
- **Primary monitor:** [person or team responsible]
- **Escalation path:** [who to contact if issues arise]
- **Criteria to close monitoring period:** [e.g., no incidents for 24 hours]

## Definition of Done

- [ ] All cutover steps completed and timed
- [ ] All verification checks passed
- [ ] No rollback triggers fired
- [ ] Post-cutover monitoring period completed without incident
- [ ] Stakeholders notified of successful cutover
- [ ] Lessons learned captured for future cutovers
