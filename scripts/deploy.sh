#!/usr/bin/env bash
# Deploys the CleanHour backend (SAM) and the frontend (Amplify Hosting, manual deploy).
# Needs: AWS credentials, AWS CLI v2, SAM CLI, zip, curl.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
STACK="${STACK:-cleanhour}"
APP_NAME="${APP_NAME:-cleanhour}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Creating (or finding) the Amplify Hosting app"
APP_ID="$(aws amplify list-apps --region "$REGION" --query "apps[?name=='$APP_NAME'].appId | [0]" --output text)"
if [ -z "$APP_ID" ] || [ "$APP_ID" = "None" ]; then
  APP_ID="$(aws amplify create-app --name "$APP_NAME" --region "$REGION" --query app.appId --output text)"
fi
SITE_URL="https://main.$APP_ID.amplifyapp.com"

echo "==> Building and deploying the backend stack '$STACK' in $REGION"
OVERRIDES=("SiteUrl=$SITE_URL")
[ -n "${PRINCIPAL_EMAIL:-}" ] && OVERRIDES+=("PrincipalEmail=$PRINCIPAL_EMAIL")
[ -n "${MODEL_ID:-}" ] && OVERRIDES+=("ModelId=$MODEL_ID")
sam build --template template.yaml
sam deploy --stack-name "$STACK" --region "$REGION" --capabilities CAPABILITY_IAM \
  --resolve-s3 --no-confirm-changeset --no-fail-on-empty-changeset \
  --parameter-overrides "${OVERRIDES[@]}"

output() {
  aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
API_URL="$(output ApiUrl)"
POOL_ID="$(output UserPoolId)"
CLIENT_ID="$(output UserPoolClientId)"
echo "API: $API_URL"

echo "==> Creating demo staff accounts (principal, PE teacher, district admin)"
DEMO_PASSWORD="${DEMO_PASSWORD:-CleanHour#2026}"
demo_user() {  # email name role school
  aws cognito-idp admin-create-user --user-pool-id "$POOL_ID" --region "$REGION" --username "$1" \
    --message-action SUPPRESS --user-attributes Name=email,Value="$1" Name=email_verified,Value=true \
    Name=name,Value="$2" Name=custom:role,Value="$3" Name=custom:school,Value="$4" >/dev/null 2>&1 || true
  aws cognito-idp admin-set-user-password --user-pool-id "$POOL_ID" --region "$REGION" --username "$1" \
    --password "$DEMO_PASSWORD" --permanent
}
demo_user principal@demo-rohini.cleanhour.in "Mrs. Sharma (Principal)" principal demo-rohini
demo_user pe.teacher@demo-rohini.cleanhour.in "Mr. Rawat" teacher demo-rohini
demo_user district.admin@cleanhour.in "District admin" admin "*"

echo "==> Packaging the frontend"
SITE="$ROOT/.aws-sam/site"
rm -rf "$SITE" "$ROOT/.aws-sam/site.zip"
mkdir -p "$SITE"
cp -R frontend/. "$SITE/"
cat > "$SITE/config.js" <<EOF
window.CLEANHOUR_API = "$API_URL";
window.CLEANHOUR_AUTH = { region: "$REGION", clientId: "$CLIENT_ID", demoPassword: "$DEMO_PASSWORD" };
EOF
(cd "$SITE" && zip -qr ../site.zip .)

echo "==> Deploying the frontend to Amplify Hosting"
aws amplify get-branch --app-id "$APP_ID" --branch-name main --region "$REGION" >/dev/null 2>&1 \
  || aws amplify create-branch --app-id "$APP_ID" --branch-name main --region "$REGION" >/dev/null
read -r JOB_ID UPLOAD_URL < <(aws amplify create-deployment --app-id "$APP_ID" --branch-name main \
  --region "$REGION" --query "[jobId,zipUploadUrl]" --output text)
curl -sS --fail -X PUT -T "$ROOT/.aws-sam/site.zip" "$UPLOAD_URL"
aws amplify start-deployment --app-id "$APP_ID" --branch-name main --job-id "$JOB_ID" --region "$REGION" >/dev/null

echo
echo "Site:    $SITE_URL"
echo "Console: $SITE_URL/console.html?date=2025-11-06"
echo "API:     $API_URL/api/health"
echo "Demo logins (password $DEMO_PASSWORD): principal@demo-rohini.cleanhour.in, pe.teacher@demo-rohini.cleanhour.in, district.admin@cleanhour.in"
