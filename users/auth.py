from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from users.models import Account, UserToken
from users.utils.crypto import generate_sub_hash
import jwt


class MultiTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = None

        # Check for Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        # Fallback, try cookie
        if not token:
            token = request.COOKIES.get("access_token")

        if not token:
            return None

        try:
            payload = jwt.decode(
                token, options={"verify_signature": False}, algorithms=["HS256"]
            )

            user_token = UserToken.objects.filter(
                access_token=token, revoked=False
            ).first()

            if not user_token:
                raise AuthenticationFailed("Unknown token")

            if user_token.revoked or user_token.expires_at < timezone.now():
                raise AuthenticationFailed("Token revocado o expirado")

            # Validate the user sub hashses
            user = user_token.user
            sub_hash = generate_sub_hash(user)
            user_sub = payload.get("sub")
            if sub_hash != user_sub:
                raise AuthenticationFailed("Token no reconocido")

            if not user.is_active:
                raise AuthenticationFailed("Usuario deshabilitado")

            return (user, token)

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token expirado")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Token inválido")
        except Account.DoesNotExist:
            raise AuthenticationFailed("Usuario no encontrado")
        except UserToken.DoesNotExist:
            raise AuthenticationFailed("Token no reconocido")
