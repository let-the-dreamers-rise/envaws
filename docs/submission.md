# Submission kit

## Short writeup (paste into the form)

**CleanHour: don't cancel play, move it to the clean hour.** (Track: Air)

**Problem.** On smog-season mornings Delhi's air at 8 AM is about twice as dirty as at 1 PM (central Delhi,
Oct–Nov 2025: 117 vs 57 µg/m³ PM2.5), yet schools hold assembly and PE at 7:45–9:30. 29% of Delhi teens show
asthma on spirometry and 88% are undiagnosed. Today's only tool is a blanket ban that costs kids weeks of exercise.

**What we built.** An AI duty officer for schools. At 5:30 AM it reads the PM2.5 and feels-like forecast for
the school, moves each outdoor period into the cleanest (or, in summer, coolest) allowed hour, respecting
playground capacity and teacher clashes, and checks every move against Cedar policies: GRAP stages, NAQI bands,
classes 1–5, asthma-watch kids, heat. The principal gets an email and approves with one tap. Parents get a
WhatsApp-ready Hindi/English notice, a Hindi voice note and a parent page. Schools join by photographing their timetable.
On the 21 Nov 2025 replay, PE air drops from 160 to 93 µg/m³, about 42% less PM2.5 breathed outdoors, and no
PE period is cancelled.

**Where AWS fits.** EventBridge Scheduler → Step Functions (plan → SNS email → wait for approval via task token →
publish; clean days auto-publish; on timeout only GRAP-required changes apply) → Lambda. A Strands agent on
Amazon Bedrock (Nova 2 Lite) writes the notices, answers the principal's Hindi/English questions with read-only tools, and
reads timetable photos. Cedar (AWS open source) decides every outdoor slot, so the model never does. DynamoDB,
Polly (Hindi neural voice), S3, SNS, API Gateway, Amplify Hosting, deployed with AWS SAM.

**AI tools used while building:** Claude Code.

## 3-minute video script (record the deployed site; keep the AWS console in a second tab)

| Time | Show | Say |
|---|---|---|
| 0:00–0:15 | Landing hero animation | "21 November 2025. The Supreme Court says outdoor activity is putting Delhi's children in a gas chamber. That morning at 8 AM, assembly time, PM2.5 was 193. By 2 PM it was 89. Same school, same day, half the dose." |
| 0:15–0:30 | Scroll: evidence marquee → before/after scrub | "Delhi has 44.9 lakh schoolchildren. 29% of teens show asthma, and most don't know it. Today's only answer is a blanket ban. CleanHour doesn't cancel play. It moves it." |
| 0:30–0:45 | Phone: the 5:30 AM SNS email arrives → tap link | "Meet the principal at 6 AM. CleanHour has already read the forecast for her school and emailed her the plan." |
| 0:45–1:25 | Console, smog replay: hero metrics, forecast bars, timetable Before → After, "What changed and why" with rule chips and "playground full" skips | "PE for 3A moves from 8:05 to 1:05, 51% cleaner. 5A can't have 1:05 because the playground is full, so it gets 12:25. Assembly and recess go indoors. Sixteen asthma-watch kids stay in. Every change cites the Cedar rule behind it. The AI never decides who goes outside." |
| 1:25–1:40 | Flip GRAP to III | "If GRAP Stage III is declared, the rules override the sky: all PE indoors, marked regulatory, and it applies even if nobody answers." |
| 1:40–1:55 | Ask: "Kya 7A ka practice 12:30 baje ho sakta hai?" | "She can ask in Hinglish. The Strands agent on Bedrock checks the rules through tools before it answers." |
| 1:55–2:15 | Approve → Hindi notice → play the Polly voice note → WhatsApp share → parent page on phone | "One tap. Parents get it on WhatsApp in Hindi, with a voice note for those who'd rather listen, before the bus leaves." |
| 2:15–2:30 | Heat replay, 8 Apr 2025 | "Same engine in April: heat is the problem, so it pulls 8A's PE earlier, from 11:45 to 9:25. Feels-like 38 to 33 degrees. It works all year." |
| 2:30–2:45 | Add your school: photo → school live | "A school joins by photographing its timetable. No sensors, no typing." |
| 2:45–3:00 | AWS console: Step Functions graph (WaitForApproval), Lambda, DynamoDB items, EventBridge schedule | "EventBridge, Step Functions, Lambda, Bedrock with Strands, Cedar, Polly, SNS, DynamoDB, Amplify. Fifty-two percent less PM2.5 on the median smog day, and no cancelled PE. CleanHour." |

Recording tips: 1080p, browser zoom 110%, a phone frame for the parent page, no music under the voice. Upload as
unlisted and check the link while signed out.

## Blog outline (AWS Builder Center, top 5 blogs win AirPods)

1. The 8 AM problem (the chart: PM2.5 by hour, Oct–Nov 2025)
2. Why "move, don't cancel" (inversion layer physics)
3. Architecture: Step Functions task tokens for human approval, Cedar for rules, Strands for words
4. What fought back: hourly vs 24-hour NAQI bands, teacher clashes, the API rate limit during the hackathon, heat vs smog trade-offs
5. What's next: CPCB nowcast correction, more languages, the DoE pilot
