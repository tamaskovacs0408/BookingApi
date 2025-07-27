from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from dependencies.database import Base
from datetime import datetime
from .user import User


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(primary_key = True, index = True)
    name: Mapped[str] = mapped_column(index = True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone = True), nullable = False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable = False)
    user: Mapped["User"] = relationship(back_populates = "appointments")
    __table_args__ = (UniqueConstraint("start_time", name = "unique_start_time"),)