# -----------------------------
# CENTRAL SYSTEM (CSMS)
# -----------------------------
import asyncio
import websockets
from datetime import datetime, timezone

from ocpp.v201 import ChargePoint as CP
from ocpp.v201 import call, call_result
from ocpp.routing import on
from common.utils.logger import get_logger

from state import evse_list, ev_list, connected_charge_points, reservation_id_counter
from ocpp.v201.enums import (
    RegistrationStatusEnumType,
    AuthorizationStatusEnumType,
    ReserveNowStatusEnumType,
    ConnectorStatusEnumType
)

logger = get_logger("CentralSystem")

class CentralSystem(CP):
    # Handles BootNotification from Charge Point
    @on('BootNotification')
    async def on_boot_notification(self, charging_station, reason, **kwargs):
        logger.info(f"BootNotification from: {charging_station['vendor_name']} / {charging_station['model']}")
        return call_result.BootNotification(
            current_time=self.now(),
            interval=10,
            status=RegistrationStatusEnumType.accepted
        )

    # Handles Authorize request from Charge Point
    @on('Authorize')
    async def on_authorize(self, id_token, **kwargs):
        logger.info(f"Authorize request received with id_token: {id_token['id_token']}")
        return call_result.Authorize(
            id_token_info={"status": AuthorizationStatusEnumType.accepted}
        )

    # Handles StatusNotification from Charge Point
    @on('StatusNotification')
    async def on_status_notification(self, timestamp, connector_status, connector_id, evse_id, **kwargs):
        logger.info(f"StatusNotification received: EVSE {evse_id}, Connector {connector_id}, Status: {connector_status}")
        target_evse = next((e for e in evse_list if e.id == evse_id), None)

        if target_evse:
            try:
                status_str = connector_status.value if hasattr(connector_status, "value") else connector_status
                target_evse.status = ConnectorStatusEnumType(status_str)
                logger.info(f"EVSE {evse_id} status updated to: {target_evse.status.value}")
            except ValueError:
                logger.warning(f"Invalid status received: {connector_status}")
        else:
            logger.warning(f"EVSE {evse_id} not found for StatusNotification")

        return call_result.StatusNotification()

    # Handles ReserveNow request (from external system)
    @on('ReserveNow')
    async def on_reserve_now(self, evse_id, id_token, **kwargs):
        logger.info(f"ReserveNow request received for EVSE {evse_id} with idToken {id_token.get('id_token')}")
        target_evse = next((e for e in evse_list if e.id == evse_id), None)

        if target_evse and target_evse.is_available():
            target_evse.reserve(id_token.get("id_token"))
            target_evse.status = ConnectorStatusEnumType.reserved
            logger.info(f"EVSE {evse_id} successfully reserved")
            return call_result.ReserveNow(status=ReserveNowStatusEnumType.accepted)

        logger.warning(f"EVSE {evse_id} reservation failed")
        return call_result.ReserveNow(status=ReserveNowStatusEnumType.rejected)

    # Handles Heartbeat
    @on('Heartbeat')
    async def on_heartbeat(self, **kwargs):
        current_time = self.now()
        logger.info(f"Heartbeat received. Responding with current_time={current_time}")
        return call_result.Heartbeat(current_time=current_time)

    # Handles MeterValues from Charge Point
    @on('MeterValues')
    async def on_meter_values(self, evse_id, meter_value, **kwargs):
        logger.info(f"MeterValues received from EVSE {evse_id}: {meter_value}")
        return call_result.MeterValues()

    # Handles TransactionEvent (Start/End charging session)
    @on('TransactionEvent')
    async def on_transaction_event(self, event_type, timestamp, trigger_reason, seq_no, transaction_info, id_token, evse, **kwargs):
        transaction_id = transaction_info.get("transaction_id")
        evse_id = evse.get("id")
        user_token = id_token.get("id_token")

        logger.info(f"TransactionEvent received: {event_type}, Transaction ID: {transaction_id}, User: {user_token}")

        target_evse = next((e for e in evse_list if e.id == evse_id), None)
        target_ev = next((ev for ev in ev_list if ev.connected_evse_id == evse_id or ev.id == user_token), None)

        if not target_evse:
            logger.warning(f"EVSE not found for TransactionEvent: ID {evse_id}")
        else:
            if event_type == "Started":
                target_evse.start_charging()
                if target_ev:
                    target_ev.connected_evse_id = evse_id
                logger.info(f"Charging started on EVSE {evse_id}")
            elif event_type == "Ended":
                target_evse.stop_charging()
                if target_ev and target_ev.connected_evse_id == evse_id:
                    target_ev.connected_evse_id = None
                logger.info(f"Charging ended on EVSE {evse_id}")

        return call_result.TransactionEvent()

    # Sends StatusNotification when plug-in is simulated
    async def plug_in_vehicle(self, evse_id: int):
        request = call.StatusNotification(
            timestamp=self.now(),
            connector_status=ConnectorStatusEnumType.occupied.value,
            connector_id=1,
            evse_id=evse_id
        )
        await self.call(request)
        logger.info(f"StatusNotification sent: EVSE {evse_id} set to Occupied")

    def now(self):
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# Reservation request entrypoint from backend
async def reserve_evse_by_id(evse_id: int, ev_id: str):
    global reservation_id_counter
    cp_id = f"CP_{evse_id}"
    cp = connected_charge_points.get(cp_id)
    if not cp:
        logger.warning(f"ReserveNow: {cp_id} not connected")
        return {"status": "failed", "reason": "Charge Point not connected"}

    reservation_id = reservation_id_counter
    reservation_id_counter += 1

    request = call.ReserveNow(
        id=reservation_id,
        expiry_date_time=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        id_token={"id_token": ev_id, "type": "Central"},
        evse_id=evse_id
    )
    response = await cp.call(request)
    logger.info(f"ReserveNow sent to {cp_id}, response: {response.status}")

    if response.status == ReserveNowStatusEnumType.accepted:
        target_evse = next((e for e in evse_list if e.id == evse_id), None)
        if target_evse:
            target_evse.status = ConnectorStatusEnumType.reserved

    return {"status": response.status}

# WebSocket connection handler
async def on_connect(websocket, path):
    cp_id = path.strip("/")
    logger.info(f"New connection from charge point: {cp_id}")
    charge_point = CentralSystem(cp_id, websocket)
    connected_charge_points[cp_id] = charge_point
    await charge_point.start()

# Starts the WebSocket server
async def start_csms():
    logger.info("Starting Central System (CSMS)...")
    server = await websockets.serve(on_connect, host="0.0.0.0", port=9000, subprotocols=["ocpp2.0.1"])
    logger.info("Central System is listening on ws://0.0.0.0:9000")
    await server.wait_closed()