import asyncio
import websockets
import json
from datetime import datetime, timezone
from .messages import MessageType
from common.utils.logger import get_logger

logger = get_logger("EVSE-ISO15118")

class EVSEServer:
    def __init__(self, host="localhost", port=9001):
        self.host = host
        self.port = port
        self._server = None  # WebSocket sunucusu

    async def start(self):
        """WebSocket sunucusunu başlatır."""
        logger.info(f"EVSE ISO15118 sunucusu başlatılıyor ws://{self.host}:{self.port}")
        self._server = await websockets.serve(self.handler, self.host, self.port)
        await self._server.wait_closed()

    async def handler(self, websocket, path):
        """Her yeni bağlantı için çalışır."""
        logger.info("EV bağlandı. Bağlantı başlatıldı.")
        try:
            async for message in websocket:
                await self.process_message(message, websocket)
        except websockets.ConnectionClosed:
            logger.info("Bağlantı kapandı.")

    async def process_message(self, message_str, websocket):
        """EV'den gelen tüm mesajları işler."""
        try:
            data = json.loads(message_str)
            msg_type = data.get("message_type")
            payload = data.get("payload", {})

            logger.info(f"EV mesajı alındı: {msg_type}")

            if msg_type == MessageType.CONNECTION_REQUEST:
                await self.handle_connection_request(payload, websocket)
            elif msg_type == MessageType.EV_INFORMATION_REQUEST:
                await self.handle_ev_information(payload, websocket)
            elif msg_type == MessageType.CHARGING_START_REQUEST:
                await self.handle_charging_start_request(payload, websocket)
            elif msg_type == MessageType.CHARGING_STOP_REQUEST:
                await self.handle_charging_stop_request(payload, websocket)

        except Exception as e:
            logger.error(f"Mesaj işleme hatası: {e}")

    async def handle_connection_request(self, payload, websocket):
        """EV bağlantı isteğini kabul eder."""
        response = {
            "message_type": MessageType.CONNECTION_RESPONSE,
            "timestamp": self._timestamp(),
            "payload": {"status": "Accepted"}
        }
        await websocket.send(json.dumps(response))
        logger.info("ConnectionResponse gönderildi.")

    async def handle_ev_information(self, payload, websocket):
        """EV hakkında bilgiler döner."""
        response = {
            "message_type": MessageType.EV_INFORMATION_RESPONSE,
            "timestamp": self._timestamp(),
            "payload": {
                "battery_capacity": 60,
                "current_soc": 35,
                "target_soc": 80,
                "charging_power": 22
            }
        }
        await websocket.send(json.dumps(response))
        logger.info("EVInformationResponse gönderildi.")

    async def handle_charging_start_request(self, payload, websocket):
        """Şarj başlatma isteğini işler ve CSMS'e iletir."""
        ev_id = payload.get("ev_id")
        evse_id = payload.get("evse_id")
        session_id = payload.get("session_id")
        charging_profile = payload.get("charging_profile", {})

        logger.info(f"Şarj başlatma isteği alındı: EV={ev_id}, EVSE={evse_id}, Profile={charging_profile}")

        now = self._timestamp()
        response = {
            "message_type": MessageType.CHARGING_START_RESPONSE,
            "timestamp": now,
            "payload": {
                "session_id": session_id,
                "status": "Accepted",
                "timestamp": now
            }
        }
        await websocket.send(json.dumps(response))
        logger.info(f"ChargingStartResponse gönderildi: EV {ev_id} - EVSE {evse_id}")

        await self.forward_start_to_csms(ev_id, evse_id)

    async def handle_charging_stop_request(self, payload, websocket):
        """Şarj durdurma isteğini işler ve CSMS'e iletir."""
        ev_id = payload.get("ev_id")
        evse_id = payload.get("evse_id")
        session_id = payload.get("session_id")
        reason = payload.get("reason", "Unknown")

        now = self._timestamp()
        response = {
            "message_type": MessageType.CHARGING_STOP_RESPONSE,
            "timestamp": now,
            "payload": {
                "session_id": session_id,
                "status": "Stopped",
                "timestamp": now
            }
        }
        await websocket.send(json.dumps(response))
        logger.info(f"ChargingStopResponse gönderildi: EV {ev_id} - EVSE {evse_id}")

        await self.forward_stop_to_csms(ev_id, evse_id, reason)

    async def forward_start_to_csms(self, ev_id, evse_id):
        """OCPP üzerinden şarj başlatma bilgisini CSMS'e iletir."""
        from state import connected_charge_points
        cp_id = f"CP_{evse_id}"
        cp = connected_charge_points.get(cp_id)
        if cp:
            await cp.send_transaction_event_started(evse_id)
            logger.info(f"CSMS'e şarj başlatma bildirildi: EVSE {evse_id} / EV {ev_id}")
        else:
            logger.warning(f"CSMS'e iletilemedi: CP {cp_id} bağlı değil.")

    async def forward_stop_to_csms(self, ev_id, evse_id, reason):
        """OCPP üzerinden şarj durdurma bilgisini CSMS'e iletir."""
        from state import connected_charge_points
        cp_id = f"CP_{evse_id}"
        cp = connected_charge_points.get(cp_id)
        if cp:
            await cp.send_transaction_event_ended(evse_id)
            logger.info(f"CSMS'e stop iletildi: EVSE {evse_id} / EV {ev_id}")
        else:
            logger.warning(f"CSMS'e iletilemedi: CP {cp_id} bağlı değil.")

    def _timestamp(self):
        return datetime.now(timezone.utc).isoformat() + "Z"
