from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration managed via environment variables."""

    project_name: str = Field(default="GPT5 Hackathon API", alias="PROJECT_NAME")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_api_base_url: str = Field(
        default="https://api.openai.com/v1", alias="OPENAI_API_BASE_URL"
    )
    openai_tutor_model: str = Field(
        default="gpt-5.5", alias="OPENAI_TUTOR_MODEL"
    )
    openai_image_model: str = Field(
        default="gpt-image-2", alias="OPENAI_IMAGE_MODEL"
    )
    openai_realtime_model: str = Field(
        default="gpt-realtime", alias="OPENAI_REALTIME_MODEL"
    )
    openai_realtime_voice: str = Field(default="verse", alias="OPENAI_REALTIME_VOICE")
    openai_realtime_instructions: str | None = Field(
        default=None, alias="OPENAI_REALTIME_INSTRUCTIONS"
    )
    openai_vision_model: str = Field(
        default="gpt-5", alias="OPENAI_VISION_MODEL"
    )
    openai_transcription_model: str = Field(
        default="gpt-4o-transcribe", alias="OPENAI_TRANSCRIPTION_MODEL"
    )
    openai_annotation_model: str = Field(
        default="gpt-5", alias="OPENAI_ANNOTATION_MODEL"
    )
    openai_research_model: str = Field(
        default="gpt-5", alias="OPENAI_RESEARCH_MODEL"
    )
    openai_generative_ui_model: str = Field(
        default="gpt-5", alias="OPENAI_GENERATIVE_UI_MODEL"
    )
    openai_usf_defense_model: str = Field(
        default="gpt-5.5", alias="OPENAI_USF_DEFENSE_MODEL"
    )
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(
        default=None, alias="AWS_SECRET_ACCESS_KEY"
    )
    aws_profile: str | None = Field(default=None, alias="AWS_PROFILE")
    aws_region_name: str | None = Field(default=None, alias="AWS_REGION")
    aws_s3_bucket: str | None = Field(default=None, alias="AWS_S3_BUCKET")
    aws_saintpaul_assets_bucket: str | None = Field(
        default=None, alias="AWS_SAINTPAUL_ASSETS_BUCKET"
    )
    aws_saintpaul_sessions_table: str | None = Field(
        default=None, alias="AWS_SAINTPAUL_SESSIONS_TABLE"
    )
    aws_saintpaul_events_table: str | None = Field(
        default=None, alias="AWS_SAINTPAUL_EVENTS_TABLE"
    )
    aws_saintpaul_errors_table: str | None = Field(
        default=None, alias="AWS_SAINTPAUL_ERRORS_TABLE"
    )
    aws_usf_sessions_table: str | None = Field(
        default=None, alias="AWS_USF_SESSIONS_TABLE"
    )
    aws_usf_events_table: str | None = Field(
        default=None, alias="AWS_USF_EVENTS_TABLE"
    )
    aws_usf_errors_table: str | None = Field(
        default=None, alias="AWS_USF_ERRORS_TABLE"
    )
    aws_usf_recordings_bucket: str | None = Field(
        default=None, alias="AWS_USF_RECORDINGS_BUCKET"
    )
    aws_yandaojie_sessions_table: str | None = Field(
        default=None, alias="AWS_YANDAOJIE_SESSIONS_TABLE"
    )
    aws_yandaojie_events_table: str | None = Field(
        default=None, alias="AWS_YANDAOJIE_EVENTS_TABLE"
    )
    aws_yandaojie_errors_table: str | None = Field(
        default=None, alias="AWS_YANDAOJIE_ERRORS_TABLE"
    )
    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    deepseek_api_base_url: str = Field(
        default="https://api.deepseek.com", alias="DEEPSEEK_API_BASE_URL"
    )
    deepseek_model: str = Field(
        default="deepseek-v4-pro", alias="DEEPSEEK_MODEL"
    )
    yandaojie_mongodb_uri: str | None = Field(
        default=None, alias="YANDAOJIE_MONGODB_URI"
    )
    yandaojie_mongodb_database: str = Field(
        default="yandaojie", alias="YANDAOJIE_MONGODB_DATABASE"
    )
    tencent_secret_id: str | None = Field(default=None, alias="TENCENT_SECRET_ID")
    tencent_secret_key: str | None = Field(default=None, alias="TENCENT_SECRET_KEY")
    tencent_region: str = Field(default="ap-chengdu", alias="TENCENT_REGION")
    auth0_domain: str | None = Field(default=None, alias="AUTH0_DOMAIN")
    auth0_client_id: str | None = Field(default=None, alias="AUTH0_CLIENT_ID")
    auth0_client_secret: str | None = Field(
        default=None, alias="AUTH0_CLIENT_SECRET"
    )
    auth0_audience: str | None = Field(default=None, alias="AUTH0_AUDIENCE")
    stripe_secret_key: str | None = Field(default=None, alias="STRIPE_SECRET_KEY")
    stripe_default_price_id: str | None = Field(
        default=None, alias="STRIPE_DEFAULT_PRICE_ID"
    )
    stripe_mode: str = Field(default="subscription", alias="STRIPE_MODE")
    cohere_api_key: str | None = Field(default=None, alias="COHERE_API_KEY")
    cohere_api_base_url: str = Field(
        default="https://api.cohere.com", alias="COHERE_API_BASE_URL"
    )
    cohere_rerank_model: str = Field(
        default="rerank-english-v3.0", alias="COHERE_RERANK_MODEL"
    )
    arxiv_api_base_url: str = Field(
        default="http://export.arxiv.org/api/query", alias="ARXIV_API_BASE_URL"
    )
    arxiv_max_results: int = Field(default=25, alias="ARXIV_MAX_RESULTS")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
