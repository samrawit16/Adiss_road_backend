import logging
import os

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.errors import AppError
from app.routers import auth, hotspots, severity, users, safety, oauth, biometric, admin, notifications, uploads


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)


app = FastAPI(
    title="Aiss Road API",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, prefix="/api/v1")
app.include_router(hotspots.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(severity.router, prefix="/api/v1")
app.include_router(safety.router, prefix="/api/v1")
app.include_router(oauth.router, prefix="/api/v1")
app.include_router(biometric.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")

from app.core.config import settings as _settings
os.makedirs("./admin_dashboard", exist_ok=True)
if _settings.storage_backend == "db":
    # Photos live in the database (free hosts erase the disk); serve them from there.
    app.include_router(uploads.router)
else:
    os.makedirs(_settings.profile_image_dir, exist_ok=True)
    os.makedirs(_settings.evidence_image_dir, exist_ok=True)
    app.mount("/uploads/profiles", StaticFiles(directory=_settings.profile_image_dir), name="profiles")
    app.mount("/uploads/evidence", StaticFiles(directory=_settings.evidence_image_dir), name="evidence")
app.mount("/admin", StaticFiles(directory="./admin_dashboard", html=True), name="admin_dashboard")


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "code": exc.code
        }
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def startup():
   
    if _settings.is_production:
        problems = _settings.production_problems()
        if problems:
            raise RuntimeError(
                "Refusing to start in production with unsafe settings:\n  - " + "\n  - ".join(problems)
            )

    from app.db import base  # noqa: F401 ensures models are imported
    from app.db.session import Base, engine

    Base.metadata.create_all(bind=engine)

    # Default police-dashboard admin (see DEFAULT_ADMIN_* in .env).
    from app.db.session import SessionLocal as _Session
    from app.services.admin_bootstrap import ensure_default_admin
    with _Session() as _db:
        ensure_default_admin(_db)

    
    from app.models.safety import Authority
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        if db.query(Authority).count() == 0:
            db.add_all([
                Authority(name="Addis Ababa Police Commission", authority_type="police", phone="991", latitude=9.03, longitude=38.74, coverage_area="Addis Ababa", is_active=True),
                Authority(name="Federal Police", authority_type="police", phone="915", latitude=9.025, longitude=38.755, coverage_area="Addis Ababa", is_active=True),
                Authority(name="Fire and Emergency Service", authority_type="fire_emergency", phone="912", latitude=9.015, longitude=38.745, coverage_area="Addis Ababa", is_active=True),
                Authority(name="Red Cross Emergency Support", authority_type="medical_support", phone="907", latitude=9.02, longitude=38.73, coverage_area="Addis Ababa", is_active=True),
            ])
            db.commit()

   
    try:
        from app.models.hotspot import Hotspot
        from scripts.seed_risk_profiles import CSV_PATH, build_profiles
        if not os.path.exists(CSV_PATH):
            logging.getLogger(__name__).warning("RTA hotspot dataset not found: %s", CSV_PATH)
        else:
            with SessionLocal() as db:
                if db.query(Hotspot).count() == 0:
                    profiles = build_profiles(CSV_PATH)
                    for _, row in profiles.iterrows():
                        db.add(Hotspot(
                            area=row["Area_accident_occured"],
                            junction_type=row["Types_of_Junction"],
                            accidents=int(row["accidents"]),
                            fatalities=int(row["fatalities"]),
                            injuries=int(row["injuries"]),
                            risk_score=float(row["risk_score"]),
                            peak_hour=int(row["peak_hour"]),
                            severity=row["severity"],
                        ))
                    db.commit()
                    logging.getLogger(__name__).info("Loaded %s hotspot records from the RTA dataset.", len(profiles))
    except Exception as exc:
        logging.getLogger(__name__).warning("Could not auto-load hotspot records: %s", exc)


    if _settings.seed_demo_data:
        from app.services.demo_seed import seed_demo_data
        with SessionLocal() as db:
            seed_demo_data(db)
