from typing import Optional

from pydantic import BaseModel


class ApiResponse(BaseModel):
    success: bool
    error: Optional[str] = None


class CredentialsResponse(ApiResponse):
    connected: bool = False
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    updated_at: Optional[str] = None


class BotControlRequest(BaseModel):
    action: Optional[str] = None
    running: Optional[bool] = None
    paper_trading: Optional[bool] = None
    mode: Optional[str] = None


class PaperModeRequest(BaseModel):
    enabled: bool


class ModeRequest(BaseModel):
    mode: str


class BalanceRequest(BaseModel):
    mode: str
    usdt_balance: Optional[float] = None
    inr_balance: Optional[float] = None
