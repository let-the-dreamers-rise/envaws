"""Hindi voice note via Amazon Polly (neural voice Kajal, hi-IN), stored in S3."""

import boto3

from . import config


def synthesize(text: str, key: str) -> str | None:
    if not config.VOICE_BUCKET:
        return None
    audio = boto3.client("polly").synthesize_speech(
        Text=text[:2900], VoiceId="Kajal", Engine="neural", LanguageCode="hi-IN", OutputFormat="mp3")
    boto3.client("s3").put_object(Bucket=config.VOICE_BUCKET, Key=key,
                                  Body=audio["AudioStream"].read(), ContentType="audio/mpeg")
    return key


def speak(text: str) -> str | None:
    """Short spoken answer for the principal, as base64 MP3 (Polly neural Kajal speaks Hindi and Indian English)."""
    if not config.running_in_aws():
        return None
    import base64
    audio = boto3.client("polly").synthesize_speech(
        Text=text[:1200], VoiceId="Kajal", Engine="neural", LanguageCode="hi-IN", OutputFormat="mp3")
    return base64.b64encode(audio["AudioStream"].read()).decode()


def url(key: str) -> str:
    return boto3.client("s3").generate_presigned_url(
        "get_object", Params={"Bucket": config.VOICE_BUCKET, "Key": key}, ExpiresIn=3600)
