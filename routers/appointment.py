from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.appointment import Appointment
from models.user import User
from schemas.appointment import AppointmentCreate, AppointmentOut, PublicAppointmentOut
from dependencies.database import get_db
from dependencies.auth import get_current_user
from datetime import datetime, timedelta, timezone
from fastapi_mail import FastMail, MessageSchema
from services.email import conf

router = APIRouter()

@router.post(
    "/appointments",
    response_model=AppointmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def book_appointment(
    appointment: AppointmentCreate,
    background_tasks: BackgroundTasks, # <-- ÚJ DEPENDENCY
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ... a meglévő logika a foglalás ellenőrzésére és mentésére ...
    db_appointment = Appointment(...)
    db.add(db_appointment)
    await db.commit()
    await db.refresh(db_appointment)

    # --- ÉRTESÍTŐ E-MAIL KÜLDÉSE ---
    try:
        # A műkörmös e-mail címe (ezt is betehetnéd a .env fájlba)
        nail_technician_email = "mukormos.email@example.com"
        
        message = MessageSchema(
            subject=f"Új időpontfoglalás: {appointment.name}",
            recipients=[nail_technician_email],
            body=f"Új időpontfoglalás érkezett:\n\n"
                 f"Név: {appointment.name}\n"
                 f"Időpont: {db_appointment.start_time.strftime('%Y-%m-%d %H:%M')}\n"
                 f"Foglaló: {current_user.name} ({current_user.email}, Tel: {current_user.phone_number})\n",
            subtype="plain"
        )
        
        fm = FastMail(conf)
        background_tasks.add_task(fm.send_message, message)
    except Exception as e:
        # Hiba esetén se álljon le a folyamat, csak jelezzük a konzolon
        print(f"Hiba az értesítő e-mail küldésekor: {e}")

    return db_appointment

@router.delete(
    "/appointments/{appointment_id}",
    status_code = status.HTTP_204_NO_CONTENT,
    summary = "Időpont törlése"
)
async def delete_appointment(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    db_appointment = result.scalar_one_or_none()

    if not db_appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Időpont nem található.")

    is_owner = db_appointment.user_id == current_user.id
    is_admin = current_user.is_superuser

    # Jogosultság ellenőrzése: Csak a tulajdonos vagy egy admin törölhet.
    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nincs jogosultságod törölni ezt az időpontot."
        )

    # Határidő ellenőrzése (ez csak a sima felhasználókra vonatkozik!)
    if is_owner and not is_admin:
        # Feltételezzük, hogy az adatbázisban UTC idő van tárolva.
        time_until_appointment = db_appointment.start_time - datetime.now(timezone.utc)
        if time_until_appointment < timedelta(hours=24):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Az időpont 24 órán belül már nem törölhető."
            )
            
    await db.delete(db_appointment)
    await db.commit()

@router.get(
    "/appointments/public",
    response_model=list[PublicAppointmentOut],
    summary="Minden foglalt időpont listázása (publikus)"
)
async def get_all_booked_appointments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Appointment).order_by(Appointment.start_time))
    appointments = result.scalars().all()
    # Itt a Pydantic automatikusan a PublicAppointmentOut sémára konvertál,
    # elhagyva a user_id-t és egyéb mezőket.
    return appointments

@router.get(
    "/appointments/me",
    response_model = list[AppointmentOut],
    summary = "Saját időpontok listázása (bejelentkezés szükséges)"
)
async def get_my_appointments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Appointment)
        .where(Appointment.user_id == current_user.id)
        .order_by(Appointment.start_time)
    )
    appointments = result.scalars().all()
    return appointments