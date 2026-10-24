from fastapi import APIRouter, Depends, Request, status, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_active_user
from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    RefreshRequest,
    LogoutRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    RequestOTPRequest,
    VerifyOTPRequest,
    ResetPasswordWithOTPRequest,
    MessageResponse
)
from app.services.auth_service import (
    register_user,
    authenticate_user,
    create_user_tokens,
    refresh_user_token,
    logout_user,
    forgot_password_service,
    reset_password_service,
    request_otp_service,
    verify_otp_service,
    reset_password_with_otp_service
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user"
)
def register(
    user_in: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new user with email, password, and full name.
    """
    user = register_user(db=db, user_in=user_in)
    return user


from app.services.activity_log_service import log_activity


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue JWT tokens"
)
def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticate email and password, creating a login session and returning JWT tokens.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        user = authenticate_user(db=db, email=credentials.email, password=credentials.password)
    except HTTPException as e:
        log_activity(
            db=db,
            action="login_failed",
            user_id=None,
            entity_type="user",
            description=f"Failed login attempt for email {credentials.email}",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"email": credentials.email, "status_code": e.status_code},
        )
        try:
            from app.services import security_monitoring
            security_monitoring.track_failed_login(
                db=db,
                email=credentials.email,
                ip_address=ip_address,
                user_agent=user_agent,
                status_code=e.status_code,
            )
        except Exception:
            pass
        raise e

    tokens = create_user_tokens(
        db=db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent
    )

    log_activity(
        db=db,
        action="login_success",
        user_id=user.id,
        entity_type="user",
        entity_id=str(user.id),
        description=f"User {user.email} logged in successfully",
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token using refresh JWT token"
)
def refresh_token(
    req: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Validate refresh token and issue a new short-lived access token.
    """
    return refresh_user_token(db=db, refresh_token=req.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout user and revoke refresh token"
)
def logout(
    req: LogoutRequest,
    db: Session = Depends(get_db)
):
    """
    Revoke refresh token session and set status to inactive.
    """
    res = logout_user(db=db, refresh_token=req.refresh_token)
    log_activity(
        db=db,
        action="logout",
        entity_type="user",
        description="User logged out and revoked refresh token",
    )
    return res


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request password reset token"
)
def forgot_password(
    req: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Generate password reset token. Obscures account presence for security.
    """
    return forgot_password_service(db=db, email=req.email)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password using reset token"
)
def reset_password(
    req: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset user password using a valid reset token.
    """
    return reset_password_service(db=db, token=req.token, new_password=req.new_password)


@router.post(
    "/forgot-password/request-otp",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request OTP for password reset"
)
def request_otp(
    req: RequestOTPRequest,
    db: Session = Depends(get_db)
):
    """
    Generate and send OTP to registered email for password reset.
    Obscures account presence for security.
    """
    return request_otp_service(db=db, email=req.email)


@router.post(
    "/forgot-password/verify-otp",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP for password reset"
)
def verify_otp(
    req: VerifyOTPRequest,
    db: Session = Depends(get_db)
):
    """
    Verify OTP before allowing password reset.
    """
    return verify_otp_service(db=db, email=req.email, otp=req.otp)


@router.post(
    "/forgot-password/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password using OTP"
)
def reset_password_with_otp(
    req: ResetPasswordWithOTPRequest,
    db: Session = Depends(get_db)
):
    """
    Reset user password using verified OTP.
    """
    if req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    return reset_password_with_otp_service(
        db=db,
        email=req.email,
        otp=req.otp,
        new_password=req.new_password
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile"
)
def get_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Fetch user profile using Bearer JWT access token.
    """
    return current_user
