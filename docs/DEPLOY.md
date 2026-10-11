# Deploying CleanHour

You need an AWS account and an access key for an IAM user with permission to create the stack
(for a hackathon account, `AdministratorAccess` is simplest). Everything deploys to `us-east-1`.

## Option A: a Claude Code cloud session (recommended)

1. In the Claude app, open the environment menu in the session title bar → **Edit**, and add environment
   variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_REGION=us-east-1`.
   Never paste keys into a chat.
2. Start a **new** session on this repo (new sessions pick up the variables) and paste:

> Deploy CleanHour to AWS from branch `claude/admiring-carson-664i25` using the AWS credentials in my environment.
> 1. `git checkout claude/admiring-carson-664i25 && ./scripts/bootstrap.sh`
> 2. Find a Bedrock model my account can call in us-east-1: `aws bedrock list-inference-profiles --region us-east-1`,
>    prefer Amazon Nova 2 Lite, and prove it with one `aws bedrock-runtime converse` call. If Nova 2 Lite isn't
>    available, use the best Amazon Nova or Anthropic model that is.
> 3. `MODEL_ID=<that id> PRINCIPAL_EMAIL=<my email> ./scripts/deploy.sh`
> 4. Smoke-test the live API: `/api/health`; sign in as `principal@demo-rohini.cleanhour.in` with
>    `aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH`; `POST /api/schools/demo-rohini/plans {"when":"replay"}`;
>    poll the plan until `pending_approval`; check `plan.notices.source == "bedrock"`; approve; check the plan is
>    `published` with a voice note; check `/api/public/demo-rohini/latest`. Also open the site and console in a browser.
> 5. Fix anything that fails, commit and push to the same branch, redeploy, and give me the site, console and
>    dashboard URLs.

## Option B: your own machine

Needs Python 3.13 (or Docker, then use `sam build --use-container`), `git`, `zip`, `curl`.

```bash
git clone -b claude/admiring-carson-664i25 https://github.com/let-the-dreamers-rise/envaws && cd envaws
./scripts/bootstrap.sh                 # installs AWS CLI + SAM CLI into .venv-deploy if missing
aws configure                          # or export AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION
PRINCIPAL_EMAIL=you@example.com ./scripts/deploy.sh
```

## After deploy: 10-minute smoke test

- [ ] Open the site; the hero animates; no console errors.
- [ ] Console → sign in with the **Principal** demo button → *Smog replay · 6 Nov 2025* → *Run the 5:30 AM check*.
- [ ] The notice says "Written by the CleanHour agent (Strands Agents on Amazon Bedrock)". If it says
      "agent offline", redeploy with a `MODEL_ID` your account can call.
- [ ] Approve → the voice note plays → WhatsApp share → parent page shows the plan in Hindi.
- [ ] Raise GRAP to III → "Update 11:00" appears on the console and parent page.
- [ ] Sign out → sign in as **PE teacher** → "Your day, Mr. Rawat", and Approve is replaced by the Cedar reason.
- [ ] Ask "Kya 7A ka practice 12:30 baje ho sakta hai?" (type or 🎙).
- [ ] Confirm the SNS subscription email if you set `PRINCIPAL_EMAIL`.
- [ ] CloudWatch → Dashboards → `cleanhour-impact` shows the run.
