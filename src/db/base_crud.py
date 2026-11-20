from typing import List, Optional, Type, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy import select

T = TypeVar("T")

class BaseCRUD:
    model: Type[T]

    @classmethod
    def get_by_id(cls, session: Session, obj_id: int) -> Optional[T]:
        return session.get(cls.model, obj_id)

    @classmethod
    def list_all(cls, session: Session) -> List[T]:
        return session.scalars(select(cls.model)).all()

    @classmethod
    def create(cls, session: Session, obj: T) -> T:
        session.add(obj)
        session.flush()
        return obj

    @classmethod
    def batch_create(cls, session: Session, obj_list: List[T]) -> List[T]:
        session.add_all(obj_list)
        session.flush()
        return obj_list

    @classmethod
    def delete(cls, session: Session, obj: T):
        session.delete(obj)
