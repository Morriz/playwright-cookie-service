from pydantic import BaseModel, EmailStr, HttpUrl


class CookieRequest(BaseModel):
    x_username: str
    x_email: EmailStr
    x_password: str
    protonmail_email: EmailStr
    protonmail_password: str
    webhook_url: HttpUrl


class CookieResponse(BaseModel):
    success: bool
    cookies: str | None = None
    error: str | None = None
    iterations: int | None = None


class WebhookPayload(BaseModel):
    """Payload sent to webhook URL upon completion"""

    success: bool
    cookies: str | None = None
    error: str | None = None
    iterations: int | None = None
    request_id: str | None = None


class TaskStatusResponse(BaseModel):
    """Response for immediate return when webhook is provided"""

    status: str = "processing"
    message: str = "Task accepted. Results will be sent to webhook URL."
    request_id: str
