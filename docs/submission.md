# Submission kit

## Short writeup (paste into the form)

**CleanHour: don't cancel play, move it to the clean hour.** (Track: Air)

**Problem.** On smog-season mornings Delhi's air at 8 AM is about twice as dirty as at 1 PM (measured at the CPCB
Rohini station, 15 Oct–30 Nov 2025: 315 vs 167 µg/m³ PM2.5), yet schools hold assembly and PE at 7:45–9:30. 29% of Delhi teens show
asthma on spirometry and 88% are undiagnosed. Today's only tool is a blanket ban that costs kids weeks of exercise.

**What we built.** An AI duty officer for schools. At 5:30 AM it reads the PM2.5 and feels-like forecast for
the school, moves each outdoor period into the cleanest (or, in summer, coolest) allowed hour, respecting
playground capacity and teacher clashes, and checks every move against Cedar policies: GRAP stages, NAQI bands,
classes 1–5, asthma-watch kids, heat. The principal gets an email and approves with one tap. Parents get a
WhatsApp-ready Hindi/English notice, a Hindi voice note and a parent page. Schools join by photographing their timetable.
Validated on measured CPCB data: moving 8 AM PE to the cleanest school hour cut PM2.5 by 57% on the median
smog-season day at Rohini. Across winter 2024-25 it would have rescued safe outdoor PE on 45 school days and kept
kids in on the 52 days when nothing was safe. The forecast model read 1.2–4× low against the stations, so
CleanHour bias-corrects it hour by hour.

**Where AWS fits.** EventBridge Scheduler → Step Functions (plan → SNS email → wait for approval via task token →
publish; clean days auto-publish; on timeout only GRAP-required changes apply) → Lambda. A Strands agent on
Amazon Bedrock (Nova 2 Lite) writes the notices, answers the principal's Hindi/English questions (also by voice) with
read-only tools, and reads timetable photos. Cedar (AWS open source) decides every outdoor slot, so the model never does,
and a second Cedar policy set decides staff authority on top of Amazon Cognito sign-in (principals approve, teachers view,
district admins onboard). 9:30/11:30 re-checks may tighten the day on their own but never loosen it. DynamoDB
(conditional writes), Polly (Hindi neural voice), S3, SNS, API Gateway (JWT authorizer), CloudWatch impact dashboard
and alarm via Powertools for AWS Lambda, Amplify Hosting, deployed with AWS SAM; CI on GitHub Actions.

**AI tools used while building:** Claude Code.

## 3-minute video script (record the deployed site; keep the AWS console in a second tab)

| Time | Show | Say |
|---|---|---|
| 0:00–0:15 | Landing hero animation | "Thursday, 6 November 2025. Rohini, Delhi. At 8 AM, PE time, the government station measured PM2.5 at 486. That's Severe. PE was still allowed that day. By 1 PM it was 85. Same school, same day." |
| 0:15–0:30 | Scroll: evidence marquee → before/after scrub | "Delhi has 44.9 lakh schoolchildren. 29% of teens show asthma, and most don't know it. Today's only answer is a blanket ban. CleanHour doesn't cancel play. It moves it." |
| 0:30–0:45 | Phone: the 5:30 AM SNS email arrives → tap link | "Meet the principal at 6 AM. CleanHour has already read the forecast for her school and emailed her the plan." |
| 0:45–1:25 | Console, smog replay (6 Nov): hero metrics, forecast bars, timetable Before → After, "What changed and why" with rule chips and "playground full" skips | "PE for 3A moves from 8:05 to 1:05: 462 down to 80. 5A can't have 1:05 because the playground is full, so it gets 12:25. Assembly and recess go indoors. Asthma-watch kids stay in. Every change cites the Cedar rule behind it. The AI never decides who goes outside." |
| 1:25–1:40 | Flip GRAP to III | "If GRAP Stage III is declared, the rules override the sky: all PE indoors, marked regulatory, and it applies even if nobody answers." |
| 1:40–1:55 | Ask: "Kya 7A ka practice 12:30 baje ho sakta hai?" | "She can ask in Hinglish. The Strands agent on Bedrock checks the rules through tools before it answers." |
| 1:55–2:15 | Approve → Hindi notice → play the Polly voice note → WhatsApp share → parent page on phone | "One tap. Parents get it on WhatsApp in Hindi, with a voice note for those who'd rather listen, before the bus leaves." |
| (optional, cut heat if short) | Raise GRAP to III after publishing → update banner; switch to PE teacher → "Your day" + Cedar reason on Approve | "CAQM raises GRAP at noon? The 11:30 re-check moves the afternoon indoors on its own. It can make the day safer, never riskier. And a teacher sees their own changes but can't approve. Cedar decides who can do what." |
| 2:15–2:30 | Heat replay, 8 Apr 2025 | "Same engine in April: heat is the problem, so it pulls 8A's PE earlier, from 11:45 to 9:25. Feels-like 38 to 33 degrees. It works all year." |
| 2:30–2:45 | Add your school: photo → school live | "A school joins by photographing its timetable. No sensors, no typing." |
| 2:45–3:00 | AWS console: Step Functions graph (WaitForApproval), CloudWatch impact dashboard, EventBridge schedules, Cognito users | "EventBridge, Step Functions, Lambda, Bedrock with Strands, Cedar, Polly, SNS, DynamoDB, Amplify. Checked against government stations: 57% less PM2.5 on the median smog day, and 45 winter days of PE rescued instead of cancelled. CleanHour." |

Recording tips: 1080p, browser zoom 110%, a phone frame for the parent page, no music under the voice. Upload as
unlisted and check the link while signed out.

## Blog outline (AWS Builder Center, top 5 blogs win AirPods)

1. The 8 AM problem (the chart: measured PM2.5 by hour at CPCB Rohini, Oct–Nov 2025)
2. Why "move, don't cancel" (inversion layer physics)
3. Architecture: Step Functions task tokens for human approval, Cedar for rules, Strands for words
4. What fought back: the forecast model reading 2–4× low against CPCB stations (and the calibration fix), hourly vs 24-hour NAQI bands, teacher clashes, heat vs smog trade-offs
5. What's next: CPCB nowcast correction, more languages, the DoE pilot
