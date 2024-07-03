import base64


class EncodingService:
    @staticmethod
    def create_base64_auth_code(client_id: str, client_secret: str):
        return base64.b64encode(f"{client_id}:{client_secret}".encode("UTF-8")).decode("UTF-8")
