from pydantic import BaseModel
from typing import Optional

class EVBase(BaseModel):
    id: str
    brand: str
    model: str
    battery_capacity_kWh: float
    consumption_kWh_per_km: float
