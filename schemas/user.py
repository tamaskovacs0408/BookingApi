import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

def validate_password_strength(v: str) -> str:
    """
    Ellenőrzi, hogy a jelszó megfelel-e a biztonsági követelményeknek.
    (Minimum 8 karakter, kis- és nagybetű, szám, speciális karakter).
    A 8 karakteres hosszt a Field() kezeli, itt a többit validáljuk.
    """
    if not re.search(r"[a-z]", v):
        raise ValueError("A jelszónak tartalmaznia kell legalább egy kisbetűt.")
    if not re.search(r"[A-Z]", v):
        raise ValueError("A jelszónak tartalmaznia kell legalább egy nagybetűt.")
    if not re.search(r"\d", v):
        raise ValueError("A jelszónak tartalmaznia kell legalább egy számot.")
    if not re.search(r"[^A-Za-z0-9]", v):
        raise ValueError("A jelszónak tartalmaznia kell legalább egy speciális karaktert.")
    return v

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone_number: str = None

class UserCreate(UserBase):
    password: str = Field(
        min_length=8,
        description="Minimum 8 karakter, kis- és nagybetű, szám, speciális karakter."
    )

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        return validate_password_strength(v)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(UserBase):
    id: int
    is_superuser: bool

    model_config = {"from_attributes": True}

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(
        min_length=8,
        description="Minimum 8 karakter, kis- és nagybetű, szám, speciális karakter."
    )

    @field_validator("new_password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        return validate_password_strength(v)

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(
        min_length=8,
        description="Minimum 8 karakter, kis- és nagybetű, szám, speciális karakter."
    )
    
    @field_validator("new_password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        return validate_password_strength(v)
