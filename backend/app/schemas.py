from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    display_name: str
    role: str
    status: str
    must_change_pwd: bool
    rejected_reason: str = ""
    created_at: datetime


class AccountCreate(BaseModel):
    username: str
    display_name: str


class BatchAccountCreate(BaseModel):
    items: list[AccountCreate]


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    version_no: int
    file_size: int
    created_at: datetime
    operator_name: str = ""


class AlbumOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    sort_order: int


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    action: str
    object_type: str
    object_name: str
    detail: str
    ip: str
    created_at: datetime
