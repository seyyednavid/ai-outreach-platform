# Demo script

The script for the portfolio [demo video](https://github.com/seyyednavid/ai-outreach-platform/releases/tag/v1.0.0) (4 min 24 s, 1920 × 1080, narrated in British English, with captions). Every application, Gmail, GitHub and Google Cloud shot is a real screen recording made on 24 November 2026 against the live deployment; results and timings are in the [E2E test report](E2E_TEST_REPORT.md#run-2-24-november-2026-superdrug). The narration column below is a full transcript.

## Scenario

| Record | Value |
|---|---|
| Seller (fictional) | Clearpath Queue Systems (Demo), products *FlowGuide Virtual Queue (Demo)* and *SmartSign Digital Signage (Demo)*, signature "Alex Morgan" with `example.com` contact details |
| Lead (real public company) | Superdrug, `https://www.superdrug.com`, Health and beauty retail, role *Head of Pharmacy Operations*, possible need *queues at in-store pharmacy counters* (treated as unconfirmed), contact email `pharmacy.ops.demo@example.com` |
| Why Superdrug | A real website and public business information, so the Research agent can identify the right company. A local pre-check of the Research agent confirmed this before recording |

## Timeline and narration

The narration column is the exact voice-over in the video. Each line starts within half a second of its scene (checked by transcribing the exported video locally).

| Time | On screen | Caption | Narration |
|---|---|---|---|
| 0:00–0:09 | Title card | AI Outreach Platform | "AI Outreach Platform. Agents research a company and draft a B2B email. Code enforces the rules, and a person approves every email." |
| 0:09–0:15 | Sign-in page (no credentials entered on camera) | Sign in | "Sign-in uses Supabase Auth, and the backend verifies the token on every request." |
| 0:14–0:19 | Dashboard | Dashboard | "The dashboard shows leads, drafts, approvals and the average review score." |
| 0:19–0:28 | My Company → *Add product* → SmartSign (Demo) | My Company · 1.8× | "We add a second product. The AI may only describe products listed here, so matching has a real choice." |
| 0:27–0:35 | Leads → *Add lead*: Superdrug with its website | New lead · 2× | "The lead is Superdrug, a real company, with its website, so research finds the right business." |
| 0:35–0:39 | New draft: choose lead and seller | New draft | "On New draft, we choose the lead and our company." |
| 0:39–0:48 | *Find best product* | Product Matching agent | "The matching agent picks FlowGuide over SmartSign, with medium confidence, and marks the need as unconfirmed." |
| 0:48–0:55 | *Find contacts* (searching) | Contact Discovery agent · 1.1× | "Contact discovery runs three web searches in parallel. Python merges, ranks and source-checks the results." |
| 0:55–1:02 | Five contacts with sources (names blurred) | Contact Discovery agent | "Five named people, each with a source, all marked as needing review. Names are blurred here." |
| 1:01–1:11 | *Generate draft* → Drafts | Research → Writer → Reviewer · 1.5× | "Generate runs research, the writer and the reviewer in about nine seconds. The improver only runs if a review fails, and this draft passed first time." |
| 1:11–1:15 | AI review | Reviewer agent | "The reviewer scored it 8.5 out of 10, with no flagged claims." |
| 1:15–1:20 | Email draft | Writer agent · 1.5× | "The email. The signature is added by code, not by the model." |
| 1:19–1:24 | What the AI was given → Research on Superdrug | Research agent | "And the research behind it, with a source for every finding." |
| 1:24–1:33 | Zoom on the first finding, outlined: *Needs human verification* | Research · source check | "But this store and pharmacy figure isn't on the page it cites. Wikipedia's numbers are close, which is exactly why a person checks the sources." |
| 1:33–1:35 | Card | Safety check | "Now, the guardrails." |
| 1:35–1:40 | *Edit*: type “We have already cut pharmacy waiting times by 80% in 300 UK pharmacies.” | Human edit · 2× | "We add a statistic that nobody can support," |
| 1:39–1:43 | *Save changes* → *Check my edits with AI* | Check my edits with AI · 1.7× | "and ask the AI to check the edit." |
| 1:42–1:49 | Two flagged sentences, each quoted | Reviewer flags 2 sentences | "The reviewer flags our statistic, and also an opinion the AI wrote itself." |
| 1:48–1:54 | Approval area | Approval blocked | "Normal approval disappears, and the override stays locked. We won't use it." |
| 1:54–2:03 | Remove the statistic; replace the opinion with “Superdrug runs in-store pharmacies in over 200 of its stores.” → check | Human fixes both · 2.4× | "We remove the statistic, and replace the opinion with a fact Wikipedia supports. The re-check then flags one more sentence." |
| 2:02–2:08 | The new flag; still blocked | Still blocked · 1.8× | "Every flag has to be resolved. This sentence assumes a need nobody has confirmed." |
| 2:08–2:14 | Remove that sentence → check → passed | Remove it, check again · 2.4× | "We remove it and check again. It passes, at 8.8, with no flags." |
| 2:14–2:20 | Tick *I have read this email* → *Approve email* | Human approval · 1.4× | "Now we can confirm and approve. Editing the email later removes the approval." |
| 2:20–2:28 | *Create Gmail draft* (confirmation: “It will not be sent”) | Save to Gmail · 1.3× | "Only an approved email can be saved to Gmail, and only as a draft. The app confirms it will not be sent." |
| 2:28–2:37 | Gmail → Drafts search → open the draft | In Gmail | "Here it is in Gmail Drafts, exactly as approved. Nothing was sent." |
| 2:36–2:42 | Owner Console overview | Owner Console | "The owner console shows pass rate, scores and model cost across all customers." |
| 2:41–2:49 | Zoom on *Guardrails and people* | Owner Console · guardrails | "And where guardrails acted: three reviewer flags dropped by code, and no approvals despite a failed review." |
| 2:48–2:56 | Owner Console → Runs (run #1, an existing record, blurred) | Owner Console · runs | "Each run has its score, approval, cost, and a link to its OpenAI trace." |
| 2:55–2:58 | Card | How it runs | "Under the hood." |
| 2:57–3:06 | Runtime architecture diagram | Architecture | "React and FastAPI run on Cloud Run, with Supabase for login and Postgres. Only the backend talks to OpenAI and Gmail." |
| 3:06–3:13 | GitHub Actions CI run | CI · 1.5× | "Every push runs Ruff, 193 tests, ESLint and Docker builds in GitHub Actions." |
| 3:12–3:21 | Deploy job steps | CD · 1.4× | "Deploy signs in with Workload Identity Federation, with no stored keys, and updates Cloud Run." |
| 3:20–3:25 | Card | Monitoring & logging | "Finally, monitoring. Is it healthy, and what happened during this demo?" |
| 3:25–3:31 | Cloud Run services | Cloud Run | "Both Cloud Run services, the backend and the frontend, are healthy." |
| 3:31–3:40 | Backend metrics: request count and latencies (last day) | Cloud Run metrics | "The backend's metrics show requests by status, and latency, over the last day. Today's demo runs are the spikes after midday." |
| 3:40–3:54 | Logs Explorer: the *Generate draft* request and three OpenAI calls → expand the request | Cloud Logging · Generate draft | "In Cloud Logging, the Generate click is one request taking 8.6 seconds, with three OpenAI calls inside it: research, writing and review." |
| 3:53–4:00 | Logs Explorer: edits, AI re-checks, approval, Gmail draft | Cloud Logging · human in the loop | "Then the edit checks, the approval and the Gmail draft, each with its status and latency." |
| 4:00–4:07 | Expand one AI re-check as structured JSON | Structured log entry · 1.8× | "Each entry is structured, so a failure can be traced to a single request." |
| 4:06–4:13 | Uptime check detail: current status by region | Uptime check | "An uptime check calls the readiness endpoint every five minutes. It's passing in North America and Europe." |
| 4:13–4:20 | Alert policies | Alert policies | "And two alert policies send an email if the backend is down or returns server errors." |
| 4:19–4:24 | End card | github.com/seyyednavid/ai-outreach-platform | "The code and documentation are on GitHub. Thanks for watching." |

Times overlap by 0.4 s where scenes crossfade. Speed-ups (1.1× to 2.4×) apply only to waiting and typing, and every one is labelled in the caption.

## Hidden or anonymised in the recording

- **Real people found by contact discovery:** names, relevance reasons and source quotes are blurred; job titles, sources and statuses are shown.
- **Personal data:** the account's email address and avatar, Gmail mailbox counts and other mailbox content (a Drafts search limited to the demo recipient), the Gmail draft id, the client IP address in log entries.
- **Google Cloud:** project id and number, service URLs (the host part of each request URL; the path stays visible), "last modified by", the account avatar, and the free-trial billing banner.
- **Existing records** in the account (another company, lead and run, including run #1 in the Owner Console) are blurred wherever they appear. The Owner Console's only customer is the maintainer's own organisation, whose name (an email address) is blurred.

## Research citation

One research finding, "Superdrug operates over 800 stores … including 200 in-store pharmacies", cites a Superdrug page that does not contain those figures. The video does not present it as verified: the finding is outlined and labelled *Needs human verification: these figures are not on the cited page*, and the caption quotes Wikipedia ("nearly nine hundred shops"; pharmacies "in over 220 shops"). The footage and the app's evidence are not altered. The sentence typed during the safety check, "Superdrug runs in-store pharmacies in over 200 of its stores", is supported by Wikipedia's "over 220".

## Production notes

- Recorded from a normal Chrome window over the DevTools protocol (page content only, no browser UI or desktop), 1280 × 720 CSS pixels at 125 % scale, then assembled with ffmpeg at 1920 × 1080, 30 fps, H.264, AAC 48 kHz mono, loudness normalised to −16 LUFS.
- **Voice:** generated locally with [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) (Apache-2.0 weights, run offline with `kokoro-onnx`), British English voice `bf_emma`, speed 1.0; the script never left the machine. No background music.
- Zooms and crops are applied to recorded frames; no screen is staged or generated. The highlight box on the research finding is the only drawn overlay.
- The browser's "Create a Gmail draft … It will not be sent" confirmation is a native dialog that screen capture does not show; it was accepted only for the `example.com` recipient.
- The Cloud Console recordings are read-only: navigation, expanding log entries and choosing a time range. No alert, failure or configuration change was triggered.
