import os

TABLE_NAME = os.environ.get("TABLE_NAME", "")
VOICE_BUCKET = os.environ.get("VOICE_BUCKET", "")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")
MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-2-lite-v1:0")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1"))
# "auto" uses Bedrock when AWS credentials are present, "off" always uses templates.
LLM_MODE = os.environ.get("LLM_MODE", "auto")
LOCAL_DATA_DIR = os.environ.get("LOCAL_DATA_DIR", os.path.join(os.getcwd(), ".localdata"))
TIMEZONE = "Asia/Kolkata"


def running_in_aws() -> bool:
    return bool(TABLE_NAME)
