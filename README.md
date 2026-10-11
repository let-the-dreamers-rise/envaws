# CleanHour

**Don't cancel play. Move it to the clean hour.**

CleanHour is an AI duty officer for Indian schools. At 5:30 AM it reads the air and heat forecast for the
school's location, moves outdoor periods (assembly, PE, recess) into the safest hour of the day, checks every
move against GRAP rules and the school's own policies, emails the principal for one-tap approval, and tells
parents in Hindi on WhatsApp, with a voice note, before the school bus leaves.

Track: **Air** (with a heat mode that also covers Heat & Water) · Environmental Hacks, Bharat Builds Tour 2026.

- Live site: `<add after deploy>` · Principal console: `<site>/console.html?date=2025-11-06`
- Demo video: `<add YouTube link>`
- Research and benchmark: [docs/idea-and-research.md](docs/idea-and-research.md) · Design: [docs/design.md](docs/design.md)

## The problem

- Delhi has **5,556 schools and 44.9 lakh students** (UDISE+ 2024-25). **29% of Delhi teens show asthma on
  spirometry and 88% of them were never diagnosed** (Lung India, 2021).
- Smog-season mornings are the worst hour of the day. A cold inversion traps pollution until the midday
  mixing layer lifts it. **Measured at the CPCB Rohini station, 15 Oct–30 Nov 2025: PM2.5 averaged 315 µg/m³ at
  8 AM vs 167 at 1 PM.** Moving an 8 AM outdoor slot to the cleanest school hour cut PM2.5 by **57% on the median
  day** (46–57% across Rohini and R K Puram, 2024 and 2025 seasons; our analysis of CPCB data).
- Across winter 2024-25 at Rohini (121 school days), 8 AM air was unsafe for PE on 97 days. Moving PE to a later
  slot made it safe on **45 of those days**. On the other 52 nothing was safe, and CleanHour keeps children in.
- Schools hold assembly and PE at 7:45–9:30 AM. The only policy tool is a **blanket, city-wide ban**
  (Nov 2025: CAQM suspended outdoor school sports across NCR), which costs children weeks of exercise.

## What it does

| Step | What happens | Built with |
|---|---|---|
| 5:30 AM | EventBridge Scheduler starts the `DailyPlan` Step Functions workflow for each school | EventBridge Scheduler, Step Functions |
| Forecast | Hourly PM2.5/PM10 + feels-like temperature for the school's coordinates, **bias-corrected hour by hour to the nearest CPCB station** (the model reads 1.2–4× low in Delhi's smog season) | Open-Meteo (CAMS), CPCB data |
| Optimizer | Each PE period searches for the cleanest slot (smog) or the coolest allowed slot (heat), respecting playground capacity and teacher clashes. Younger classes pick first | Python, Lambda |
| Rules | Every outdoor slot is checked by **Cedar** policies: GRAP stages, NAQI bands, classes 1–5, asthma-watch cohorts, heat thresholds. Each change cites the rule that caused it | Cedar (AWS open source) via `cedarpy` |
| Words | A **Strands agent on Amazon Bedrock** (Nova 2 Lite) writes the principal brief and Hindi + English parent notices from the plan's facts, and answers questions ("Kya 7A ka practice 12 baje ho sakta hai?") using read-only tools | Strands Agents SDK, Bedrock |
| Approve | Principal gets an email (SNS) with the brief and a link, and approves with one tap. Step Functions waits on a task token. If nobody answers by 6:45, **only GRAP-required changes** apply. Clean-air days auto-publish | SNS, Step Functions `waitForTaskToken`, Choice |
| Parents | WhatsApp-ready message for the class group, Hindi voice note (Amazon Polly, neural *Kajal*), and a parent page showing their child's day | Polly, S3, Amplify Hosting |
| Staff & roles | Staff sign in with **Amazon Cognito**. A second **Cedar** policy set (`authz.cedar`) decides authority on every request: principals run and approve their own school, teachers view and ask (with a "Your day" card of their changed periods), district admins onboard schools but never approve | Cognito, API Gateway JWT authorizer, Cedar |
| During the day | At 9:30 and 11:30 a re-check reads the latest forecast and the current GRAP stage. CleanHour **may make the rest of the day safer on its own** (outdoor → indoor, with a Hindi/English update to parents, staff and the principal) but **never riskier** without a newly approved plan | EventBridge Scheduler, Lambda, SNS |
| Voice | The principal can ask by voice in Hindi or Hinglish. The answer is spoken by Polly | Browser speech recognition, Amazon Polly |
| Ops | Every run records its impact as CloudWatch metrics (PE periods moved, asthma-watch kids kept in, dose cut) on an impact dashboard. An alarm fires if the morning workflow fails. CI runs tests and lint on every push | Powertools for AWS Lambda (EMF), CloudWatch, GitHub Actions |
| Onboarding | A school photographs its timetable. A multimodal Strands agent on Bedrock transcribes it, and code normalises it (Games/PT → PE, "1:05" → 13:05, no fake teacher clashes). The school is live for the next 5:30 AM run | Bedrock (Nova 2 Lite, image input), Strands |

**Design rule (the same one the First Commit winners used): the model writes words, code decides
actions.** The LLM has no tool that can change a timetable. If Bedrock is unavailable, deterministic
template notices are used and the UI says so.

### Try these in the console
1. **Smog replay, Thu 6 Nov 2025, measured air at Rohini** (486 µg/m³ at 8 AM, 85 at 1 PM; GRAP II, so PE was
   allowed): 5 PE periods move to 11:45–1:05, assembly and recess go indoors, asthma-watch kids stay in. PE air
   368 → 88 µg/m³, about 65% less PM2.5 breathed outdoors.
2. **Flip GRAP to Stage III**: Cedar forces all PE indoors, marked *regulatory*.
3. **Heat replay, 8 Apr 2025** (Delhi's first heatwave): the same engine pulls 8A's PE *earlier*, from 11:45 to
   9:25 AM (feels-like 38 → 33 °C), and keeps classes 1–5 in at recess.
4. **Approve** → WhatsApp share → voice note → **parent page** (Hindi first).
5. **Tomorrow / live days**: real forecasts. On clean days CleanHour stays quiet (no alert fatigue).
6. **+ Add your school**: photograph a timetable and open the new school's console (district admin only).
7. **Switch to the PE teacher** (demo login, or "Demo as" locally): "Your day, Mr. Rawat" lists his moved periods,
   and Approve is replaced by the Cedar reason a teacher can't approve.
8. **After publishing, raise GRAP to III**: the mid-day re-check moves the rest of the day's PE indoors on its own,
   and the parent page shows the update in Hindi.

Demo logins after deploy (password printed by `deploy.sh`, default `CleanHour#2026`):
`principal@demo-rohini.cleanhour.in`, `pe.teacher@demo-rohini.cleanhour.in`, `district.admin@cleanhour.in`.

## Architecture

```
EventBridge Scheduler (05:30 IST) ─▶ Lambda (scheduler) ─▶ Step Functions: DailyPlan
   Plan (Lambda: forecast → optimizer → Cedar → Strands/Bedrock notices → DynamoDB) ─▶ SNS email to principal
   IsQuiet? ── yes ─▶ Publish
            └─ no ──▶ WaitForApproval (task token, 75 min) ──approve──▶ Publish (Polly → S3)
                                                     └─timeout──▶ AutoPublish (GRAP-required changes only)
Amplify Hosting (landing, console, parent page) ─▶ API Gateway HTTP API ─▶ Lambda (API) ─▶ DynamoDB / Step Functions / Bedrock
```

**AWS services:** Amplify Hosting, API Gateway (HTTP API + JWT authorizer), Amazon Cognito, Lambda (×6),
Step Functions, EventBridge Scheduler, DynamoDB (conditional writes), Amazon Bedrock, Amazon Polly, Amazon SNS, S3,
CloudWatch (EMF metrics, dashboard, alarm), IAM.
**AWS open source:** Strands Agents SDK, Cedar (two policy sets: child safety and staff authority), Powertools for
AWS Lambda, AWS SAM.

## Run it locally

```bash
pip install -r backend/requirements.txt
LLM_MODE=off python local_server.py      # http://localhost:8080 (template notices, no AWS needed)
python -m pytest -q backend/tests          # 16 tests (incl. staff policies, re-check): Cedar rules, optimizer constraints, heat, onboarding, API flow
```
With AWS credentials and Bedrock access, drop `LLM_MODE=off` and the Strands agent writes the notices.

## Deploy

```bash
# Needs AWS CLI v2, SAM CLI, and Bedrock access to Amazon Nova 2 Lite in us-east-1.
PRINCIPAL_EMAIL=you@example.com ./scripts/deploy.sh   # email is optional
# MODEL_ID=<bedrock model or inference profile id> overrides the default us.amazon.nova-2-lite-v1:0
```
The script deploys `template.yaml` (SAM), then uploads `frontend/` to Amplify Hosting with the API URL written
into `config.js`.

## Honest limitations

- The forecast is the CAMS global model (~40 km grid). Checked against CPCB stations it reads 1.2–4× low in
  Delhi's smog season, so CleanHour applies hour-by-hour correction factors fitted on the nearest station's
  2025 data (`school.py`). Factors for Dec–Feb are assumed from late November. Next step: a live morning
  nowcast from the station's latest reading.
- India's NAQI bands are defined on 24-hour averages. Applying them to hourly forecasts is a planning approximation.
- Dose estimates use assumed ventilation rates and an indoor/outdoor ratio of 0.8 (see `optimizer.py`).
- The demo school is fictional. GRAP class ranges change order to order, which is why they live in editable Cedar policies.
- Demo accounts and their shared password are public so judges can try every role. A pilot would issue
  real accounts per school.

## Repository

```
backend/cleanhour/   optimizer.py, policies.cedar + rules.py, agent.py (Strands), forecast.py, service.py,
                     api.py (HTTP API handler), workflow.py (Step Functions tasks), voice.py (Polly), store.py,
                     onboard.py (timetable photo → school)
backend/tests/       pytest suite
frontend/            index.html (landing, GSAP), console.html (principal), parent.html (parents), onboard.html
template.yaml        SAM: API, Lambdas, Step Functions, Scheduler, DynamoDB, S3, SNS
scripts/deploy.sh    backend + Amplify Hosting deploy
analysis/            ground_truth.py: reproduces every CPCB-based number in this README
docs/                research, benchmark, design directions, submission writeup
```

## AI tools used

- **Claude Code** (Anthropic) helped with research, code, and copy during the event.
- **Amazon Bedrock (Amazon Nova 2 Lite) via Strands Agents** runs inside the product to write notices and answer questions.

## Credits and licences

Air quality data: CPCB continuous monitoring stations (Rohini DPCC, R K Puram DPCC), republished by
[OpenCity](https://data.opencity.in/dataset/delhi-hourly-air-quality-reports). Forecasts: [Open-Meteo](https://open-meteo.com/) (CC BY 4.0), CAMS model. Policy engine:
[Cedar](https://www.cedarpolicy.com/) via [cedarpy](https://github.com/k9securityio/cedar-py) (Apache-2.0). Agents:
[Strands Agents SDK](https://github.com/strands-agents/sdk-python) (Apache-2.0). Animation: [GSAP](https://gsap.com/)
(standard no-charge licence). Fonts: Instrument Serif, Inter, Noto Serif Devanagari (SIL OFL).
Health and policy figures are cited in [docs/idea-and-research.md](docs/idea-and-research.md). Not medical advice.
