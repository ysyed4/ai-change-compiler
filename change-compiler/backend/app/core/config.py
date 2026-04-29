from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "Change Compiler API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/change_compiler"
    prometheus_url: str = "http://prometheus:9090"
    kafka_bootstrap_servers: str = "kafka1:9092,kafka2:9092,kafka3:9092"

    prometheus_timeout_seconds: float = 3.0
    kafka_metadata_timeout_seconds: float = 5.0
    execute_real_restart: bool = False

    # Auth (JWT)
    auth_enabled: bool = True
    jwt_secret: str = "dev-change-me"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "change-compiler"
    jwt_audience: str = "change-compiler-api"
    dev_token_endpoint_enabled: bool = True

    # Commercial / packaging feature flags
    require_manual_approval_before_execute: bool = True
    feature_advanced_policies_enabled: bool = True
    feature_integrations_enabled: bool = True
    feature_real_execution_enabled: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
