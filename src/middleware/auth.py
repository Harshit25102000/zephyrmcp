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
        payload = auth_header[6:].strip()
        
        # Try parsing as JSON first (User's custom format: username and password keys)
        if payload.startswith("{"):
            try:
                import json
                creds = json.loads(payload)
                return creds.get("username"), creds.get("password"), None
            except:
                pass
        
        # Try parsing as key=value pairs (Alternative custom format)
        if "username=" in payload and "password=" in payload:
            try:
                # Basic username=xyz, password=abc
                parts = {}
                for item in payload.split(","):
                    if "=" in item:
                        k, v = item.strip().split("=", 1)
                        parts[k] = v
                return parts.get("username"), parts.get("password"), None
            except:
                pass

        # Fallback to standard Base64 Basic Auth
        try:
            decoded_creds = base64.b64decode(payload).decode("utf-8")
            if ":" in decoded_creds:
                username, password = decoded_creds.split(":", 1)
                return username, password, None
        except:
            pass
            
    return None, None, None
