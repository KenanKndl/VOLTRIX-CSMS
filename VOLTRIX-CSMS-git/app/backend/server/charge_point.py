# -----------------------------
# CHARGE POINT (EVSE)
# -----------------------------
import asyncio
import websockets
from datetime import datetime, timezone

from state import connected_charge_points

from ocpp.v201 import ChargePoint as CP
from ocpp.routing import on
from ocpp.v201 import call, call_result

from ocpp.v201.enums import (
    RegistrationStatusEnumType,        # Şarj istasyonunun CSMS tarafından kabul edilip edilmediğini belirtir
    TriggerReasonEnumType,             # TransactionEvent’in tetiklenme nedenini belirtir (örneğin: authorized, stop_authorized)
    ChargingStateEnumType,             # Şarj durumunu belirtir (örneğin: charging, idle)
    ReasonEnumType,                    # Transaction bitiş nedeni (örneğin: ev_disconnected)
    StandardizedUnitsOfMeasureType,    # Ölçü birimlerini belirtir (Wh, V, A gibi)
    MeasurandEnumType,                 # Ölçülen değer tipini belirtir (enerji, akım, voltaj vs.)
    ReserveNowStatusEnumType,          # Rezervasyon isteğinin durumunu belirtir
    ConnectorStatusEnumType,           # EVSE’nin mevcut durumu (available, occupied vs.)
    TransactionEventEnumType           # TransactionEvent türü (started, ended vs.)
)


from common.utils.logger import get_logger

logger = get_logger("ChargePoint")


class ChargePoint(CP):
    def __init__(self, id, websocket, initial_status=ConnectorStatusEnumType.available):
        super().__init__(id, websocket)
        self.initial_status = initial_status
        self.meter_task = None
        self.transaction_active = False

    # CSMS'ye BootNotification mesajı gönderir (istasyonun açıldığını bildirir)
    async def send_boot_notification(self):
        request = call.BootNotification(
            charging_station={"model": "VTX-EVSE", "vendor_name": "Voltrix"},
            reason="PowerUp"
        )
        response = await self.call(request)
        logger.info(f"BootNotification Response: {response.status}, Interval: {response.interval}")

        if response.status == RegistrationStatusEnumType.accepted:
            await self.send_authorize_request("voltrix-user")
            await self.send_status_notification(evse_id=1, status=self.initial_status)

    # Kimlik doğrulama (Authorize) isteği gönderir
    async def send_authorize_request(self, id_token: str = "voltrix-user"):
        request = call.Authorize(
            id_token={"id_token": id_token, "type": "Central"}
        )
        response = await self.call(request)
        status = response.id_token_info.get('status', 'Unknown')
        logger.info(f"Authorize Response: {status}")

    # Belirtilen EVSE için durum bildirimi gönderir
    async def send_status_notification(self, evse_id: int, status: ConnectorStatusEnumType, connector_id: int = 1):
        request = call.StatusNotification(
            timestamp=self.now(),
            connector_status=status,
            connector_id=connector_id,
            evse_id=evse_id
        )
        await self.call(request)
        logger.info(f"StatusNotification sent: {status} for EVSE {evse_id}")
        
    # Şarj başlatma işlemini bildirir ve sayaç verilerini göndermeye başlar
    async def send_transaction_event_started(self, evse_id: int):
        timestamp = self.now()
        transaction_id = f"tx-{self.id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        self.current_transaction_id = transaction_id

        request = call.TransactionEvent(
            event_type=TransactionEventEnumType.started,
            timestamp=timestamp,
            trigger_reason=TriggerReasonEnumType.authorized,
            seq_no=1,
            transaction_info={
                "transactionId": transaction_id,
            },
            meter_value=[
                {
                    "timestamp": timestamp,
                    "sampled_value": [
                        {
                            "value": 0,
                            "measurand": MeasurandEnumType.energy_active_import_register,
                            "unit_of_measure": {
                                "unit": StandardizedUnitsOfMeasureType.wh,
                                "multiplier": 0
                            }
                        }
                    ]
                }
            ],
            offline=False,
            evse={"id": evse_id},
            id_token={"idToken": "voltrix-user", "type": "Central"}
        )

        await self.call(request)
        logger.info(f"TransactionEvent STARTED sent. Transaction ID: {transaction_id}")
        self.transaction_active = True

        # MeterValues gönderimini başlat
        self.meter_task = asyncio.create_task(self.send_meter_values(evse_id))

        return transaction_id

    # Şarj işleminin bitişini bildirir ve sayaç verisi göndermeyi durdurur
    async def send_transaction_event_ended(self, evse_id: int):
        timestamp = self.now()

        request = call.TransactionEvent(
            event_type=TransactionEventEnumType.ended,
            timestamp=timestamp,
            trigger_reason=TriggerReasonEnumType.stop_authorized,
            seq_no=2,
            transaction_info={
                "transactionId": self.current_transaction_id,
                "stopped_reason": ReasonEnumType.ev_disconnected,
                "charging_state": ChargingStateEnumType.idle
            },
            meter_value=[
                {
                    "timestamp": timestamp,
                    "sampled_value": [
                        {
                            "value": 100,
                            "measurand": MeasurandEnumType.energy_active_import_register,
                            "unit_of_measure": {
                                "unit": StandardizedUnitsOfMeasureType.wh,
                                "multiplier": 0
                            }
                        }
                    ]
                }
            ],
            offline=False,
            evse={"id": evse_id},
            id_token={"idToken": "voltrix-user", "type": "Central"}
        )

        await self.call(request)
        logger.info(f"TransactionEvent ENDED sent. Transaction ID: {self.current_transaction_id}")
        self.transaction_active = False

        # MeterValues görevini durdur
        if self.meter_task and not self.meter_task.done():
            self.meter_task.cancel()
            logger.info("MeterValues task cancelled.")

    # Her 10 saniyede bir sayaç (voltaj, akım, enerji) verisi gönderir
    async def send_meter_values(self, evse_id: int):
        try:
            i = 0
            while self.transaction_active:
                await asyncio.sleep(10)  # 10 saniyede bir veri gönder
                timestamp = self.now()

                request = call.MeterValues(
                    evse_id=evse_id,
                    meter_value=[{
                        "timestamp": timestamp,
                        "sampled_value": [
                            {
                                "value": 1234 + i * 10,
                                "measurand": MeasurandEnumType.energy_active_import_register,
                                "unit_of_measure": {
                                    "unit": StandardizedUnitsOfMeasureType.wh,
                                    "multiplier": 0
                                }
                            },
                            {
                                "value": 230,
                                "measurand": MeasurandEnumType.voltage,
                                "unit_of_measure": {
                                    "unit": StandardizedUnitsOfMeasureType.v
                                }
                            },
                            {
                                "value": 16,
                                "measurand": MeasurandEnumType.current_import,
                                "unit_of_measure": {
                                    "unit": StandardizedUnitsOfMeasureType.a
                                }
                            }
                        ]
                    }]
                )
                await self.call(request)
                logger.info(f"MeterValues sent for EVSE {evse_id} at {timestamp}")
                i += 1

        except asyncio.CancelledError:
            logger.info("MeterValues task was cancelled gracefully.")

    # Her 10 saniyede bir CSMS'ye heartbeat (yaşıyorum) mesajı gönderir
    async def send_heartbeat(self):
        logger.info("Heartbeat started.")
        while True:
            await asyncio.sleep(10)
            timestamp = self.now()
            request = call.Heartbeat()
            response = await self.call(request)
            logger.info(f"Heartbeat sent at {timestamp}, CSMS responded with: {response.current_time}")

    # Aracın EVSE'ye takıldığını simüle eder
    async def plug_in_vehicle(self, evse_id: int):
        logger.info("Simulated plug-in initiated.")
        await self.send_status_notification(evse_id=evse_id, status=ConnectorStatusEnumType.occupied)

    # Şu anki zamanı ISO 8601 formatında döner
    def now(self):
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    # CSMS'den gelen rezervasyon isteğini kabul eder (simülasyon için her zaman kabul)
    @on('ReserveNow')
    async def on_reserve_now(self, id, expiry_date_time, id_token, evse_id, **kwargs):
        """
        Handles incoming ReserveNow requests from CSMS.
        For simulation purposes, we accept all reservations.
        """
        logger.info(f"ReserveNow received: EVSE {evse_id}, ID Token: {id_token.get('idToken')}")
        return call_result.ReserveNow(status=ReserveNowStatusEnumType.accepted)

    def now(self) -> str:
        """Return current UTC time in ISO 8601 format."""
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    
# Charge Point WebSocket'e bağlanır, başlangıç işlemlerini başlatır
async def run_charge_point(cp_id: str, initial_status: str):
    uri = f"ws://127.0.0.1:9000/{cp_id}"
    async with websockets.connect(uri, subprotocols=["ocpp2.0.1"]) as ws:
        cp = ChargePoint(cp_id, ws, initial_status=initial_status)
        connected_charge_points[cp_id] = cp  # ✅ BU SATIRI EKLE
        asyncio.create_task(cp.send_boot_notification())
        asyncio.create_task(cp.send_heartbeat())
        await cp.start()
