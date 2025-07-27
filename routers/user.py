from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from models.user import User
from dependencies.database import get_db
from dependencies.auth import get_current_user
from schemas.user import ( UserCreate, UserLogin, UserOut, UserUpdate, PasswordUpdate, PasswordResetRequest, PasswordReset )
from services.auth import (
    hash_password, verify_password, create_access_token, create_password_reset_token, verify_password_reset_token
)
from fastapi_mail import FastMail, MessageSchema
from services.email import conf

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED,)

async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user.email))

    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ez az e-mail cím már regisztrálva van.")
    
    db_user = User(
        name = user.name,
        email = user.email,
        phone_number = user.phone_number,
        hashed_password = hash_password(user.password)
    )

    db.add(db_user)

    await db.commit()

    await db.refresh(db_user)

    return db_user


@router.post("/login", response_model=Token)

async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user.email))

    db_user = result.scalar_one_or_none()

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid credentials",
            headers = {"WWW-Authenticate": "Bearer"}
            )
    
    token = create_access_token({"sub": str(db_user.id)})

    return {"access_token": token, "token_type": "bearer"}


@router.delete(
    "/users/{user_id}",
    status_code = status.HTTP_204_NO_CONTENT,
    summary = "Delete user"
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user_to_delete = result.scalar_one_or_none()
    
    if not user_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Felhasználó nem található.")
    
    is_admin = current_user.is_superuser
    is_self = current_user.id == user_to_delete.id
    
    if not is_admin and not is_self:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nincs jogosultságod a felhasználó törléséhez.")

    if is_admin and is_self:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Adminisztrátor nem törölheti saját magát.")

    await db.delete(user_to_delete)
    await db.commit()

@router.patch("/users/{user_id}", response_model=UserOut, summary="Felhasználói profil módosítása")
async def update_user_profile(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Felhasználó nem található.")

    # Jogosultság: csak admin vagy a felhasználó maga módosíthat
    if not current_user.is_superuser and current_user.id != db_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nincs jogosultság a módosításhoz.")

    # A kapott adatokat (amik nem None) frissítjük az adatbázis objektumon
    update_data = user_update.model_dump(exclude_unset=True)
    
    # E-mail egyediségének ellenőrzése, ha megváltozott
    if "email" in update_data and update_data["email"] != db_user.email:
        result = await db.execute(select(User).where(User.email == update_data["email"]))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ez az e-mail cím már foglalt.")
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
        
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.put("/users/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT, summary="Jelszó módosítása")
async def update_password(
    user_id: int,
    password_update: PasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalar_one_or_none()
    
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Felhasználó nem található.")

    is_admin = current_user.is_superuser
    is_self = current_user.id == db_user.id

    if not is_admin and not is_self:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nincs jogosultság a módosításhoz.")
        
    # Ha nem admin, akkor ellenőrizni kell a régi jelszót
    if not is_admin:
        if not verify_password(password_update.current_password, db_user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A jelenlegi jelszó hibás.")

    # Az új jelszó hash-elése és mentése
    db_user.hashed_password = hash_password(password_update.new_password)
    await db.commit()

# --- ÚJ VÉGPONT: Elfelejtett jelszó - Token kérése ---
@router.post("/forgot-password", summary="Jelszó-visszaállító token kérése")
async def request_password_reset(
    request: PasswordResetRequest, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if user:
        password_reset_token = create_password_reset_token(email=user.email)
        
        template_body = {
            "name": user.name,
            # Ide egy frontend URL-t kellene tenni, ami feldolgozza a tokent
            "reset_url": f"http://localhost:3000/reset-password?token={password_reset_token}" 
        }

        message = MessageSchema(
            subject = "Jelszó-visszaállítási kérelem",
            recipients = [user.email],
            template_body = template_body,
            subtype = "html"
        )
        
        fm = FastMail(conf)
        # Email küldés a háttérben
        background_tasks.add_task(fm.send_message, message)
        
    return {"message": "Ha létezik ilyen e-mail cím, elküldtük a visszaállításhoz szükséges utasításokat."}


# --- ÚJ VÉGPONT: Elfelejtett jelszó - Új jelszó beállítása ---
@router.post("/reset-password", summary="Jelszó visszaállítása token segítségével")
async def reset_password(
    password_reset: PasswordReset,
    db: AsyncSession = Depends(get_db)
):
    email = verify_password_reset_token(password_reset.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Érvénytelen vagy lejárt token."
        )
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="A tokenhez tartozó felhasználó nem található."
        )
        
    user.hashed_password = hash_password(password_reset.new_password)
    await db.commit()
    
    return {"message": "A jelszó sikeresen megváltoztatva."}