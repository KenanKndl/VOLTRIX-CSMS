from datetime import datetime
from typing import Optional
from .evse_base import EVSEBase
from ocpp.v201.enums import ConnectorStatusEnumType

class EVSE(EVSEBase):
    id: Optional[int] = None
    status: ConnectorStatusEnumType
    current_ev_id: Optional[str] = None
    charging_start_time: Optional[datetime] = None
    estimated_finish_time: Optional[datetime] = None

    def is_available(self) -> bool:
        return self.status == ConnectorStatusEnumType.available

    def is_busy(self) -> bool:
        return self.status in [ConnectorStatusEnumType.occupied, ConnectorStatusEnumType.reserved]

    def reserve(self, ev_id: str):
        self.status = ConnectorStatusEnumType.reserved
        self.current_ev_id = ev_id

    def start_charging(self):
        self.status = ConnectorStatusEnumType.occupied
        self.charging_start_time = datetime.now()

    def stop_charging(self):
        self.status = ConnectorStatusEnumType.available
        self.current_ev_id = None
        self.charging_start_time = None
        self.estimated_finish_time = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "model": self.model,
            "vendor": self.vendor,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "max_power_kW": self.max_power_kW,
            "status": self.status.value,
            "current_ev_id": self.current_ev_id,
            "charging_start_time": str(self.charging_start_time) if self.charging_start_time else None,
            "estimated_finish_time": str(self.estimated_finish_time) if self.estimated_finish_time else None
        }
