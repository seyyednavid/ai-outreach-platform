from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Outreach Platform"
    database_url: str
    openai_api_key: str

    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    # Login (Supabase Auth). Tokens are checked against the project's
    # public signing keys, so no Supabase secret is needed here.
    supabase_url: str | None = None
    # Only for older Supabase projects that still sign tokens with a
    # shared secret (HS256). New projects leave this empty.
    supabase_jwt_secret: str | None = None

    # The first user who signs in with this email receives the data
    # that existed before login was added.
    legacy_owner_email: str | None = None

    # Owners of the product, comma-separated. Only they can see the
    # Usage page: tokens, costs and traces for every customer.
    admin_emails: str = ""

    # Fernet key that encrypts Gmail tokens stored in the database.
    token_encryption_key: str | None = None

    # Tracing. Off: traces keep timing and structure, but not prompts
    # or outputs (email text, names). Turn off in production.
    trace_include_sensitive_data: bool = True

    # Prices for the cost estimate, in US dollars per million tokens.
    # Defaults: gpt-4.1-mini. Check https://openai.com/api/pricing
    llm_input_price_per_million: float = 0.40
    llm_output_price_per_million: float = 1.60

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
