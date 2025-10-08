from pydantic import BaseModel, EmailStr, HttpUrl


class CookieRequest(BaseModel):
    login_url: HttpUrl
    svc_username: str | None = None
    svc_email: EmailStr
    svc_password: str | None = None
    email_password: str
    callback_url: HttpUrl


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
