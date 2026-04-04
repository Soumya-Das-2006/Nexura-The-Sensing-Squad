"""
apps/accounts/api_views.py

DRF REST API endpoints for mobile app / external integrations:
  POST /api/v1/auth/send-otp/      → generate & send OTP
  POST /api/v1/auth/verify-otp/    → verify OTP, return JWT tokens
  POST /api/v1/auth/refresh/       → refresh JWT access token
  GET  /api/v1/auth/me/            → current user profile
  POST /api/v1/auth/logout/        → blacklist refresh token
"""
import logging
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, KYCRecord
from .otp_service import generate_otp, verify_otp

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _normalise_mobile(raw: str) -> str:
    return raw.strip().lstrip('+').lstrip('91').lstrip('0')


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh['mobile']    = user.mobile
    refresh['is_worker'] = user.is_worker
    refresh['is_admin']  = user.is_admin
    return {
        'refresh': str(refresh),
        'access':  str(refresh.access_token),
    }


# ── Endpoints ────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    """
    Send an OTP to the given mobile number.

    Body: { "mobile": "9XXXXXXXXX", "purpose": "register" | "login" }
    """
    mobile  = _normalise_mobile(request.data.get('mobile', ''))
    purpose = request.data.get('purpose', 'login')

    if not mobile or len(mobile) != 10 or not mobile.isdigit():
        return Response({'error': 'Valid 10-digit mobile number required.'}, status=400)

    if purpose not in ('register', 'login'):
        return Response({'error': 'purpose must be register or login.'}, status=400)

    # For login, require account to exist
    if purpose == 'login' and not User.objects.filter(mobile=mobile, is_active=True).exists():
        return Response({'error': 'No account found for this number.'}, status=404)

    try:
        generate_otp(mobile, purpose=purpose)
    except Exception as e:
        logger.error(f"OTP send failed for {mobile}: {e}")
        return Response({'error': 'OTP dispatch failed. Try again.'}, status=503)

    response = {'message': f'OTP sent to +91 {mobile}.', 'mobile': mobile}
    if settings.OTP_TEST_MODE:
        response['otp'] = settings.OTP_TEST_CODE
        response['test_mode'] = True
    return Response(response)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp_api(request):
    """
    Verify OTP and return JWT tokens.

    Body: { "mobile": "9XXXXXXXXX", "code": "123456", "purpose": "register" | "login" }
    Response: { "access": "...", "refresh": "...", "user": {...} }
    """
    mobile  = _normalise_mobile(request.data.get('mobile', ''))
    code    = str(request.data.get('code', '')).strip()
    purpose = request.data.get('purpose', 'login')

    if not mobile or not code:
        return Response({'error': 'mobile and code are required.'}, status=400)

    ok, reason = verify_otp(mobile, code, purpose=purpose)
    if not ok:
        messages_map = {
            'not_found':    'No active OTP found. Please request a new one.',
            'expired':      'OTP has expired. Please request a new one.',
            'already_used': 'OTP already used.',
            'max_attempts': 'Too many attempts. Request a new OTP.',
            'invalid':      'Invalid OTP.',
        }
        return Response({'error': messages_map.get(reason, 'OTP verification failed.')}, status=400)

    # Get or create user
    user, created = User.objects.get_or_create(
        mobile=mobile,
        defaults={'is_worker': True, 'mobile_verified': True},
    )
    if not created:
        user.mobile_verified = True
        user.save(update_fields=['mobile_verified'])

    KYCRecord.objects.get_or_create(worker=user)

    tokens = _tokens_for_user(user)
    return Response({
        **tokens,
        'user': {
            'mobile':           user.mobile,
            'is_worker':        user.is_worker,
            'mobile_verified':  user.mobile_verified,
            'profile_complete': user.profile_complete,
            'language':         user.language,
        },
        'created': created,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Return the current authenticated user's basic profile."""
    user = request.user
    data = {
        'mobile':           user.mobile,
        'email':            user.email,
        'is_worker':        user.is_worker,
        'is_admin':         user.is_admin,
        'mobile_verified':  user.mobile_verified,
        'profile_complete': user.profile_complete,
        'language':         user.language,
        'date_joined':      user.date_joined,
    }

    # Attach worker profile if it exists
    try:
        wp = user.workerprofile
        data['profile'] = {
            'name':         wp.name,
            'platform':     wp.platform,
            'segment':      wp.segment,
            'zone_id':      wp.zone_id,
            'zone_city':    wp.zone.city if wp.zone else None,
            'upi_id':       wp.upi_id,
            'risk_score':   wp.risk_score,
        }
    except Exception:
        data['profile'] = None

    # Attach KYC status
    try:
        data['kyc_status'] = user.kyc.status
    except Exception:
        data['kyc_status'] = 'pending'

    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_api(request):
    """Blacklist the provided refresh token."""
    try:
        refresh_token = request.data.get('refresh')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Logged out successfully.'})
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    """
    Wrapper around simplejwt's TokenRefreshView.
    Body: { "refresh": "..." }
    """
    from rest_framework_simplejwt.serializers import TokenRefreshSerializer
    serializer = TokenRefreshSerializer(data=request.data)
    if serializer.is_valid():
        return Response(serializer.validated_data)
    return Response(serializer.errors, status=400)
