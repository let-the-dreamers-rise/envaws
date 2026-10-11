# CleanHour — idea + research for Environmental Hacks (Air track)

> **One line:** An AI duty officer for Delhi schools that, before kids leave home, moves
> assembly and PE out of the toxic morning hours into the cleanest hour of the school day,
> checks every move against GRAP rules, and tells parents in Hindi on WhatsApp.
>
> **Tagline:** *Khelna band nahi, waqt badlo.* (Don't stop the play, change the time.)

---

## 1. Benchmark: what won the last event in this exact series

First Commit (Bharat Builds Tour, event 01, Sept 17–20, 2026; same organisers, same
AWS judging criteria): 13,667 participants, 4,270 teams, 1,180 submissions.

| Prize | Project | What it is | Stack depth |
|---|---|---|---|
| 1st, Ship It | **Suraksha** (StarBugs, 3 ppl) | Agentic companion for an aging parent. Hindi/Hinglish voice, fall detection from Galaxy Watch, *asks the parent first* before alerting family | Bedrock Nova 2 Lite agents + LLM judge, Cedar consent policies on every tool call, Step Functions `waitForTaskToken` escalation chain, EventBridge 1-min sweeps, DynamoDB single-table, Transcribe, Polly, Cognito, API GW, Lambda containers, Amplify, CDK. 35 commits |
| 2nd, Build It | **Beacon Night Shift** (solo) | On-call agent for 3 AM AWS outages; finds root cause, proposes one allowlisted fix, applies only after a spoken "approve fix 1", and verifies recovery. "Sleep contracts" let it auto-fix the same fault next time | Strands Agents SDK, Bedrock Nova 2 Lite + embeddings, Step Functions verify loop, CloudTrail/EventBridge, DynamoDB, SNS, Transcribe/Polly, Powertools, 244 tests |
| 3rd, Best UI | **CampusEvac** (3 ppl) | Two-player 3D fire-drill game: evacuee + warden, "neither can finish alone" | Next.js + React Three Fiber, AppSync Events realtime, DynamoDB, Polly, SES, CDK, Amplify |
| Runners-up | Magpie, FreshTrace, Expressive captions, Factcade | AI finance workspace, food traceability, caption voice agent, factory ops copilot | Mostly Bedrock + Lambda/Amplify |

**Patterns judges rewarded:**
1. **A named human in a specific moment.** "Amma", "the 3 AM page". Not "users".
2. **An agent that acts, not a dashboard.** The model writes the words; **code decides the actions**
   (allowlists, Cedar policies), with a **human approval step** before anything happens.
3. **One clever twist that makes it memorable:** sleep contracts, ask-the-parent-first, a co-op game.
4. **Built for someone who isn't holding the phone** (the parent, the half-asleep engineer).
5. **Vernacular + voice** (Hindi/Hinglish, Polly/Transcribe).
6. **Deep but purposeful AWS:** 8–14 services, plus AWS open source (Strands, Cedar, Powertools).
   Bedrock **Nova 2 Lite** shows up in both top-2 winners.
7. **Deployed and live**, with a link that works. Many submissions had one, so it's table stakes.

Caveat: that's one prior event and three winners. It's a strong signal but a small sample.

**What most teams in the Air track will build (avoid):** AQI dashboards, "chat with AQI" bots,
clean-route planners, stubble-fire maps, carbon calculators, personal exposure trackers.
They're all informative, and none of them changes a decision.

---

## 2. Market research

### The pain (Delhi, right now: Oct–Nov is stubble + inversion season)
- **5,556 schools, 44.9 lakh students in Delhi; 2,681 are government schools** (UDISE+ 2024-25).
- **29% of Delhi teens have asthma on spirometry, and 88% of them were never diagnosed**
  (Lung India 2021, 3,157 students). CPCB found **lung-function deficits in 43.5% of Delhi
  schoolchildren vs 25.7%** in a control city.
- **Nov 2025:** the Supreme Court called outdoor activity for schoolchildren "putting them in a
  gas chamber". CAQM then **suspended outdoor sports across NCR**, and DoE pushed classes up to 5 into hybrid
  mode under GRAP Stage III. The policy tool today is a **blunt city-wide ban**, which means
  weeks with no PE. Delhi teens already show **2x obesity**, the one risk factor most strongly
  tied to asthma in that same study.
- Schools run **assembly at ~7:30–8:00 AM and PE in early periods**, which is the worst hour of the day.

### The insight (verified with real data)

> **Update during the build: ground truth from CPCB stations.** The model figures below come from CAMS. We then
> checked them against measured 15-minute data from CPCB stations (Rohini DPCC, R K Puram DPCC; republished by
> OpenCity). The daily shape holds, and it's stronger: at Rohini, 15 Oct–30 Nov 2025, PM2.5 averaged **315 at 8 AM
> vs 167 at 1 PM**, and moving 8 AM PE to the cleanest school hour cut PM2.5 by **57% on the median day** (46–57%
> across two stations and two seasons). Across winter 2024-25 at Rohini (121 school days), moving PE rescued safe
> outdoor play on **45 days**; on 52 days nothing was safe. CAMS read **1.2–4× low** against the station, so
> the product bias-corrects the forecast hour by hour. The demo replay is now **6 Nov 2025, measured: 486 at 8 AM,
> 85 at 1 PM.**

Delhi PM2.5 has a strong daily cycle: the morning inversion traps smoke, and by midday the
boundary layer rises and dilutes it. Hourly PM2.5 for central Delhi, **15 Oct–30 Nov 2025**
(CAMS model via Open-Meteo, computed for this doc):

| Hour | 07:00 | 08:00 | 09:00 | 10:00 | 11:00 | 12:00 | 13:00 | 14:00 |
|---|---|---|---|---|---|---|---|---|
| PM2.5 µg/m³ | 123 | 117 | 102 | 85 | 70 | 61 | 57 | 55 |

- Moving an 8 AM outdoor slot to the cleanest hour inside school time (8–14h) cut PM2.5 by
  **52% on the median day** (47 days analysed).
- **33 of 47 days** had "Poor"-or-worse air (>90 µg/m³) at 8 AM.
- **21 Nov 2025** (the "gas chamber" week): **193 at 8 AM vs 89 at 2 PM (-54%)**.
  On 24 Nov it was 195 → 69 (**-65%**).
- Live forecast today (11 Oct 2026): Delhi is climbing from ~64 to ~109 µg/m³ by 13 Oct
  morning, with ~62 at 1 PM. The season is starting now, so the demo is timely.

**So the product isn't "cancel PE". It's "move PE".** Kids keep their exercise and get about half the dose.

### Existing solutions and the gap
| Who | What | Gap |
|---|---|---|
| SAFAR, Sameer, IQAir, AQI.in | City/station AQI numbers | Information, not a decision. Nobody owns "what does my school do at 7:30?" |
| Airveda, Prana Air | Indoor/outdoor sensors sold to elite private schools | Hardware ₹₹, staff still have to interpret it, nothing for the 2,681 govt schools |
| myAQI (US teen project) | Generic tips for principals | No timetable, no India rules, no parent comms |
| NRDC Ahmedabad school flag program, US EPA Air Quality Flag Program | Coloured flag → activity guidance | Manual, daily, same-for-the-whole-day colour; no scheduling |
| CAQM/GRAP orders | City-wide bans by stage | Blunt, late (often announced the evening before), all-or-nothing |

**Nobody does: forecast → per-school timetable change → rule check → parent notice in Hindi.**

### Who pays (entrepreneur view)
- **Free tier for government schools** (DoE / Samagra Shiksha / CSR). One DoE circular is the
  distribution channel to 2,681 schools.
- **Paid for private schools** (parent-facing assurance is a selling point for admissions).
- **Year-round retention:** the same engine runs **Heat mode** in April–June (move PE away from the
  WBGT peak). The input becomes temperature/humidity instead of PM2.5, and the product stops being seasonal.
- Zero hardware, so marginal cost per school is roughly one Lambda run and one LLM call a day.

---

## 3. The product: CleanHour

**User:** the school principal or duty teacher at 6:00 AM.
**Beneficiary who isn't holding the phone:** the kids, especially the "asthma watch" group.
**Second audience:** parents, via the class WhatsApp group the school already uses.

### Core loop (this is the spine; build this first)
1. **5:30 AM, EventBridge Scheduler fires** for each school.
2. **Forecast:** fetch hourly PM2.5/PM10 for the school's lat/long (Open-Meteo Air Quality API, free, no key).
3. **Optimizer (plain code, not the LLM):** for each outdoor activity (assembly, PE, games),
   find the cleanest slot that day, respecting the playground's capacity (say 2 classes per
   slot), PE-teacher clashes, and the period grid. Swap it with an indoor period of the same class.
4. **Rules (Cedar, AWS open source):** every proposed outdoor slot is checked.
   ```cedar
   // Regulatory: GRAP Stage III+ means no outdoor sports at all
   forbid(principal, action == Action::"ScheduleOutdoor", resource)
     when { context.grap_stage >= 3 };
   // High exertion only below Very Poor
   forbid(principal, action == Action::"ScheduleOutdoor", resource)
     when { resource.exertion == "high" && context.pm25 > 120 };
   // Asthma-watch kids stay in above Poor
   forbid(principal in Group::"asthma_watch", action == Action::"ScheduleOutdoor", resource)
     when { context.pm25 > 90 };
   permit(principal, action, resource);
   ```
   If no slot passes, the activity goes indoors (yoga in the hall, indoor PE).
5. **Agent (Strands Agents SDK + Bedrock Nova 2 Lite):** writes the principal's 3-line brief and
   the parent notice in **Hindi + English**, citing which rule caused each change. It also answers
   follow-ups such as *"Kya class 7 ka sports-day practice ho sakta hai?"* using the same tools.
   **The LLM never changes the schedule. Code and Cedar do.** (This is exactly what the winners did.)
6. **One-tap approve** by the principal (Step Functions `waitForTaskToken`). If the principal hasn't
   approved by 6:45 and the change is forced by a regulatory rule, it auto-applies and logs it.
7. **Broadcast:**
   - Hindi **voice note** (Amazon Polly, voice *Kajal*, hi-IN) for parents who don't read.
   - **"Share to WhatsApp" deep link** (`wa.me/?text=...`) prefilled with the notice and voice-note link.
     Indian schools already run on class WhatsApp groups. This also avoids SMS DLT registration.
   - **Public school page** showing a big colour flag plus "Today: PE for 6B moved 8:00 → 13:20", for
     parents and the gate display.

### The twists that make it memorable
- **"Don't cancel, move."** The same school on the same day gets half the dose and keeps PE. Everyone else is building alerts.
- **Asthma watch:** parents opt their child in, and that child gets stricter rules. It speaks to the 88% undiagnosed figure.
- **Evening preview at 8 PM:** "Tomorrow: assembly indoors, carry PE shoes for 1 PM", so parents know before the morning.

---

## 4. AWS architecture

```
EventBridge Scheduler (5:30 AM, 8 PM) ─▶ Step Functions "DailyPlan"
   ├─ Lambda: fetch forecast (Open-Meteo) ─────────────┐
   ├─ Lambda: optimizer + Cedar check (cedarpy) ───────┤──▶ DynamoDB (schools, timetables,
   ├─ Lambda: Strands agent → Bedrock Nova 2 Lite ─────┤     plans, approvals, audit)
   │     (brief + Hindi/English notice)                │
   ├─ Wait for principal (waitForTaskToken) ◀── API Gateway ◀── Amplify web app (principal console)
   └─ Lambda: Polly (hi-IN Kajal) → S3 voice note; publish plan ─▶ public school page + WhatsApp link
CloudWatch: logs/metrics for every run
```

**AWS services:** Amplify Hosting, API Gateway (HTTP API), Lambda, Step Functions, EventBridge
Scheduler, DynamoDB, Bedrock (Nova 2 Lite), Polly, S3, CloudWatch (plus Cognito if time allows).
**AWS open source:** Strands Agents SDK, Cedar. Both count toward the "Built on AWS" criterion.

**Data:** Open-Meteo Air Quality API (CAMS forecast, hourly, no key). GRAP stage has no API, so
it's an admin toggle in the console (be honest about this in the video). Stretch: CPCB station
now-cast via the data.gov.in API (free key) to correct the forecast in the morning.

---

## 5. Build plan for the time left (~8 h)

Check the exact deadline on the event page first. The schedule page says submission is Sun Oct 11
and the clock time is "being finalised".

| Time | Do | Done when |
|---|---|---|
| 0:00–0:30 | AWS account, enable Bedrock Nova 2 Lite model access (us-east-1), repo skeleton, Amplify app | `hello` deploys |
| 0:30–2:00 | **Optimizer + Cedar** in Python. Seed one *fictional* school (e.g. "Demo Sarvodaya Vidyalaya, Rohini") with a 6-period timetable for 6 classes. Test on **21 Nov 2025 replay** and **tomorrow's live forecast** | Prints before/after timetable + rule reasons |
| 2:00–3:30 | Strands agent tools (`get_forecast`, `get_timetable`, `propose_plan`, `check_rules`, `write_notice`) on Bedrock; Polly Hindi voice note to S3; DynamoDB writes | Lambda returns plan + Hindi notice + mp3 URL |
| 3:30–5:00 | **UI:** hourly PM2.5 colour strip, before/after timetable, Approve button, notice preview, Play voice note, Share-to-WhatsApp; public parent page with the flag | Clickable end to end |
| 5:00–5:45 | EventBridge schedule, Step Functions approval wait, deploy everything | Live URL works signed-out |
| 5:45–6:30 | Bug fixes. **Code freeze** | |
| 6:30–7:30 | Record the video, write the README/writeup (list AI tools used), submit | Submitted with 30 min buffer |

**Cut line:** if you're behind at 3:30, drop Step Functions (use a plain API approve) and the evening
preview. **Never cut:** forecast → optimizer → Cedar → Hindi notice → approve → parent page.
"One feature that runs beats five that almost do."

---

## 6. Three-minute video script

- **0:00–0:20, hook.** "21 November 2025. The Supreme Court says outdoor activity is putting Delhi's
  children in a gas chamber. That morning at 8 AM, assembly time, PM2.5 was 193. At 2 PM it was 89.
  Same school, same day, half the dose."
- **0:20–0:40, problem.** The 6 AM principal. 44.9 lakh kids. 29% of Delhi teens are asthmatic, and 88%
  don't know it. Today's answer is a blanket ban, which means weeks with no PE.
- **0:40–1:50, demo.** Trigger the 5:30 run → hourly strip → the agent moves 6B's PE 8:00 → 13:20,
  takes assembly indoors, and keeps the asthma-watch kids in, with each Cedar rule cited. Ask in Hindi
  "Class 7 practice ho sakti hai?" and get the answer. **Approve** → Hindi voice note plays → WhatsApp share →
  parent page goes orange. Flip GRAP to Stage III and show Cedar forcing everything indoors.
- **1:50–2:30, AWS.** Architecture slide, then show it live in the console: Step Functions graph,
  Lambda logs, DynamoDB items, Bedrock, Polly. (The rules require the video to *show* AWS.)
- **2:30–3:00, impact.** "52% less PM2.5 per outdoor hour across last season, without cancelling one
  PE class. Zero hardware. 5,556 Delhi schools. Heat mode next summer."

---

## 7. Honest risks
- **The forecast is a coarse CAMS model.** It underestimates absolute peaks (CPCB stations read higher)
  but captures the daily *shape* well. Pitch the **relative** reduction, not absolute numbers.
- **Applying 24-h NAQI bands to hourly values is an approximation.** Say so in the writeup.
- **GRAP class ranges change order to order.** That's why they're editable Cedar policies, not hardcoded rules.
- **Bedrock model access** can take minutes to enable, so do it first. Fallback: Claude Haiku on Bedrock.
- Use a **fictional school** in the demo, not a real one.

---

## 8. Bonus points you shouldn't leave on the table
- **Blog prize (AirPods, top 5):** publish a write-up on AWS Builder Center. "What fought back" plus the
  52% chart. Few teams bother.
- **Fast-track interview:** make sure your Builder Center profile has verified student enrollment.
- The commit history must fall within the event dates. This repo started today, so you're fine.

---

## Sources
- First Commit winners: https://www.wemakedevs.org/aws/first-commit/projects
- First Commit recap: https://www.wemakedevs.org/blogs/first-commit-hackathon-recap-and-whats-next
- Suraksha repo: https://github.com/harshendram/firstcommit-hack
- Beacon repo: https://github.com/Prashant-thakur77/Beacon
- CampusEvac repo: https://github.com/AfreenInnovates/campus
- Rules: https://www.wemakedevs.org/aws/env/rules · Schedule: https://www.wemakedevs.org/aws/env/schedule
- Delhi schools (UDISE+ 2024-25): https://news.careers360.com/delhi-student-surge-school-capacity-gap-udise-report-2024-25-classrooms-expansion-plan-2026
- Asthma in Delhi teens (Lung India 2021): https://doaj.org/article/d2d68bb526d44776a6edb24fe572ed9a
- CPCB children lung function study: https://www.cpcb.nic.in/uploads/healthreports/Study-Air-Quality-health-effects_Children-2012.pdf
- SC "gas chamber" / outdoor activity halt (Nov 2025): https://www.businesstoday.in/amp/india/story/delhi-air-pollution-schools-ordered-to-halt-outdoor-activities-after-supreme-court-order-503139-2025-11-21
- CAQM stops outdoor sports: https://madhyamamonline.com/amp/india/severe-air-pollution-caqm-asks-delhi-ncr-states-stop-outdoor-sports-1476930
- GRAP Stage III hybrid up to class 5: https://www.tribuneindia.com/news/delhi/hybrid-mode-for-students-till-class-5-in-gurugram-schools
- Morning PM2.5 peak in Indian megacities (EGU22): https://meetingorganizer.copernicus.org/EGU22/EGU22-9142.html
- US EPA Air Quality Flag Program: https://archive.epa.gov/apti/video/web/pdf/flagprogram.pdf
- NRDC Ahmedabad school flag program: https://www.nrdc.org/bio/nehmat-kaur/new-air-quality-flag-program-schools-ahmedabad
- Airveda in Delhi schools: https://community.nasscom.in/communities/emerging-tech/iot-ai/in-the-spotlight-airveda-shortlisted-by-gmda-to-set-up-air-quality-monitors-in-gurugram.html
- myAQI: https://www.globalindian.com/youth/rohan-varinakaval-indian-american-teen-finds-solution-for-schools-amid-air-quality-crisis/
- Data: Open-Meteo Air Quality API (CAMS): https://open-meteo.com/en/docs/air-quality-api
