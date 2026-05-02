from decimal import Decimal

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser
from app.db.session import DBSession
from app.schemas.billing import (
    BalanceResponse,
    PromoRequest,
    TopupRequest,
    TransactionListResponse,
    TransactionOut,
)
from app.services import billing_service
from app.services.billing_service import (
    PromoAlreadyActivatedError,
    PromoCodeExhaustedError,
    PromoCodeExpiredError,
    PromoCodeInactiveError,
    PromoCodeNotFoundError,
)

router = APIRouter(prefix='/billing', tags=['billing'])


@router.get('/balance')
async def get_balance(
    current_user: CurrentUser,
    db: DBSession,
) -> BalanceResponse:
    wallet = await billing_service.get_wallet(str(current_user.id), db)
    return BalanceResponse(wallet_id=wallet.id, balance=wallet.balance)


@router.post('/topup', status_code=status.HTTP_201_CREATED)
async def topup(
    body: TopupRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> TransactionOut:
    tx = await billing_service.topup(
        str(current_user.id), Decimal(str(body.amount)), db
    )
    return TransactionOut.model_validate(tx)


@router.post('/promo', status_code=status.HTTP_201_CREATED)
async def activate_promo(
    body: PromoRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> TransactionOut:
    try:
        tx = await billing_service.activate_promo(str(current_user.id), body.code, db)
    except PromoCodeNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Promo code not found'
        )
    except PromoCodeInactiveError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail='Promo code is inactive'
        )
    except PromoCodeExpiredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail='Promo code has expired'
        )
    except PromoCodeExhaustedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Promo code has reached max activations',
        )
    except PromoAlreadyActivatedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Promo code already activated by this user',
        )

    return TransactionOut.model_validate(tx)


@router.get('/transactions')
async def list_transactions(
    current_user: CurrentUser,
    db: DBSession,
) -> TransactionListResponse:
    txs = await billing_service.get_transactions(str(current_user.id), db)
    items = [TransactionOut.model_validate(tx) for tx in txs]
    return TransactionListResponse(items=items, total=len(items))
