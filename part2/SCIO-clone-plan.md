# SCIO Clone — Build Plan

**Author:** Hoang Tran · **Date:** 2026-10-14 · **Status:** v1, for discussion

## 1. Summary

- **What:** A multi-tenant digital-signage CMS plus a player runtime. Customers pair screens, upload content, arrange it into playlists, split screens and schedules, push it to a fleet, and see what is playing. Playback keeps working when the network goes down.
- **MVP, 22 weeks:** CMS, players for Android, Windows/macOS/Linux, Samsung Tizen and LG webOS, 8 apps, schedules, teams, per-screen billing and proof of play. This is enough to sell to a small or mid-size business with 5–500 screens.
- **Phase 2, about 20 more weeks:** Designer (a Canva-style editor), data sources, SSO, sub-accounts and white-label, a public API, and more apps.
- **Team:** 7 engineers, 1 QA engineer, 1 product designer/PM. This size gets the MVP out in under six months without coordination costs taking over.
- **Biggest bet:** one TypeScript player runtime wrapped in thin native shells. Eight of the 14 platforms OptiSigns supports run HTML5, so one renderer covers most of the market.

## 2. What I learned from the product

I used a Pro Plus trial (app.optisigns.com) and read the help center end to end: I scraped all 414 articles for Part 1 of this test.

| Area | What it actually is |
|---|---|
| **Screens** | Pair with a 6-digit code. Each screen has tags, folders, location, orientation (0/90/180/270), scale mode, background and mute. One of three things is bound to it: an **asset, a playlist or a schedule**. A separate **operational schedule** powers the TV on/off through HDMI-CEC or RS-232. An **OnHold** folder frees a licence without deleting the screen. Status is sent every 30 s, and a screen is marked offline after 10 min of silence. |
| **Players** | 14 platforms: Windows, macOS, Linux, Android, Fire OS, Amazon Signage, Apple TV, iOS, ChromeOS, Samsung Tizen/SSSP, LG webOS, BrightSign, Roku, Raspberry Pi. OptiSigns also sells its own hardware (OptiStick, Pro, ProMax) with built-in device management, which enables reboot, screenshot, Wi-Fi, time zone and bulk commands. |
| **Files/Assets** | Images, video and documents (up to 25 MB per file and 1 GB storage on Free), folders, sharing, favourites, trash. **About 150 "apps"** are configured web content: YouTube, Weather, Power BI, Tableau, Google Slides, RSS, Teams Rooms, Salesforce, Grafana, Website, Split Screen and more. |
| **Playlists** | Ordered items, each with a duration, plus transitions, shuffle and per-type scaling. Advanced settings add **content-tag rules** (different screens play different items from the same playlist), **nested sub-playlists with their own schedule**, resume-on-next-play, max duration and background music. The UI shows total size and runtime. |
| **Schedules** | A calendar of events with daily, weekly, monthly or custom recurrence and time-zone handling. When events overlap, the last-updated one wins. Items have live/expire dates. |
| **Designer / Templates** | A full canvas editor: text, shapes, frames, filters, animation, layers and version history. Its **widgets embed a Playlist, Apps, Video, Weather, Time and Date**, and **repeaters** bind to data. There is a template library and an "AI Designer". |
| **Engage** | Touch kiosks, QR overlays, lift-and-learn with IoT sensors, AI camera and check-in. It is a separate plan, with a 1-device trial on other plans. |
| **Analytics** | Proof of Play is opt-in per device, because it "slightly increase[s] network usage". There is also AI Analytics. |
| **Account** | Teams with screen quotas, roles (Owner/Super Admin/Admin/User), sub-account billing, branding and custom domain, audit log, monitoring alerts, SAML SSO, API keys, integrations, share links, data sources and tags. |
| **Commercial** | Licences are sold per screen. Plans are Free (3 screens), Standard, Pro Plus, Engage and Enterprise, plus add-ons: Video Wall, OptiSound, AeriCast, Engage, and Custom Domain at $10/mo. **Entitlements depend on the plan *and* the device type**: the Free plan only runs on OptiSigns hardware and desktop operating systems. |

## 3. The one thing I did not expect, and what it changed

**The content model is a tree, not a list.**

I walked in expecting *screen → playlist → files*. What I found:

- A **Designer** layout can contain a **Playlist widget**.
- That playlist can contain **Designer assets**, **apps** and **sub-playlists that carry their own schedule**.
- A **Split Screen** puts a different playlist in each zone.
- A **schedule** picks which of these trees is live.
- **Content-tag rules** then filter the tree per screen.

So what a screen shows at any moment is the result of evaluating a recursive tree, with *(time, screen tags, time zone)* as inputs.

This changed the plan in three ways:

1. **One polymorphic `ContentNode` model** (asset | app | playlist | layout | schedule) instead of separate tables wired together ad hoc. The server compiles each screen's tree into a versioned, flattened **device manifest**: every media URL with a hash, plus the time rules. It rejects cycles at save time. The player never queries the CMS; it only reads manifests.
2. **The player renderer is a recursive zone/timeline evaluator from week 3**, not a slideshow. When Designer arrives in Phase 2 it becomes one more node type, not a player rewrite. Without this, I would have budgeted for a player rework around month 7.
3. **Split Screen moved into the MVP.** Once zones exist in the renderer, it costs about 4 engineer-weeks, and it is the most common "advanced" layout customers ask for.

## 4. Scope

**MVP (in):**
- Accounts, teams and roles.
- Pairing.
- Screen management: folders, tags, bulk edit, orientation, scale.
- Asset library: upload, transcode, thumbnails, PDF/PPTX → pages.
- Playlists: nested, transitions, tag rules.
- Schedules: recurrence, time zones, overlap priority, live/expire.
- Split screen.
- Push to screens.
- Offline playback.
- Status/heartbeat, remote screenshot and reload.
- Proof of play (basic report + CSV).
- Per-screen Stripe billing with plan entitlements and OnHold.
- 8 apps: Website, YouTube, Weather, RSS/News, Clock/Countdown, Google Slides, QR Code, Embed/HTML.

**Phase 2:**
- Designer and templates.
- Data sources / repeaters.
- Operational schedule (CEC/RS-232; needs native hooks).
- Sync play and video wall.
- SAML SSO, audit log, API keys, webhooks.
- Sub-accounts, white-label and custom domain.
- An app SDK and about 30 more apps (Power BI, Teams Rooms, Google Calendar…).
- Mobile admin app.

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
  - **Cache**: content-addressed by hash, so updates download only the delta. Downloaded media plays offline indefinitely; live web apps are skipped while offline, which matches OptiSigns' behaviour.

## 6. Sequence and timeline (team of 7 engineers + QA + designer/PM)

| Weeks | Milestone | Done means | Why in this order |
|---|---|---|---|
| 1–2 | **M0 Foundations + risk spike** | CI/CD, IaC, auth, tenancy model, device protocol spec v1. *Spike:* pair an Android stick and an Electron app and show one image. | The device side carries the most unknowns, so I want proof early, before CRUD screens. |
| 3–6 | **M1 One screen, offline** | Pairing, upload and transcode, playlists, manifest compiler v1, player download/cache/playback, heartbeat/status. | This is the core loop. Everything else is variations on it. |
| 7–10 | **M2 A fleet** | Folders, tags, bulk edit, push to screens, schedules engine and calendar UI, live/expire, split-screen zones. | Customers buy fleets. Schedules depend on the manifest compiler from M1. |
| 11–14 | **M3 Apps** | App framework (config schema + sandboxed web view + refresh policy) and the 8 apps. | Apps are what make signage feel alive. The framework has to exist before the long tail of apps. |
| 15–18 | **M4 Business** | Teams/roles/invites, plans and entitlements (plan × device type), Stripe per-screen billing, OnHold, proof of play, screenshot/reload, offline alerts. | Billing comes after the product works, but before beta, because entitlements touch every module. |
| 19–22 | **M5 Hardening + beta** | Tizen and webOS shells, a 10k-device load test with simulated players, security review, onboarding flow, docs, 5 beta customers. | TV platforms reuse the core once it is stable. The load test needs real code to test. |
| 23–42 | **Phase 2** | Designer (about 12 weeks with 2 FE + 1 BE), data sources, operational schedule, SSO/audit/API, sub-accounts/white-label, BrightSign, app SDK + 30 apps. | Designer is the largest single feature and doesn't block selling, so it comes after the MVP earns feedback. |

## 7. Estimate (engineer-weeks)

| Epic | Eng-wks |
|---|---|
| Platform foundations (CI/CD, IaC, auth, tenancy, observability) | 10 |
| Device protocol, pairing, gateway, heartbeat | 8 |
| Player core (renderer, timeline, schedule eval, cache, offline, transitions) | 16 |
| Player shells: Android 6 · Electron 4 · Tizen + webOS 6 | 16 |
| Media pipeline (upload, transcode, thumbnails, doc → pages) | 7 |
| Asset library UI (folders, search, share, trash) | 6 |
| Playlists (nested, tag rules, transitions) | 7 |
| Schedules engine + calendar UI | 8 |
| Manifest compiler, push to screens, bulk edit | 6 |
| App framework + 8 apps | 10 |
| Split screen / zones | 4 |
| Teams, roles, invites | 4 |
| Billing and entitlements (Stripe, plan × device, OnHold) | 6 |
| Device ops (screenshot, reload, status dashboard, alerts) | 4 |
| Proof of play (ingest, report, CSV) | 4 |
| **Total** | **116** |

Capacity is 7 engineers × 22 weeks = **154 eng-weeks**. That leaves a **~30% buffer** over 116 for integration, device quirks and onboarding. I size each epic as a 1–2 person team for N weeks, which is how I would staff it.

Assumptions:
- The team is staffed from week 1.
- Product/UX decisions follow the existing product, so there is no discovery phase.
- QA has a device lab: 2 of each shell platform.

If the team had 5 engineers, I would cut Tizen/webOS and the apps down to 4, rather than stretch the date.

## 8. Risks

| Risk | Mitigation |
|---|---|
| TV platform quirks (codecs, storage limits, web view memory) | Spike in M0; device lab from week 3; nightly soak tests on real hardware |
| Clock drift breaks schedules | The player syncs time with the server and evaluates in the device's time zone; skew alarm in heartbeat |
| Apps that need OAuth (Google, Microsoft) and token refresh on unattended screens | Tokens stay server side and are refreshed by a server-side proxy, so the player never holds refresh tokens |
| Fan-out when one playlist is used by 10k screens | Incremental manifest compile + CDN; devices fetch manifests, the gateway only sends a version number |
| Storage and egress costs | Content-addressed dedupe; transcode to sensible bitrates; delta downloads only |
| Scope creep toward the ~150 apps | The app SDK in Phase 2 turns apps into configuration + a web bundle, not core work |

## 9. Questions I would ask OptiSigns before starting

1. What is the target segment for the clone's first release: small businesses on 1–10 screens, or multi-location chains?
2. Is reusing existing OptiSigns hardware and its device management in scope? It changes the Android shell work.
3. Are there contractual SLAs (for example, content-change latency or uptime) that the gateway design must meet?
