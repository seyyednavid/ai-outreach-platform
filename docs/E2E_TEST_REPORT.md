# End-to-end test report

Two runs against the **deployed** application, from a user's point of view, with every result observed live; nothing was simulated. Run 2 is the one recorded for the [demo video](https://github.com/seyyednavid/ai-outreach-platform/releases/tag/v1.0.0).

- [Run 2: 24 November 2026, Superdrug](#run-2-24-november-2026-superdrug)
- [Run 1: 24 November 2026, fictional lead](#run-1-24-november-2026-fictional-lead)

## Run 2: 24 November 2026, Superdrug

| | |
|---|---|
| Time | 14:00 to 15:50 UTC |
| Application version | Commit `c2c70a2` (images `c2c70a25943a`) |
| Browser | The maintainer's normal Chrome, signed in by the maintainer (app, Gmail, Google Cloud Console); the automation connected over the DevTools protocol and never handled credentials |
| Demo data | Seller *Clearpath Queue Systems (Demo)* with two products; lead **Superdrug** (`https://www.superdrug.com`, a real public company) with the demo contact email `pharmacy.ops.demo@example.com` |
| Pre-check | Before recording, the real Research agent was run locally with the same input: it identified Superdrug and cited superdrug.com and Wikipedia |

### Results

| Step | Result |
|---|---|
| Add a second product (SmartSign Digital Signage) | **Passed** |
| Add the Superdrug lead with its website | **Passed** |
| Product Matching agent | **Passed**: 200 in 3.2 s; chose *FlowGuide Virtual Queue* over SmartSign, confidence *medium*, `customer_need_verified: false` |
| Contact Discovery agent | **Passed**: 200 in 7.8 s; **5 named contacts** (Head of Pharmacy Operations South, Pharmacy Director, Pharmacy Superintendent, Chief Operating Officer, Trading Director), each with a source (Superdrug press releases and people pages, trade press), all *Needs review*. An earlier attempt in the same session found 4 |
| Generation (research → writer → reviewer) | **Passed**: 200 in 8.8 s; research about **Superdrug** (correct company) with 3 sourced findings; score 8.5/10, no flags |
| Improver agent | **Not triggered**: the draft passed its first review (`improvement_count: 0`) |
| Unsupported claim added by hand → *Check my edits with AI* | **Passed**: the Reviewer flagged the planted statistic *and* a sentence the AI had written ("…demonstrates a strong commitment to customer access and care"), with explanations |
| Approval while flagged | **Blocked**: "Approve email" not shown, "Approve anyway" disabled; the override was never used |
| Fix both sentences → check | The Reviewer flagged one more AI-written sentence as an inferred need ("Managing customer flow efficiently … is key to maintaining a positive experience") |
| Remove it → check | **Passed**: 200 in 2.7 s, score 8.8/10, no flags |
| Human approval | **Passed**: `human_approved: true` |
| Gmail draft from the app | **Passed**: confirmation "Create a Gmail draft addressed to pharmacy.ops.demo@example.com? It will not be sent.", 200, `status: created` |
| Draft visible in Gmail | **Passed**: opened in Gmail Drafts (search limited to the demo recipient), content identical to the approved email; not sent |
| Cloud Run, Logging, Monitoring | **Passed**: both services healthy; this run's POST/PUT requests in Logs Explorer with status 200 (AI re-checks 2.4–3.9 s, saves about 75 ms); the *Generate draft* request (`POST /api/v1/outreach/run`, 200 in 8.6 s) with three OpenAI Responses API calls inside it (research, writer, reviewer); uptime check passing from Virginia, Oregon and Belgium; both alert policies present |
| Owner Console (recorded 18:00 UTC, same day) | **Passed**: overview shows 3 drafts, 100% AI pass rate, 67% first time, average score 8.4, 3 Reviewer flags dropped by code, 0 approvals despite a failed review, $0.03 model cost; the runs list shows run #3 (score 8.8, passed, approved, 24,129 tokens) with trace links. Only one customer exists (the maintainer); its name is blurred, and run #1 (an existing record) is blurred |

### Findings

1. **Citation accuracy.** One research finding, "over 800 stores … including 200 in-store pharmacies", cites Superdrug's governance page, which does not state those figures. Wikipedia gives 796 locations (as of 2017) and pharmacies in over 220 shops, so the figures are roughly right but the citation is wrong. The video (version 3) marks this finding on screen as needing human verification instead of presenting it as checked. The other two findings match their sources (AS Watson's 17,000+ stores on the governance page; £1.6 billion revenue and £136.8 million pre-tax profit on Wikipedia).
2. **Reviewer consistency.** In an earlier take of the same safety test, the re-check passed after only the planted statistic was removed, without re-flagging the AI's own opinion sentence; in the recorded take it was flagged, and a third sentence was flagged after the fix. The Reviewer is strict but not fully deterministic (matching the evaluation's 28/30 consistency), which is why a person approves every email.
3. **Log noise.** The OpenAI SDK's HTTP client logs as `httpx2`, not `httpx`, so "HTTP Request: POST https://api.openai.com/…" INFO lines still reach Cloud Logging (58 in 4 hours; URLs and status codes only, no secrets). Adding `httpx2` to `QUIET_LOGGERS` in `app/core/logging_config.py` would fix it. The same lines show `POST /v1/traces/ingest → 204`, confirming that OpenAI trace export works in production.
4. **Confirmation dialog.** The Gmail confirmation is a native `confirm()` dialog. When the automation is attached to a real Chrome window, it was answered in the page (accepting only an `example.com` recipient and the "It will not be sent" wording).

### Screenshots

Application and Gmail: [product matching](assets/screenshots/demo-04-product-matching.png), [contact discovery](assets/screenshots/demo-05-contact-discovery.png), [research sources](assets/screenshots/demo-08-research-sources.png), [flagged claims](assets/screenshots/demo-09-flagged-claims.png), [approval blocked](assets/screenshots/demo-10-approval-blocked.png), [draft in Gmail](assets/screenshots/demo-13-draft-in-gmail.png). Google Cloud: [metrics](assets/screenshots/gcp-console-metrics.png), [the generation request and its OpenAI calls](assets/screenshots/gcp-console-logs-generate.png), [the run's POST/PUT requests](assets/screenshots/gcp-console-logs.png), [one structured entry](assets/screenshots/gcp-console-log-entry.png), [uptime check](assets/screenshots/gcp-console-uptime.png), [alert policies](assets/screenshots/gcp-console-alerts.png).

## Run 1: 24 November 2026, fictional lead

| |
|---|---|
| Date | 24 November 2026, 12:40 to 13:05 UTC |
| Application version | Commit `c2c70a2` (backend and frontend images `c2c70a25943a`) |
| Environment | Live demo on Google Cloud Run, `europe-west2`; Supabase (London) |
| Account | The maintainer's own account, signed in by the maintainer in a visible browser window; the automation never handled the password |
| Test data | New, fictional records labelled "(Demo)". Existing records were not edited or deleted, and are blurred in all media |
| Tooling | Python Playwright 1.58 with the system Chrome; screenshots and video recorded by Playwright |

### Summary

| Area | Result |
|---|---|
| Sign-in (Supabase Auth) | **Passed** |
| Dashboard | **Passed** |
| Create seller company with signature | **Passed** (after correcting a test-script field mistake; see notes) |
| Add product to the catalogue | **Passed** |
| Add lead | **Passed** |
| Product matching agent | **Passed**: 200 in 4.0 s, picked the demo product, marked "Fit unconfirmed" |
| Contact discovery agent | **Passed (no contacts)**: 200 in 4.5 s; 0 contacts for a fictional company, shown as "No suitable contacts were found. The email will use a neutral greeting." |
| Draft generation (research → write → review) | **Passed**: 200 in 7.4 s; 3 research findings with sources, score 8.5/10, no flags |
| Improver agent | **Not triggered**: the draft passed the first review, so the bounded improve loop correctly did not run (`improvement_count: 0`) |
| Human edit + "Check my edits with AI" | **Passed**: an added unsupported claim was flagged with its exact quote (200 in 8.2 s); the draft then failed the code checks |
| Override gate on a failed review | **Passed**: "Approve anyway" stayed disabled until "I have checked every flagged claim and the email is accurate" was ticked. It was not pressed |
| Re-check after removing the claim | **Passed**: 200 in 5.7 s, no flags, passed |
| Human approval | **Passed**: 200, `human_approved: true`, "Approved on … Editing the email removes the approval." |
| Gmail connection status | **Passed**: "Connected" (existing OAuth connection still valid) |
| Gmail draft creation | **Passed**: browser confirmation "Create a Gmail draft addressed to jordan.lee@example.com? It will not be sent.", then 200, `status: created`, Gmail draft id returned, "Draft created in Gmail" with a link to Gmail drafts |
| Gmail mailbox inspected directly | **Not verified independently**: the automation has no Gmail access; evidence is the Gmail API's response (draft id) shown by the app |
| Drafts history per lead | **Passed**: the run appears under the demo lead with score and status |
| Error handling seen by the user | **Passed** for the cases met: no contacts found, failed review, disabled actions with explanations |
| Registration | **Not tested**: would create another account and send a confirmation email |
| Sign out | **Not tested, deliberately**: the button calls Supabase `signOut()` with the default global scope, which would end the maintainer's sessions on all devices |
| OpenAI Traces dashboard | **Not captured**: needs a separate OpenAI dashboard login. Each run stores its trace id; traces are linked from the Owner Console |

### Agent workflow observed

1. **Product matching:** chose "FlowGuide Virtual Queue (Demo)" from the one-product catalogue and labelled it "Fit unconfirmed".
2. **Contact discovery:** three web searches ran (search limitations listed in the UI); no named person was found, which is the correct outcome for a company that does not exist.
3. **Generation:** research produced 3 findings with source links; the writer drafted the email; code added the signature from My Company; the reviewer scored it 8.5/10 (personalisation 8, clarity 9, relevance 8, call to action 9) with no flagged claims, so it passed on the first review.
4. **Human in the loop:** a sentence not supported by any evidence ("Our system cut waiting times by 80% across 200 UK pharmacies last year.") was added by hand. The reviewer flagged it and quoted it; code marked the edit as failed; approval required an explicit override. After the sentence was removed, the check passed and the draft was approved.
5. **Gmail:** a draft addressed to a fictional `example.com` address was created in the connected mailbox. Nothing was sent.

**What the AI recommended vs what the backend enforced:** the agents produced the research, email text, scores, flags and product choice. Code decided that the edited draft failed (a remaining flag), locked normal approval, required the override checkbox for "Approve anyway", added the signature, and allowed the Gmail draft only after approval.

### Findings

1. **Research can match a different company with a similar name.** The fictional lead "Northbridge Pharmacy Group (Demo)" had no website, and the research agent's web search returned real, unrelated pharmacies called "Northbridge" in Australia. The email then described that pharmacy's services; the reviewer did not flag it because the claims matched the research, although one reviewer suggestion noticed the target appeared to be in Australia. Adding the lead's website (an existing optional field) gives the agent an unambiguous target; making a website or location required for research, or asking the research agent to report low confidence in the entity match, would reduce this risk.
2. **Public sign-up is enabled.** Supabase reports `disable_signup: false` (email confirmation required). Every account uses the server's OpenAI key.
3. **Sign out is global.** `supabase.auth.signOut()` without a scope ends the user's sessions on all devices; `{ scope: "local" }` would end only the current one (the API client already uses `local` when a token is rejected).
4. **CI warning:** GitHub reports that `astral-sh/setup-uv@v6` runs on a deprecated Node.js 20 runtime.
5. **Windows console:** `scripts.evaluate_reviewer` fails while printing "✓" on a cp1252 console; setting `PYTHONIOENCODING=utf-8` avoids it. CI (Linux) is not affected.

### Test notes

- The first company save put the phone number into the description and doubled the default sign-off. This was a **test-script mistake** (a loose label match), not an application bug; the demo record was corrected through the app's Edit form.
- A short "Check my edits with AI" call was triggered by mistake once while the script's selector was being fixed (on the demo run only).
- Measured times are single observations from this run, not benchmarks.

### Demo records created

| Type | Name |
|---|---|
| Seller company | Clearpath Queue Systems (Demo), signature "Alex Morgan, Sales Manager", `alex.morgan@example.com`, +44 20 0000 0000 |
| Product | FlowGuide Virtual Queue (Demo) |
| Lead | Northbridge Pharmacy Group (Demo), Retail pharmacy, Head of Store Operations |
| Outreach run | Run 1 for that lead (#2 overall): approved |
| Gmail draft | To `jordan.lee@example.com`, not sent. Can be deleted from Gmail Drafts at any time |

### Related evidence

- CI run for `c2c70a2`: [CI #10](https://github.com/seyyednavid/ai-outreach-platform/actions/runs/45384986363) (backend, frontend, Docker: all passed; 193 tests)
- Deployment of `c2c70a2`: [Deploy #4](https://github.com/seyyednavid/ai-outreach-platform/actions/runs/45385376160) (all 15 steps passed in 2 min 43 s)
- Reviewer evaluation re-run the same day: 81% of planted problems caught, 0% false alarms, 28/30 cases consistent across 3 runs, $0.097
- Infrastructure, monitoring and logging evidence: [`docs/assets/screenshots/gcp-*.png`](assets/screenshots)
- Screenshots and the screen recording of this run are kept by the maintainer and not published; the published media come from Run 2
