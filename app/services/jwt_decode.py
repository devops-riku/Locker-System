import jwt


# Decode without verifying signature (safe for inspection only)
def JWTDecode(token):
    decoded = jwt.decode(token, options={"verify_signature": False})
    return decoded

