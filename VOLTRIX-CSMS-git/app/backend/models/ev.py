from typing import Optional
from .ev_base import EVBase


class EV(EVBase):
    current_soc: float  # Mevcut şarj seviyesi (%)
    target_soc: float   # Kullanıcının istediği şarj seviyesi (%)
    location_lat: float
    location_long: float
    connected_evse_id: Optional[str] = None

    def get_required_energy_kWh(self) -> float:
        """Hedefe ulaşmak için gereken enerji miktarı (kWh)."""
        delta_percent = max(self.target_soc - self.current_soc, 0)
        return (delta_percent / 100) * self.battery_capacity_kWh

    def get_estimated_range_km(self) -> float:
        """Mevcut şarjla kaç km yol alınabileceğini hesaplar."""
        return (self.current_soc / 100) * self.battery_capacity_kWh / self.consumption_kWh_per_km

    def get_target_range_km(self) -> float:
        """Hedeflenen şarjla ulaşılan menzili hesaplar."""
        return (self.target_soc / 100) * self.battery_capacity_kWh / self.consumption_kWh_per_km

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "brand": self.brand,
            "model": self.model,
            "battery_capacity_kWh": self.battery_capacity_kWh,
            "consumption_kWh_per_km": self.consumption_kWh_per_km,
            "current_soc": self.current_soc,
            "target_soc": self.target_soc,
            "location_lat": self.location_lat,
            "location_long": self.location_long,
            "connected_evse_id": self.connected_evse_id,
            "estimated_range_km": self.get_estimated_range_km(),
            "required_energy_kWh": self.get_required_energy_kWh()
        }
