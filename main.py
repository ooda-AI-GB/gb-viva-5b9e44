from fastapi import FastAPI, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from passlib.context import CryptContext
import datetime
from starlette.middleware.sessions import SessionMiddleware

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Session Middleware for simple auth (cookie-based)
# In production, use a secure secret key loaded from env vars
app.add_middleware(SessionMiddleware, secret_key="super-secret-key-mdo-poc")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_current_user(request: Request, db: Session = Depends(get_db)):
    username = request.session.get("user")
    if not username:
        return None
    return db.query(models.User).filter(models.User.username == username).first()

# --- Seeding ---
def seed_data(db: Session):
    if db.query(models.User).count() > 0:
        return

    print("Seeding data...")
    
    # Users
    users = [
        models.User(username="doctor1", hashed_password=get_password_hash("pass"), full_name="Dr. Smith", role="doctor"),
        models.User(username="doctor2", hashed_password=get_password_hash("pass"), full_name="Dr. Jones", role="doctor"),
        models.User(username="doctor3", hashed_password=get_password_hash("pass"), full_name="Dr. Williams", role="doctor"),
        models.User(username="doctor4", hashed_password=get_password_hash("pass"), full_name="Dr. Brown", role="doctor"),
        models.User(username="doctor5", hashed_password=get_password_hash("pass"), full_name="Dr. Davis", role="doctor"),
        models.User(username="head", hashed_password=get_password_hash("pass"), full_name="Dr. Head", role="head"),
        models.User(username="admin", hashed_password=get_password_hash("pass"), full_name="Admin User", role="admin"),
    ]
    db.add_all(users)
    db.commit()

    # Refresh to get IDs
    docs = db.query(models.User).filter(models.User.role == "doctor").all()
    
    # Meetings (15)
    types = ["Department", "CME", "Hospital-wide"]
    meetings = []
    for i in range(15):
        m = models.Meeting(
            title=f"Meeting {i+1}",
            date=datetime.date.today() - datetime.timedelta(days=i*2),
            meeting_type=types[i % 3]
        )
        meetings.append(m)
    db.add_all(meetings)
    db.commit()

    # Attendance
    for m in meetings:
        for d in docs:
            # Random attendance
            import random
            status = random.choice(["Present", "Absent", "Excused"])
            db.add(models.Attendance(meeting_id=m.id, user_id=d.id, status=status))
    db.commit()

    # Clinic Slots (10)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    slots = []
    for i in range(10):
        slots.append(models.ClinicSlot(
            day_of_week=days[i % 5],
            start_time=f"{8 + (i%4)}:00",
            end_time=f"{12 + (i%4)}:00",
            user_id=docs[i % 5].id
        ))
    db.add_all(slots)
    db.commit()

    # Service Entries (8)
    procedures = ["Appendectomy", "Cholecystectomy", "Hernia Repair", "Consultation", "Teaching Rounds"]
    for i in range(8):
        db.add(models.ServiceEntry(
            date=datetime.date.today() - datetime.timedelta(days=i),
            procedure_name=procedures[i % 5],
            user_id=docs[i % 5].id,
            notes=f"Routine procedure {i+1}"
        ))
    db.commit()

    # Research Items (5)
    research = [
        ("New Techniques in Surgery", "Publication", "Published"),
        ("Annual Medical Conference", "Presentation", "Submitted"),
        ("Cardiology Trial Phase 1", "Trial", "Approved"),
        ("Pediatric Care Review", "Publication", "Submitted"),
        ("Grand Rounds Presentation", "Presentation", "Published")
    ]
    for i, (title, rtype, status) in enumerate(research):
        db.add(models.ResearchItem(
            title=title,
            research_type=rtype,
            status=status,
            user_id=docs[i % 5].id
        ))
    db.commit()
    print("Seeding complete.")

@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    seed_data(db)
    db.close()

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/login")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    
    request.session["user"] = user.username
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/login")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    # Calculate stats
    total_meetings = db.query(models.Meeting).count() # Simply count all for POC
    clinic_sessions = db.query(models.ClinicSlot).count()
    procedures = db.query(models.ServiceEntry).count()
    research = db.query(models.ResearchItem).count()

    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user": user,
        "stats": {
            "meetings": total_meetings,
            "clinics": clinic_sessions,
            "procedures": procedures,
            "research": research
        }
    })

@app.get("/meetings", response_class=HTMLResponse)
async def meetings(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    if user.role == "admin" or user.role == "head":
        attendance = db.query(models.Attendance).all()
    else:
        attendance = db.query(models.Attendance).filter(models.Attendance.user_id == user.id).all()
        
    return templates.TemplateResponse("meetings.html", {"request": request, "user": user, "attendance": attendance})

@app.get("/schedule", response_class=HTMLResponse)
async def schedule(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    slots = db.query(models.ClinicSlot).all()
    return templates.TemplateResponse("schedule.html", {"request": request, "user": user, "slots": slots})

@app.get("/services", response_class=HTMLResponse)
async def services(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    entries = db.query(models.ServiceEntry).order_by(models.ServiceEntry.date.desc()).all()
    return templates.TemplateResponse("services.html", {"request": request, "user": user, "entries": entries})

@app.post("/services")
async def add_service(
    request: Request, 
    procedure_name: str = Form(...), 
    notes: str = Form(...), 
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    new_entry = models.ServiceEntry(
        procedure_name=procedure_name,
        notes=notes,
        user_id=user.id,
        date=datetime.date.today()
    )
    db.add(new_entry)
    db.commit()
    return RedirectResponse(url="/services", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/research", response_class=HTMLResponse)
async def research(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    items = db.query(models.ResearchItem).all()
    return templates.TemplateResponse("research.html", {"request": request, "user": user, "items": items})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
