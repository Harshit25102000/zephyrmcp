from typing import Optional, Tuple
import base64

def get_auth_from_headers(headers: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extracts authentication information from headers.
    Returns (username, password, token).
    """
    auth_header = headers.get("authorization") or headers.get("Authorization")
    
    if not auth_header:
        return None, None, None
    
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return None, None, token
    
    if auth_header.startswith("Basic "):
        encoded_creds = auth_header[6:]
        decoded_creds = base64.b64decode(encoded_creds).decode("utf-8")
        if ":" in decoded_creds:
            username, password = decoded_creds.split(":", 1)
            return username, password, None
            
    return None, None, None
