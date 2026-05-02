from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.db.session import DBSession
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.services import auth_service
from app.services.auth_service import EmailAlreadyExistsError, InvalidCredentialsError

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DBSession) -> RegisterResponse:
    try:
        user = await auth_service.register(body.email, body.password, db)
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail='Email already registered'
        )

    return RegisterResponse(user_id=user.id, email=user.email)


@router.post('/login')
async def login(body: LoginRequest, db: DBSession) -> TokenResponse:
    try:
        user = await auth_service.authenticate(body.email, body.password, db)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials'
        )

    user_id = str(user.id)
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post('/refresh')
async def refresh(body: RefreshRequest) -> AccessTokenResponse:
    try:
        user_id = decode_refresh_token(body.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid refresh token'
        )

    return AccessTokenResponse(access_token=create_access_token(user_id))


@router.get('/me')
async def me(current_user: CurrentUser) -> MeResponse:
    return MeResponse(
        user_id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at,
    )
