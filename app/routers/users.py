
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.staticfiles import StaticFiles
import os

from app.core.deps import get_current_user
from app.core.errors import AppError, ValidationError
from app.models.user import User
from app.schemas.user import ProfileImageOut, UserOut, UserUpdate
from app.db.session import get_db
from app.services import file_store
from app.services.profile_image_service import save_profile_image

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return current


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdate, current: User = Depends(get_current_user),
              db=Depends(get_db)):
    if body.full_name is not None:
        current.full_name = body.full_name
    if body.phone is not None:
        current.phone = body.phone
    db.commit()
    db.refresh(current)
    return current


@router.post("/me/profile-image", response_model=ProfileImageOut)
async def upload_profile_image(file: UploadFile = File(...),
                               current: User = Depends(get_current_user),
                               db=Depends(get_db)):
    """Upload a profile image (JPEG/PNG/WebP, max 5 MB). The image is
    re-encoded (metadata stripped) and served from /uploads/profiles."""
    path = await save_profile_image(current.id, file, db)
    # remove the previous image so uploads do not pile up
    old = current.profile_image_path
    if old and not file_store.delete_stored(db, old) and os.path.exists(old):
        try:
            os.remove(old)
        except OSError:
            pass
    current.profile_image_path = path
    db.commit()
    filename = os.path.basename(path)
    return ProfileImageOut(profile_image_url=f"/uploads/profiles/{filename}")
