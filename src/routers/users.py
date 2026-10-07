from fastapi import APIRouter, Depends, status

from src.deps import get_user_service
from src.schemas.user import UserIn, UserOut
from src.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserIn,
    service: UserService = Depends(get_user_service),
) -> UserOut:
    return await service.create(payload)


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
) -> UserOut:
    return await service.get(user_id)
