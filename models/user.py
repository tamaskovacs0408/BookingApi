from typing import List, TYPE_CHECKING
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from dependencies.database import Base

if TYPE_CHECKING:
    from .appointment import Appointment

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key = True, index = True)
    name: Mapped[str] = mapped_column(String, index = True)
    email: Mapped[str] = mapped_column(String, unique = True, index = True)
    phone_number: Mapped[str] = mapped_column(String, nullable = True)
    hashed_password: Mapped[str] = mapped_column(String)
    appointments: Mapped[List["Appointment"]] = relationship(back_populates = "user", cascade = "all, delete-orphan")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default = False, nullable = False)