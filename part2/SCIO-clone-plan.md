# SCIO Clone — Build Plan

**Author:** Hoang Tran · **Date:** 2026-10-14 · **Status:** v2, numbers re-checked against the live product and help center

## 1. Summary

- **What:** A multi-tenant digital-signage CMS plus a player runtime. Customers pair screens, upload content, arrange it into playlists, split screens and schedules, push it to a fleet, and see what is playing. Playback keeps working when the network goes down.
- **MVP, 22 weeks:** CMS, players for Android (which also covers Fire TV), Windows/macOS/Linux, Samsung Tizen and LG webOS, 8 content apps, schedules, teams, per-screen billing and proof of play. This is enough to sell to a small or mid-size business with 5–500 screens.
- **Phase 2, about 16 more weeks:** Designer (a Canva-style editor), data sources, SSO, sub-accounts and white-label, a public API, and about 30 more content apps.
- **Team:** 7 engineers, 1 QA engineer, 1 product designer/PM. This size gets the MVP out in under six months without coordination costs taking over.
- **AI-assisted estimate:** the team works with AI coding assistants. I apply a per-epic AI factor instead of one flat discount: about 17% saving overall (136 => 113 engineer-weeks for the MVP). Without AI the same MVP needs about 24 weeks, not 22.
- **Biggest bet:** one TypeScript player runtime wrapped in thin native shells. 12 of the 14 platforms OptiSigns supports can host an HTML5 web view (only Roku and Apple TV cannot), so one renderer covers most of the market.
- **Two kinds of "app" in this plan:** a **player** is the software installed on a device (Android, Windows, Tizen…). A **content app** is an integration such as YouTube, Weather or Google Slides that the customer adds under Files/Assets → Apps and that plays *inside* the player.

## 2. What I learned from the product

I used a Pro Plus trial (app.optisigns.com) and read the help center end to end: I scraped all of its articles (413 published) for Part 1 of this test.

| Area | What it actually is |
|---|---|
| **Screens** | Pair with a 6-digit code (with an option for lowercase codes). Each screen has tags, folders, location, orientation (0/90/180/270), scale mode, background music and mute. One of three things is bound to it: an **asset, a playlist or a schedule**. A separate **operational schedule** powers the TV on/off through HDMI-CEC or RS-232. An **OnHold** folder frees a licence without deleting the screen. Status is sent every 30 s, and a screen is marked offline after 10 min of silence. |
| **Players** | 14 platforms: Windows, macOS, Linux, Android, Fire OS, Amazon Signage, Apple TV, iOS, ChromeOS, Samsung Tizen/SSSP, LG webOS, BrightSign, Roku, Raspberry Pi. OptiSigns also sells its own hardware (OptiStick, Pro, ProMax) with built-in device management, which enables reboot, screenshot, Wi-Fi, time zone and bulk commands. |
| **Files/Assets** | Images, video and documents (up to 25 MB per file and 1 GB storage on Free), folders, sharing, favourites, trash, plus Feeds. **133 content apps** in the Add App picker (25 of them on the Free plan) are integrations that render as web content inside the player: YouTube, Weather, Power BI, Tableau, Google Slides, RSS, Teams Rooms, Salesforce, Grafana, Website, Split Screen and more. |
| **Playlists** | Ordered items, each with a duration, plus transitions, shuffle and per-type scaling. Advanced settings add **content-tag rules** (different screens play different items from the same playlist), **nested sub-playlists with their own schedule**, resume-on-next-play and max duration per item. The UI shows total size and runtime. |
| **Schedules** | A calendar of events with daily, weekly, monthly or custom recurrence and time-zone handling. The editor warns about overlaps; when they are intentional, the last-updated schedule wins. Each screen plays in its own local time zone. Items have live/expire dates. |
| **Designer / Templates** | A full canvas editor, and it is **included in the Free plan**. Its **widgets embed a Playlist, content apps, Video, Weather, Time and Date**, and **repeaters** bind to data. There is a template library with a "Try AI Designer" entry point. |
| **Engage** | Touch kiosks, QR overlays, lift-and-learn with IoT sensors, AI camera and check-in. It is a separate plan, with a 1-device trial on other plans. |
| **Analytics** | Proof of Play and AI Analytics. Proof of Play is only on Pro Plus and Enterprise: it is switched on for the account, then per screen in Edit Screen, and its real-time upload can be turned off to save bandwidth. |
| **Account** | Teams with screen quotas, roles (Owner, Super Admin, Admin, User, **Content Proposal, Content Approval**, Read Only, plus **custom roles**), MFA, sub-account billing, branding and custom domain, audit log, monitoring alerts, SAML SSO, API keys, external communications (RS-232), integrations, share links, data sources and tags. |
| **Commercial** | Licences are sold per screen. Plans are Free (3 screens), Standard, Pro Plus, Engage and Enterprise, plus add-ons: Video Wall, OptiSound, AeriCast, Engage, and Custom Domain at $10/mo. **Entitlements depend on the plan *and* the device type**: the Free plan only runs on OptiSigns hardware (Android Player, Pro/ProMax, OptiKiosk), Windows, macOS, Linux and Raspberry Pi; not on Fire TV, generic Android, smart TVs, Roku or Apple. The trial is Pro Plus with 2 screens. |

## 3. The one thing I did not expect, and what it changed

**The content model is a tree, not a list.**

I walked in expecting *screen => playlist => files*. What I found:

- A **Designer** layout can contain a **Playlist widget**.
- That playlist can contain **Designer assets**, **content apps** and **sub-playlists that carry their own schedule**.
- A **Split Screen** puts a different playlist in each zone.
- A **schedule** picks which of these trees is live.
- **Content-tag rules** then filter the tree per screen.

So what a screen shows at any moment is the result of evaluating a recursive tree, with *(time, screen tags, time zone)* as inputs.

This changed the plan in three ways:

1. **One polymorphic `ContentNode` model** (asset | content app | playlist | layout | schedule) instead of separate tables wired together ad hoc. The server compiles each screen's tree into a versioned, flattened **device manifest**: every media URL with a hash, plus the time rules. It rejects cycles at save time. The player never queries the CMS; it only reads manifests.
2. **The player renderer is a recursive zone/timeline evaluator from week 3**, not a slideshow. When Designer arrives in Phase 2 it becomes one more node type, not a player rewrite. Without this, I would have budgeted for a player rework around month 7.
3. **Split Screen moved into the MVP.** Once zones exist in the renderer, it costs about 4 engineer-weeks, and it is the most common "advanced" layout customers ask for.

## 4. Scope

**MVP (in):**
- Accounts, teams, the 7 built-in roles, custom roles and MFA.
- Content approval: Content Proposal users submit, Content Approval users publish.
- Pairing.
- Screen management: folders, tags, bulk edit, orientation, scale.
- Asset library: upload, transcode, thumbnails, PDF/PPTX => pages.
- Playlists: nested, transitions, tag rules.
- Schedules: recurrence, time zones, overlap priority, live/expire.
- Split screen.
- Push to screens.
- Offline playback.
- Status/heartbeat, remote screenshot and reload.
- Proof of play (basic report + CSV).
- Per-screen Stripe billing with plan entitlements and OnHold.
- 8 content apps: Website, YouTube, Weather, RSS/News, Google Slides, **Canva**, QR Code, Embed/HTML.
  - Each one tests a different part of the content-app framework: a plain URL, custom HTML/JS (which also covers content that runs with no network), external video, a polled data API, a changing feed, OAuth to a third party (Google Slides, Canva) and content generated from user input.
  - Canva is in because it is the MVP's answer to having no Designer: customers design in Canva and the screen shows the live design.

**Phase 2:**
- Designer and templates.
- Data sources / repeaters.
- Operational schedule (CEC/RS-232; needs native hooks).
- Sync play and video wall.
- SAML SSO, audit log, API keys, webhooks.
- Sub-accounts, white-label and custom domain.
- A content-app SDK and about 30 more content apps (Power BI, Teams Rooms, Google Calendar, Clock/Countdown…).
- Mobile admin app.

**The biggest scope bet:** Designer is in the Free plan, so the MVP does not match even OptiSigns' cheapest tier. MVP customers upload files or show designs from Canva through the Canva content app (Canva is in the top row of the picker). Designer costs about 36 engineer-weeks; putting it in the MVP would push launch by about 6 weeks. This is the first decision I would confirm with OptiSigns.

**Deliberately out, and why:**
- **Engage** (kiosks, AI camera, IoT): a separate product with separate buyers.
- **OptiSound and AeriCast:** they need licensing or hardware deals rather than engineering.
- **Own hardware and MDM, mass provisioning:** a business decision, not a software one.
- **Roku and Apple TV:** native-only, small share of signage installs.
- **AI Designer.**
- **BrightSign:** it supports HTML5, so it comes cheaply after Tizen/webOS. It is first in line for Phase 2.

## 5. Architecture (short)

- **CMS web:** React + TypeScript SPA.
- **Backend:** a **modular monolith** (TypeScript/Node, Postgres, Redis, S3 + CDN).
  - Modules: identity/tenancy, content, scheduling, devices, billing, reporting.
  - It splits into services only where load forces it, and the device gateway is the first candidate.
- **Media pipeline:** a queue of workers that run ffmpeg (normalising H.264/MP4), produce thumbnails, and convert documents to images with LibreOffice.
- **Device gateway:** a WebSocket connection per device (with long-poll fallback).
  - It sends "manifest version N is available" and receives heartbeats every 30 s and proof-of-play batches.
  - Target: **50k concurrent devices per gateway node pool** at launch.
- **Manifest compiler:**
  - Runs on every content, schedule or assignment change, through change events.
  - Rebuilds only the manifests of the affected screens.
  - Target: **under 10 s p95 from Save to the new content on an online screen**.
- **Player:**
  - **Core**: TypeScript, which renders zones and timelines and evaluates schedules locally in the device's time zone.
  - **Native shells**: Android (Kotlin), Electron (Windows/macOS/Linux), Tizen, webOS. Each provides storage, a download manager, auto-start, a watchdog and the device ID.
  - **Cache**: content-addressed by hash, so updates download only the delta. Downloaded media plays offline indefinitely; content apps that need the internet are skipped while offline, which matches OptiSigns' behaviour.

## 6. Sequence and timeline (team of 7 engineers + QA + designer/PM)

| Weeks | Milestone | Done means | Why in this order |
|---|---|---|---|
| 1–2 | **M0 Foundations + risk spike** | CI/CD, IaC, auth, tenancy model, device protocol spec v1. *Spike:* pair an Android stick and an Electron player and show one image. | The device side carries the most unknowns, so I want proof early, before CRUD screens. |
| 3–6 | **M1 One screen, offline** | Pairing, upload and transcode, playlists, manifest compiler v1, player download/cache/playback, heartbeat/status. | This is the core loop. Everything else is variations on it. |
| 7–10 | **M2 A fleet** | Folders, tags, bulk edit, push to screens, schedules engine and calendar UI, live/expire, split-screen zones. | Customers buy fleets. Schedules depend on the manifest compiler from M1. |
| 11–14 | **M3 Content apps** | Content-app framework (config schema + sandboxed web view + refresh policy + server-side OAuth) and the 8 content apps. | Content apps are what make signage feel alive. The framework has to exist before the long tail of apps. |
| 15–18 | **M4 Business** | Teams, built-in and custom roles, approval flow, invites, plans and entitlements (plan × device type), Stripe per-screen billing, OnHold, proof of play, screenshot/reload, offline alerts. | Billing comes after the product works, but before beta, because entitlements touch every module. |
| 19–22 | **M5 Hardening + beta** | Tizen and webOS shells, a 10k-device load test with simulated players, security review, onboarding flow, docs, 5 beta customers. | TV platforms reuse the core once it is stable. The load test needs real code to test. |
| 23–38 | **Phase 2** | Designer (about 12 weeks with 2 FE + 1 BE), data sources, operational schedule, SSO/audit/API, sub-accounts/white-label, BrightSign, content-app SDK + 30 content apps. | Designer is the largest single feature and doesn't block selling, so it comes after the MVP earns feedback. |

## 7. Estimate (engineer-weeks, with AI)

How I estimate:
- **Base** is what a senior engineer would need without AI help.
- **AI factor** is how much of that base remains when the team uses AI coding assistants (code generation, tests, refactors, docs). It is not one flat number:
  - **0.60–0.70:** CRUD screens, UI, content-app integrations and test scaffolding, where most of the code is predictable.
  - **0.80–0.85:** product logic that AI drafts well but a person must design and review (playlists, schedules, player core).
  - **0.90–1.00:** device quirks, billing and security, where time goes into testing on real hardware, reading vendor docs and checking correctness, not typing code.
- **Focus factor 0.8:** an engineer delivers about 4 days of feature work a week once meetings, reviews and support are counted. v1 of this plan left this out, which made the buffer look like 30% when it was not.

| Epic | Base | AI factor | With AI |
|---|---:|---:|---:|
| Platform foundations (CI/CD, IaC, auth + MFA, tenancy, observability) | 11 | 0.80 | 8.8 |
| Device protocol, pairing, gateway, heartbeat | 8 | 0.90 | 7.2 |
| Player core (renderer, timeline, schedule eval, cache, offline, transitions) | 16 | 0.85 | 13.6 |
| Player shells: Android 7 · Electron 4 · Tizen + webOS 8 | 19 | 0.95 | 18.1 |
| Media pipeline (upload, transcode, thumbnails, doc => pages) | 7 | 0.85 | 6.0 |
| CMS shell, design system, asset library UI, global search | 8 | 0.65 | 5.2 |
| Playlists (nested, sub-playlist schedule, tag rules, transitions) | 7 | 0.80 | 5.6 |
| Schedules engine + calendar UI | 8 | 0.85 | 6.8 |
| Manifest compiler, push to screens, bulk edit | 6 | 0.90 | 5.4 |
| Content-app framework + 8 content apps (incl. OAuth for Google Slides and Canva) | 11 | 0.70 | 7.7 |
| Split screen / zones | 4 | 0.85 | 3.4 |
| Teams, built-in + custom roles, invites | 6 | 0.75 | 4.5 |
| Content approval workflow | 3 | 0.80 | 2.4 |
| Billing and entitlements (Stripe, plan × device, trial => Free downgrade, OnHold) | 8 | 0.90 | 7.2 |
| Device ops (screenshot, reload, status dashboard, alerts) | 4 | 0.80 | 3.2 |
| Proof of play (ingest, report, CSV, plan-gated) | 4 | 0.80 | 3.2 |
| E2E test automation + simulated-player load harness | 4 | 0.60 | 2.4 |
| Security review and hardening | 2 | 1.00 | 2.0 |
| **Total MVP** | **136** | **0.83** | **113** |

What changed from v1 (116 engineer-weeks):
- **Added work I had missed:** content approval (3), custom roles and MFA (+3), CMS shell and design system (+2), E2E/load harness (4) and security (2).
- **Raised estimates:** Tizen/webOS store submission and signing (+2), Android kiosk/OTA (+1), billing for trial => Free downgrade (+2), and Canva instead of Clock/Countdown in the content apps (+1, because Canva needs OAuth).

**Capacity:** 7 engineers × 22 weeks × 0.8 focus = **123 engineer-weeks**.
- **With AI:** 113 needed, **~9% buffer**. That is thin, so the cut line is set in advance: if velocity at the end of M1 is below plan, Tizen/webOS move to Phase 2 (saves 8).
- **Without AI:** 136 needed, which is about 24 weeks for the same team. AI is what holds the 22-week date; it does not shrink the team.

**Phase 2**

| Epic | Base | AI factor | With AI |
|---|---:|---:|---:|
| Designer + template library | 36 | 0.75 | 27.0 |
| Data sources / repeaters (Sheets, Excel, API) | 8 | 0.75 | 6.0 |
| Operational schedule (HDMI-CEC / RS-232, native hooks) | 6 | 0.95 | 5.7 |
| Sync play and video wall | 8 | 0.95 | 7.6 |
| SAML SSO, audit log, API keys, webhooks | 8 | 0.75 | 6.0 |
| Sub-accounts, sub-account billing, white-label, custom domain | 6 | 0.85 | 5.1 |
| BrightSign shell | 4 | 0.95 | 3.8 |
| Content-app SDK + ~30 more content apps | 16 | 0.60 | 9.6 |
| Mobile admin app | 8 | 0.70 | 5.6 |
| **Total Phase 2** | **100** | **0.76** | **76** |

16 weeks × 7 × 0.8 = 90 engineer-weeks, so 76 leaves ~18% buffer. Phase 2 gets a higher AI saving than the MVP because more of it is UI and integrations.

**Assumptions:**
- The team is staffed from week 1 and every engineer already uses an AI coding assistant daily. There is no ramp-up on the tools.
- AI output goes through the same code review and tests as human code. Review time is already inside the factors.
- Product/UX decisions follow the existing product, so there is no discovery phase.
- QA has a device lab with 2 units of each shell platform.
- QA and the designer/PM are not counted in engineer-weeks.

If the team had 5 engineers, capacity drops to 88 engineer-weeks (5 × 22 × 0.8) against 113 needed, so cutting alone does not hold the date. I would move Tizen/webOS, content approval, custom roles and proof of play to Phase 2 and ship 4 content apps instead of 8. That saves about 17 engineer-weeks and puts the MVP at about 24 weeks instead of 22.

## 8. Risks

| Risk | Mitigation |
|---|---|
| TV platform quirks (codecs, storage limits, web view memory) | Spike in M0; device lab from week 3; nightly soak tests on real hardware |
| Clock drift breaks schedules | The player syncs time with the server and evaluates in the device's time zone; skew alarm in heartbeat |
| Content apps that need OAuth (Google, Canva, Microsoft) and token refresh on unattended screens | Tokens stay server side and are refreshed by a server-side proxy, so the player never holds refresh tokens |
| Fan-out when one playlist is used by 10k screens | Incremental manifest compile + CDN; devices fetch manifests, the gateway only sends a version number |
| Storage and egress costs | Content-addressed dedupe; transcode to sensible bitrates; delta downloads only |
| AI saving does not materialise (review load, wrong code in device or billing paths) | AI factors are per epic and conservative where correctness matters; re-measure velocity at end of M1 and cut Tizen/webOS to Phase 2 if below plan |
| Scope creep toward the 133 content apps | The content-app SDK in Phase 2 turns each one into configuration + a web bundle, not core work |

## 9. Questions I would ask OptiSigns before starting

1. What is the target segment for the clone's first release: small businesses on 1–10 screens, or multi-location chains?
2. Is reusing existing OptiSigns hardware and its device management in scope? It changes the Android shell work.
3. Are there contractual SLAs (for example, content-change latency or uptime) that the gateway design must meet?
