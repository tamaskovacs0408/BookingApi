from pydantic import BaseModel, field_validator
from datetime import datetime
import pytz


class AppointmentCreate(BaseModel):
    name: str
    start_time: datetime

    @field_validator("start_time")
    @classmethod
    def convert_to_utc(cls, v: datetime) -> datetime:
        """
        A naiv időpontokat (amelyeket a kliens küld) Magyarországi időként
        értelmezi, és átalakítja őket UTC időzónára az adatbázisban való
        tároláshoz.
        """
        # Ha a kapott időpont "naiv" (nincs rajta időzóna információ)
        if v.tzinfo is None:
            budapest_tz = pytz.timezone("Europe/Budapest")
            # 1. Hozzárendeljük a budapesti időzónát
            aware_time = budapest_tz.localize(v)
            # 2. Átalakítjuk UTC-re
            return aware_time.astimezone(pytz.utc)
        
        # Ha már eleve időzóna-aware, akkor is átalakítjuk UTC-re a konzisztencia miatt
        return v.astimezone(pytz.utc)


class AppointmentOut(BaseModel):
    id: int
    user_id: int
    name: str
    start_time: datetime

    model_config = {
        "from_attributes": True
    }

class PublicAppointmentOut(BaseModel):
    start_time: datetime