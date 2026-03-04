from typing import Optional, Tuple

def get_auth_from_headers(headers: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extracts authentication information from headers.
    - Bearer token: sent in 'Authorization: Bearer <token>'
    - Basic Auth: 'username' and 'password' keys sent directly in headers.
    
    Raises Exception if no credentials are found.
    Returns (username, password, token).
    """
    # 1. Check for Bearer token in Authorization header
    auth_header = headers.get("authorization") or headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        return None, None, token
    
    # 2. Check for username and password in dedicated header keys
    username = headers.get("username") or headers.get("Username")
    password = headers.get("password") or headers.get("Password")
    
    if username and password:
        return username, password, None
        
    # 3. Raise error if absolutely no credentials provided
    raise Exception("Credentials not provided. Please provide either 'Authorization: Bearer <token>' or 'username' and 'password' headers.")
