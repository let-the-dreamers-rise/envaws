# CleanHour

**Don't cancel play. Move it to the clean hour.**

CleanHour is an AI duty officer for Indian schools. At 5:30 AM it reads the air and heat forecast for the
school's location, moves outdoor periods (assembly, PE, recess) into the safest hour of the day, checks every
move against GRAP rules and the school's own policies, emails the principal for one-tap approval, and tells
parents in Hindi on WhatsApp, with a voice note, before the school bus leaves.

Track: **Air** (with a heat mode that also covers Heat & Water) · Environmental Hacks, Bharat Builds Tour 2026.

- Live site: `<add after deploy>` · Principal console: `<site>/console.html?date=2025-11-21`
- Demo video: `<add YouTube link>`
- Research and benchmark: [docs/idea-and-research.md](docs/idea-and-research.md) · Design: [docs/design.md](docs/design.md)

## The problem

- Delhi has **5,556 schools and 44.9 lakh students** (UDISE+ 2024-25). **29% of Delhi teens show asthma on
  spirometry and 88% of them were never diagnosed** (Lung India, 2021).
- Smog-season mornings are the worst hour of the day. A cold inversion traps pollution until the midday
  mixing layer lifts it. In central Delhi between 15 Oct and 30 Nov 2025, PM2.5 averaged **117 µg/m³ at 8 AM vs
  57 at 1 PM**. Moving an 8 AM outdoor slot to the cleanest school hour cut PM2.5 by **52% on the median day**
  (47 days, CAMS model data; our analysis).
- Schools hold assembly and PE at 7:45–9:30 AM. The only policy tool is a **blanket, city-wide ban**
  (Nov 2025: CAQM suspended outdoor school sports across NCR), which costs children weeks of exercise.

## What it does

| Step | What happens | Built with |
|---|---|---|
| 5:30 AM | EventBridge Scheduler starts the `DailyPlan` Step Functions workflow for each school | EventBridge Scheduler, Step Functions |
| Forecast | Hourly PM2.5/PM10 + feels-like temperature for the school's coordinates | Open-Meteo (CAMS) |
| Optimizer | Each PE period searches for the cleanest slot (smog) or the coolest allowed slot (heat), respecting playground capacity and teacher clashes. Younger classes pick first | Python, Lambda |
| Rules | Every outdoor slot is checked by **Cedar** policies: GRAP stages, NAQI bands, classes 1–5, asthma-watch cohorts, heat thresholds. Each change cites the rule that caused it | Cedar (AWS open source) via `cedarpy` |
| Words | A **Strands agent on Amazon Bedrock** (Nova 2 Lite) writes the principal brief and Hindi + English parent notices from the plan's facts, and answers questions ("Kya 7A ka practice 12 baje ho sakta hai?") using read-only tools | Strands Agents SDK, Bedrock |
| Approve | Principal gets an email (SNS) with the brief and a link, and approves with one tap. Step Functions waits on a task token. If nobody answers by 6:45, **only GRAP-required changes** apply. Clean-air days auto-publish | SNS, Step Functions `waitForTaskToken`, Choice |
| Parents | WhatsApp-ready message for the class group, Hindi voice note (Amazon Polly, neural *Kajal*), and a parent page showing their child's day | Polly, S3, Amplify Hosting |
| Onboarding | A school photographs its timetable. A multimodal Strands agent on Bedrock transcribes it, and code normalises it (Games/PT → PE, "1:05" → 13:05, no fake teacher clashes). The school is live for the next 5:30 AM run | Bedrock (Nova 2 Lite, image input), Strands |

**Design rule (the same one the First Commit winners used): the model writes words, code decides
actions.** The LLM has no tool that can change a timetable. If Bedrock is unavailable, deterministic
template notices are used and the UI says so.

### Try these in the console
1. **Smog replay, 21 Nov 2025** (the "gas chamber" week): 5 PE periods move to 11:45–1:05, assembly and recess go
   indoors, 16 asthma-watch kids stay in. PE air 160 → 93 µg/m³, about 42% less PM2.5 breathed outdoors.
2. **Flip GRAP to Stage III**: Cedar forces all PE indoors, marked *regulatory*.
3. **Heat replay, 8 Apr 2025** (Delhi's first heatwave): the same engine pulls 8A's PE *earlier*, from 11:45 to
   9:25 AM (feels-like 38 → 33 °C), and keeps classes 1–5 in at recess.
4. **Approve** → WhatsApp share → voice note → **parent page** (Hindi first).
5. **Tomorrow / live days**: real forecasts. On clean days CleanHour stays quiet (no alert fatigue).
6. **+ Add your school**: photograph a timetable and open the new school's console.

## Architecture

```
EventBridge Scheduler (05:30 IST) ─▶ Lambda (scheduler) ─▶ Step Functions: DailyPlan
   Plan (Lambda: forecast → optimizer → Cedar → Strands/Bedrock notices → DynamoDB) ─▶ SNS email to principal
   IsQuiet? ── yes ─▶ Publish
            └─ no ──▶ WaitForApproval (task token, 75 min) ──approve──▶ Publish (Polly → S3)
                                                     └─timeout──▶ AutoPublish (GRAP-required changes only)
Amplify Hosting (landing, console, parent page) ─▶ API Gateway HTTP API ─▶ Lambda (API) ─▶ DynamoDB / Step Functions / Bedrock
```

**AWS services:** Amplify Hosting, API Gateway (HTTP API), Lambda (×5), Step Functions, EventBridge Scheduler,
DynamoDB, Amazon Bedrock, Amazon Polly, Amazon SNS, S3, CloudWatch Logs, IAM.
**AWS open source:** Strands Agents SDK, Cedar, AWS SAM.

## Run it locally

```bash
pip install -r backend/requirements.txt
LLM_MODE=off python local_server.py      # http://localhost:8080 (template notices, no AWS needed)
python -m pytest -q backend/tests          # 12 tests: Cedar rules, optimizer constraints, heat, onboarding, API flow
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

- The forecast is the CAMS global model (~40 km grid). It underestimates absolute peaks compared with CPCB
  ground stations but captures the daily *shape*, and the shape is what picks the cleanest hour. Next step:
  correct it each morning with the nearest CPCB station reading.
- India's NAQI bands are defined on 24-hour averages. Applying them to hourly forecasts is a planning approximation.
- Dose estimates use assumed ventilation rates and an indoor/outdoor ratio of 0.8 (see `optimizer.py`).
- The demo school is fictional. GRAP class ranges change order to order, which is why they live in editable Cedar policies.
- The demo API has no login. A pilot would add Cognito for principals.

## Repository

```
backend/cleanhour/   optimizer.py, policies.cedar + rules.py, agent.py (Strands), forecast.py, service.py,
                     api.py (HTTP API handler), workflow.py (Step Functions tasks), voice.py (Polly), store.py,
                     onboard.py (timetable photo → school)
backend/tests/       pytest suite
frontend/            index.html (landing, GSAP), console.html (principal), parent.html (parents), onboard.html
template.yaml        SAM: API, Lambdas, Step Functions, Scheduler, DynamoDB, S3, SNS
scripts/deploy.sh    backend + Amplify Hosting deploy
docs/                research, benchmark, design directions, submission writeup
```

## AI tools used

- **Claude Code** (Anthropic) helped with research, code, and copy during the event.
- **Amazon Bedrock (Amazon Nova 2 Lite) via Strands Agents** runs inside the product to write notices and answer questions.

## Credits and licences

Air quality and weather data: [Open-Meteo](https://open-meteo.com/) (CC BY 4.0), CAMS model. Policy engine:
[Cedar](https://www.cedarpolicy.com/) via [cedarpy](https://github.com/k9securityio/cedar-py) (Apache-2.0). Agents:
[Strands Agents SDK](https://github.com/strands-agents/sdk-python) (Apache-2.0). Animation: [GSAP](https://gsap.com/)
(standard no-charge licence). Fonts: Instrument Serif, Inter, Noto Serif Devanagari (SIL OFL).
Health and policy figures are cited in [docs/idea-and-research.md](docs/idea-and-research.md). Not medical advice.
