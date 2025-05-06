import asyncio
import websockets
import json
from datetime import datetime, timezone
from .messages import MessageType
from common.utils.logger import get_logger

logger = get_logger("EV-ISO15118")

class EVClient:
    def __init__(self, ev_id: str, evse_id: int, uri="ws://localhost:9001"):
        self.ev_id = ev_id  # Aracın kimliği
        self.evse_id = evse_id  # Bağlandığı şarj noktası
        self.uri = uri  # Bağlantı adresi
        self.session_id = f"session-{ev_id}-{datetime.now(timezone.utc).timestamp()}"  # Oturum ID'si
        self.websocket = None  # WebSocket bağlantı nesnesi

    # EV bağlantısını başlatır, gerekli başlangıç mesajlarını yollar ve gelen yanıtları dinler.
    async def connect(self):
        """EV bağlantısını başlatır ve dinleme döngüsüne girer."""
        async with websockets.connect(f"{self.uri}/iso15118") as websocket:
            self.websocket = websocket
            logger.info("EV bağlantısı başlatıldı.")
            await self.send_connection_request()
            await self.send_ev_information_request()
            asyncio.create_task(self.monitor_soc())  # SOC %100 olunca şarjı durdur

            while True:
                message = await websocket.recv()
                await self.handle_response(message)

    # EV'nin EVSE'ye bağlantı isteği göndermesini sağlar.
    async def send_connection_request(self):
        """EV → EVSE bağlantı isteği gönder."""
        if not self.websocket:
            return
        message = {
            "message_type": MessageType.CONNECTION_REQUEST,
            "timestamp": self._timestamp(),
            "payload": {
                "ev_id": self.ev_id,
                "evse_id": self.evse_id,
                "session_id": self.session_id,
                "protocol_version": "1.0"
            }
        }
        await self.websocket.send(json.dumps(message))
        logger.info("ConnectionRequest gönderildi.")

    # EV'nin araç bilgilerini (örneğin batarya durumu) talep ettiği mesajı gönderir.
    async def send_ev_information_request(self):
        """EV → EVSE araç bilgilerini gönderir (battery, SOC vs)."""
        if not self.websocket:
            return
        message = {
            "message_type": MessageType.EV_INFORMATION_REQUEST,
            "timestamp": self._timestamp(),
            "payload": {
                "session_id": self.session_id
            }
        }
        await self.websocket.send(json.dumps(message))
        logger.info("EVInformationRequest gönderildi.")

    # EV'nin şarj başlatma talebini EVSE'ye iletmesini sağlar.
    async def send_charging_start_request(self):
        """Şarj başlatma talebi gönder."""
        if not self.websocket:
            logger.warning("WebSocket bağlantısı yok, şarj başlatılamaz.")
            return
        message = {
            "message_type": MessageType.CHARGING_START_REQUEST,
            "timestamp": self._timestamp(),
            "payload": {
                "session_id": self.session_id,
                "ev_id": self.ev_id,
                "evse_id": self.evse_id,
                "charging_profile": {
                    "energy_amount_kWh": 20,
                    "target_soc": 80
                }
            }
        }
        await self.websocket.send(json.dumps(message))
        logger.info("ChargingStartRequest gönderildi.")

    # EV'nin şarjı durdurmak için EVSE'ye talep göndermesini sağlar.
    async def send_charging_stop_request(self, reason="UserStopped"):
        """Şarj durdurma talebi gönder."""
        if not self.websocket:
            logger.warning("WebSocket bağlantısı yok, şarj durdurulamaz.")
            return
        message = {
            "message_type": MessageType.CHARGING_STOP_REQUEST,
            "timestamp": self._timestamp(),
            "payload": {
                "session_id": self.session_id,
                "ev_id": self.ev_id,
                "evse_id": self.evse_id,
                "reason": reason
            }
        }
        await self.websocket.send(json.dumps(message))
        logger.info("ChargingStopRequest gönderildi.")

    # EVSE'den gelen tüm yanıtları işler ve loglar.
    async def handle_response(self, message_str):
        """EVSE'den gelen yanıtları işler."""
        try:
            message = json.loads(message_str)
            msg_type = message.get("message_type")
            payload = message.get("payload", {})
            logger.info(f"Gelen yanıt: {msg_type} - Payload: {payload}")
        except Exception as e:
            logger.error(f"Yanıt işleme hatası: {e}")

    # Batarya doluluk oranını (SOC) simüle eder, %100 olunca şarjı durdurur.
    async def monitor_soc(self):
        """Simüle edilmiş SOC takibi, %100 olunca şarjı durdurur."""
        soc = 35  # örnek SOC
        while soc < 100:
            await asyncio.sleep(5)
            soc += 5
            logger.info(f"Simüle edilen SOC: {soc}%")

        logger.info("SOC %100 oldu. ChargingStopRequest gönderiliyor...")
        await self.send_charging_stop_request(reason="FullyCharged")

    # UTC formatında zaman damgası döner.
    def _timestamp(self):
        return datetime.utcnow().isoformat() + "Z"
