from pydantic import BaseModel, Field

class EVSEBase(BaseModel):
    name: str
    brand: str
    model: str
    vendor: str
    latitude: float
    longitude: float
    max_power_kW: float = Field(..., gt=0, description="Maximum charging power in kW")
