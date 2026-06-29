from secrets import token_urlsafe


_MODEL_CREDENTIALS: dict[str, str] = {}


def register_model_credential(api_key: str) -> str:
    credential_ref = f"model-cred-{token_urlsafe(18)}"
    _MODEL_CREDENTIALS[credential_ref] = api_key
    return credential_ref


def get_model_credential(credential_ref: str) -> str | None:
    if not credential_ref:
        return None
    return _MODEL_CREDENTIALS.get(credential_ref)
