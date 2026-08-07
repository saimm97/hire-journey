# Issue Tracker

Engineering work for HireJourney is tracked in Jira Cloud.

## Project

- Site: https://career-opss.atlassian.net
- Project name: hirejourney
- Project key: `HIJ`
- Project view: https://career-opss.atlassian.net/jira/software/projects/HIJ/list

## Issue hierarchy

Use the following hierarchy:

- Epic
  - Story
  - Task
  - Bug

An Epic represents a meaningful product capability or delivery milestone.

Use a Story for user-visible or operationally valuable behavior. Use a Task for supporting engineering work that does not independently represent user behavior. Use a Bug for behavior that contradicts an existing requirement or accepted contract.

## Workflow

Issues move through:

1. To Do
2. In Progress
3. Review
4. Done

Agents may recommend a status or transition in a ticket draft, but must not apply the transition in Jira.

## Agent permissions

Agents operate in draft-only mode.

Agents may:

- Prepare Jira-ready ticket titles and descriptions.
- Recommend an issue type, parent Epic, priority, estimate, labels, and dependencies.
- Prepare acceptance criteria and verification steps.
- Recommend links such as blocks, is blocked by, relates to, or duplicates.
- Read repository documentation and code to make drafts accurate.

Agents must not:

- Create Jira issues.
- Update existing Jira issues.
- Transition issue status.
- Add comments or attachments.
- Apply labels, priorities, estimates, assignees, or relationships.
- Use an Atlassian connector to mutate Jira.

The maintainer reviews every draft and performs all Jira mutations manually.

## Draft format

A Jira ticket draft should include:

- Issue type
- Parent Epic, when applicable
- Summary
- User or operational value
- Scope
- Acceptance criteria
- Out of scope
- Dependencies
- Suggested priority
- Suggested estimate
- Suggested labels
- Verification steps

Drafts should be independently shippable where practical. Avoid splitting one behavior into disconnected backend, frontend, and testing tickets when none delivers value alone.
