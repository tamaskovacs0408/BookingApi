from fastapi import FastAPI
from contextlib import asynccontextmanager
from routers import user, appointment
from dependencies.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Localhost for Nextjs frontend
    allow_methods=["*"],
    allow_headers=["*"],
)

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("Application starting... Creating database tables")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    print("Application shutdown...")


app = FastAPI(lifespan=lifespan)

app.include_router(user.router, prefix="/auth", tags=["Authentication"])
app.include_router(appointment.router, tags=["Appointments"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Booking API!"}
