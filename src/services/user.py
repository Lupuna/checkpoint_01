from src.exceptions import UserNotFoundError
from src.repositories.user import UserRepository
from src.schemas.user import UserIn, UserOut


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def create(self, payload: UserIn) -> UserOut:
        return await self.user_repository.create_user(payload.title)

    async def get(self, user_id: int) -> UserOut:
        user = await self.user_repository.get_user(user_id)
        if user is None:
            raise UserNotFoundError("user")
        return user
