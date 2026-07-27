# Hire Journey visual language

- Status: active
- Last updated: 27 July 2026
- Implementation branch: `feat/ui-refresh`
- Scope: frontend presentation and interaction conventions

Hire Journey should feel like a calm, credible career workspace. The interface
uses clear hierarchy, neutral surfaces, restrained color, and direct language so
people can focus on reviewing their information and making career decisions.
This document defines the default visual rules for new and existing screens.

## Principles

1. **Calm over decorative.** Use whitespace, hierarchy, and borders before
   gradients, shadows, animation, or illustration.
2. **Truthful state.** Progress and success styling must reflect known product
   state. Loading and unresolved errors must not imply completion.
3. **One clear next action.** A screen should have one primary indigo action.
   Secondary and reversible actions are visually quieter.
4. **Editable and recoverable.** Forms keep errors beside the relevant field,
   preserve safe user input, and expose a recovery action when one exists.
5. **Functional elements only.** Do not show disabled future navigation or
   controls without a working destination.

## Typography

Geist Sans is the only interface and heading family. Geist Mono is reserved for
request references and genuinely technical or tabular values such as dates,
URLs, and salary figures. It is not used to make ordinary labels look technical.

The standard scale is:

| Use | Size | Guidance |
| --- | ---: | --- |
| Page title | 32px | Semibold, tight tracking |
| Section title | 20px | Semibold |
| Card title | 16px | Semibold |
| Body | 15–16px | Regular, comfortable line height |
| Label | 14px | Medium |
| Metadata | 12–13px | Muted; mono only when technically meaningful |

Avoid tiny uppercase labels, decorative italics, and gradient text. Sentence
case is the default for headings, navigation, labels, and actions.

## Color

| Token | Value | Use |
| --- | --- | --- |
| Background | `#F8FAFC` | Page canvas |
| Surface | `#FFFFFF` | Forms, navigation, primary content |
| Muted surface | `#F1F5F9` | Selected controls and quiet grouping |
| Ink | `#172033` | Primary text |
| Muted text | `#64748B` | Supporting text and inactive state |
| Border | `#E2E8F0` | Dividers and control outlines |
| Primary | `#4F46E5` | Primary actions and active state |
| Primary hover | `#4338CA` | Primary hover state |
| Success | `#047857` | Confirmed completion and success feedback |
| Error | `#B42318` | Validation and destructive actions |

Coral is a limited marketing accent. It must not compete with indigo for primary
application actions or represent product state.

## Surfaces and spacing

- Prefer flat white surfaces on the slate page background.
- Use subtle borders and section dividers before shadows.
- Ordinary controls and cards use 8–10px radii; larger form surfaces may use
  12px. Pills are reserved for chips, tags, and compact selections.
- Repeatable form rows use a bordered, muted container without elevation.
- Keep labels outside input borders and use a consistent 44px control height.
- Helper text and inline errors sit directly below the control they describe.

## Actions and focus

The shared `Button` variants are authoritative for ordinary actions:

- `default`: the single primary indigo action;
- `outline`: secondary or alternative actions;
- `ghost`: low-emphasis navigation and utility actions; and
- `destructive`: actions with destructive consequences.

Primary form actions are 44px tall. Every interactive element must retain a
visible keyboard focus ring. Icon-only controls require an accessible name, and
disabled or busy controls must expose their state without relying on color.

## Navigation

Application navigation only exposes working destinations. Dashboard and Profile
are available in both the large-screen sidebar and the compact mobile header.
Both variants provide account identity and logout, and the active route uses
`aria-current="page"`. Future destinations remain hidden until they work.

## Authentication

Authentication retains the large-screen split layout and the single-column
mobile form. The brand panel explains the product in three neutral parts:
upload a resume, review the profile, and discover relevant roles. It must not
look like a stateful progress tracker. Trust copy must be factual and verifiable.
Password and Google authentication behavior remains independent of presentation.

## Onboarding

Onboarding uses one primary white form surface with subtle section dividers.
Its ordered progress list has exactly three real stages: Resume, Profile, and
Preferences.

| Known state | Progress presentation |
| --- | --- |
| Empty or parsing profile | Resume active |
| Editable profile | Resume complete; Profile active |
| Editable preferences | Resume and Profile complete; Preferences active |
| Loading or load error | All steps neutral; no completion claim |

The active stage uses `aria-current="step"`, completed stages use the success
color and hidden completion text, and future stages stay neutral. Progress does
not pulse or animate decoratively.

Inline validation, focus-first-invalid behavior, request references, accessible
date precision controls, same-file resume retry, stale-project recovery, and the
sticky save footer are functional requirements. Visual changes must preserve
their field paths, ARIA relationships, and state transitions.

## Post-onboarding profile

The permanent Profile page is read-first. It presents identity, experience,
education, certifications, projects, skills, and job preferences as one
scannable professional record. A single **Edit profile** action opens the
existing hardened detail and preference forms; onboarding itself remains
always editable and is not routed through this presentation.

The profile editor has one save action. Details are validated and saved before
preferences, and any failure keeps the editor open with its existing inline
errors and recovery controls. Cancel dismisses transient feedback and reloads
both aggregates from the server so unsaved values are never presented as saved
profile data.

## Review checklist

Before merging a new screen or visual change, verify:

- one obvious primary action and no competing CTA colors;
- working keyboard focus order and visible focus at 200% zoom;
- sufficient contrast for text, borders, errors, and active state;
- wrapping at 375px and with long names, locations, and error messages;
- honest loading, empty, success, error, and disabled states;
- no ordinary labels in mono, tiny uppercase text, or decorative progress; and
- the same functional destinations and account actions on mobile and desktop.
