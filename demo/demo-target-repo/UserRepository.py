"""Existing repository layer (correct pattern)."""


class UserRepository:
    @staticmethod
    def get_user(user_id: int) -> dict:
        return {"id": user_id}
