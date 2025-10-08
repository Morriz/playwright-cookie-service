from models import CookieRequest


def build_login_task(request: CookieRequest) -> str:
    """
    Build Claude task prompt for login automation.

    Args:
        request: Cookie request with credentials and login URL

    Returns:
        Task prompt string
    """
    auth_type = (
        "username/password"
        if request.svc_username and request.svc_password
        else "magic link/email-only"
    )

    credentials_info = f"""
Credentials:
- Service Email: {request.svc_email}
- ProtonMail Email: {request.svc_email}
- ProtonMail Password: {request.email_password}
"""
    if request.svc_username:
        credentials_info += f"- Service Username: {request.svc_username}\n"
    if request.svc_password:
        credentials_info += f"- Service Password: {request.svc_password}\n"

    task = f"""
You are a browser automation expert. Your task is to log in to the authentication service.

Login URL: {request.login_url}
Authentication Type: {auth_type}

{credentials_info}

SECURITY - DO NOT ECHO CREDENTIALS:
- NEVER repeat passwords, usernames, emails, or verification codes in your responses
- NEVER log or output credential values
- Use generic descriptions like "entered the password" or "submitted verification code"
- Only reference credentials by type, never by value

Steps to follow:
1. Navigate to {request.login_url}
2. {"Enter the username and submit" if request.svc_username else "Enter the email if requested"}
3. If asked for email/phone verification, enter the email
4. {"Enter the password and submit" if request.svc_password else "Look for magic link or verification code sent to email"}
5. If a verification code or magic link is required:
   a. Open https://account.proton.me/login in a new tab or navigate to it
   b. Log in to ProtonMail with the provided credentials
   c. Find the latest email from the service with a verification code (6-8 digits) or magic link
   d. Extract the code or click the magic link
   e. Navigate back to the service login page if needed
   f. Enter the verification code if applicable
6. Wait until successfully logged in
7. Respond with "Login complete" when done

CRITICAL - ERROR REPORTING PROTOCOL:
If you encounter an unrecoverable error, respond with EXACTLY this format:
TASK_FAILED: <brief description of what went wrong>

Examples:
- TASK_FAILED: Bot detection blocked login with message "Could not log you in now"
- TASK_FAILED: Login failed after 2 attempts, password may be incorrect
- TASK_FAILED: Magic link not received after 2 minutes

IMPORTANT:
- Use browser_snapshot before each interaction to see page state
- Adapt to actual page content, don't assume selectors
- If any step fails 2 times in a row (like login submission), use TASK_FAILED protocol
- Do NOT keep retrying failed actions - this could lock the account
- If you see console errors indicating bot detection or API failures, use TASK_FAILED protocol immediately
- If the service shows error message "Could not log you in now. Please try again later.", use TASK_FAILED protocol IMMEDIATELY
"""

    return task
