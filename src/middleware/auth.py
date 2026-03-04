from typing import Optional, Tuple
from mcp.server.fastmcp import Context

def extract_zephyr_auth(ctx: Context) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extracts authentication information from the request context using the GitLab pattern.
    - Bearer token: sent in 'Authorization: Bearer <token>'
    - Basic Auth: 'username' and 'password' keys sent directly in headers.
    
    Expected Headers:
    - Authorization: Bearer <token>
    OR
    - username: <user>
    - password: <pwd>
    
    Returns (username, password, token).
    Raises Exception if no credentials are found.
    """
    request = getattr(ctx, "request", None)
    if not request and hasattr(ctx, "request_context"):
        request = ctx.request_context.request

    if not request:
        raise RuntimeError("No HTTP request context found. Please use HTTP transport.")

    headers = request.headers
    
    # 1. Check for Bearer token in Authorization header
    auth_header = headers.get("authorization") or headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        return None, None, token
    
    # 2. Check for username and password in dedicated header keys
    username = headers.get("username") or headers.get("Username")
    password = headers.get("password") or headers.get("Password")
    
    if username and password:
        return username, password, None
        
    # 3. Raise error if absolutely no credentials provided
    raise RuntimeError("Credentials not provided. Provide 'Authorization: Bearer <token>' or 'username'/'password' headers.")
