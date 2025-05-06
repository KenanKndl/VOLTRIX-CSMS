# === IMPORTS ===
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from contextlib import asynccontextmanager
import asyncio

# Dahili Modüller
from models.ev import EV
from models.evse import EVSE
from ocpp.v201.enums import ConnectorStatusEnumType
from data.power_lookup import model_power_map
from server.central_system import start_csms, reserve_evse_by_id
from server.charge_point import run_charge_point
from state import evse_list, ev_list, evse_id_counter, connected_charge_points, active_ev_clients
from common.utils.logger import get_logger
from iso15118.evse_server import EVSEServer
from iso15118.ev_client import EVClient

# Logger başlatılıyor
logger = get_logger("Main")

# =======================================================
# FASTAPI UYGULAMA ÖMRÜ (LIFESPAN)
# =======================================================

@asynccontextmanager
async def lifespan(app):
    """Initialize CSMS and load initial EV and EVSE data."""
    asyncio.create_task(start_csms())
    await load_initial_data()
    logger.info("Lifespan startup completed.")
    yield


# FastAPI uygulaması başlatılıyor
app = FastAPI(lifespan=lifespan)

# CORS ayarları (frontend erişimine izin ver)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# =======================================================
# BAŞLANGIÇ VERİLERİNİN YÜKLENMESİ (EV + EVSE)
# =======================================================

async def load_initial_data(autoload_evse: bool = False):
    """Preload default EVs and conditionally EVSEs on startup."""
    global evse_id_counter

    # EV'leri yükle
    ev_list.clear()
    ev_list.extend([
        EV(id="EV-001", brand="Tesla", model="Model 3", battery_capacity_kWh=60, consumption_kWh_per_km=0.15,
           current_soc=40, target_soc=90, location_lat=40.7128, location_long=29.9230),
        EV(id="EV-002", brand="Renault", model="ZOE", battery_capacity_kWh=45, consumption_kWh_per_km=0.13,
           current_soc=55, target_soc=100, location_lat=40.7321, location_long=29.9540),
        EV(id="EV-003", brand="Hyundai", model="Kona", battery_capacity_kWh=64, consumption_kWh_per_km=0.16,
           current_soc=20, target_soc=80, location_lat=40.7483, location_long=29.9801),
        EV(id="EV-004", brand="Volkswagen", model="ID.4", battery_capacity_kWh=77, consumption_kWh_per_km=0.18,
           current_soc=50, target_soc=100, location_lat=40.7600, location_long=29.9200),
        EV(id="EV-005", brand="BMW", model="i4 eDrive40", battery_capacity_kWh=83.9, consumption_kWh_per_km=0.19,
           current_soc=30, target_soc=85, location_lat=40.7900, location_long=29.9100),
        EV(id="EV-006", brand="Mercedes-Benz", model="EQB 300", battery_capacity_kWh=66.5, consumption_kWh_per_km=0.17,
           current_soc=25, target_soc=90, location_lat=40.7020, location_long=29.9500),
        EV(id="EV-007", brand="Nissan", model="Leaf e+", battery_capacity_kWh=62, consumption_kWh_per_km=0.15,
           current_soc=60, target_soc=100, location_lat=40.7400, location_long=29.9700),
        EV(id="EV-008", brand="BYD", model="Atto 3", battery_capacity_kWh=60.5, consumption_kWh_per_km=0.16,
           current_soc=45, target_soc=95, location_lat=40.7200, location_long=29.9650),
    ])
    logger.info(f"{len(ev_list)} adet EV yüklendi.")

    # Eğer EVSE'ler otomatik yüklenecekse...
    if not autoload_evse:
        logger.info("EVSE otomatik yükleme devre dışı.")
        return

    from server.charge_point import run_charge_point
    from iso15118.evse_server import EVSEServer

    evse_list.clear()
    evse_id_counter = 1

    default_evse_data = [
        {
            "name": "İstMarina AC",
            "brand": "ZES",
            "model": "AC Type-2",
            "vendor": "Vestel",
            "latitude": 40.7142,
            "longitude": 29.9235,
            "status": "Available"
        },
        {
            "name": "CaddeBostan Reserved",
            "brand": "Voltrun",
            "model": "DC Fast",
            "vendor": "Siemens",
            "latitude": 40.7325,
            "longitude": 29.9550,
            "status": "Reserved"
        },
        {
            "name": "Kartepe Park",
            "brand": "Sharz",
            "model": "Wallbox",
            "vendor": "ABB",
            "latitude": 40.7487,
            "longitude": 29.9805,
            "status": "Occupied"
        },
        {
            "name": "Gebze Teknik Bakım",
            "brand": "Eşarj",
            "model": "DC Ultra",
            "vendor": "Delta",
            "latitude": 40.7905,
            "longitude": 29.9110,
            "status": "Unavailable"
        },
        {
            "name": "Pendik Arıza",
            "brand": "Tesla",
            "model": "Supercharger",
            "vendor": "Tesla",
            "latitude": 40.7202,
            "longitude": 29.9652,
            "status": "Faulted"
        },
    ]

    for evse_data in default_evse_data:
        evse = EVSE(
            id=evse_id_counter,
            name=evse_data["name"],
            brand=evse_data["brand"],
            model=evse_data["model"],
            vendor=evse_data["vendor"],
            latitude=evse_data["latitude"],
            longitude=evse_data["longitude"],
            max_power_kW=model_power_map.get(evse_data["model"], 22.0),
            status=ConnectorStatusEnumType(evse_data["status"])  # ❗ .lower() kaldırıldı
        )
        evse_list.append(evse)

        cp_id = f"CP_{evse.id}"
        asyncio.create_task(run_charge_point(cp_id, evse_data["status"]))

        iso_port = 9001 + evse.id
        iso_server = EVSEServer(port=iso_port)
        asyncio.create_task(iso_server.start())

        evse_id_counter += 1

    logger.info(f"{len(evse_list)} adet EVSE yüklendi.")

# =======================================================
# EVSE İŞLEMLERİ
# =======================================================

@app.post("/evses")
async def add_evse(data: dict):
    """Add new EVSE, start its Charge Point, and ISO15118 EVSE server."""
    global evse_id_counter
    try:
        model = data["model"]
        max_power = model_power_map.get(model, 22.0)

        # EVSE nesnesini oluştur
        evse = EVSE(
            id=evse_id_counter,
            name=data["name"],
            brand=data["brand"],
            model=model,
            vendor=data["vendor"],
            latitude=data["latitude"],
            longitude=data["longitude"],
            max_power_kW=max_power,
            status=ConnectorStatusEnumType(data["status"])
        )
        evse_list.append(evse)
        evse_id_counter += 1

        cp_id = f"CP_{evse.id}"
        asyncio.create_task(run_charge_point(cp_id, data["status"]))

        # ISO15118 EVSE server'ını başlat (her EVSE için farklı port)
        from iso15118.evse_server import EVSEServer  # burada import et
        iso_port = 9001 + evse.id  # her EVSE için farklı port
        iso_server = EVSEServer(port=iso_port)
        asyncio.create_task(iso_server.start())
        logger.info(f"ISO15118 EVSE Server başlatıldı: ws://localhost:{iso_port}")

        return {"status": "added", "evse": evse.to_dict()}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/evses")
def list_evses():
    """Return list of all EVSEs."""
    return [evse.to_dict() for evse in evse_list]

@app.get("/evses/summary")
def get_evse_summary():
    """Return summary of EVSEs (total and connected)."""
    total = len(evse_list)
    connected = sum(1 for evse in evse_list if evse.status in [
        ConnectorStatusEnumType.available,
        ConnectorStatusEnumType.reserved,
        ConnectorStatusEnumType.occupied
    ])
    return {"total": total, "connected": connected}

@app.get("/evses/statuses")
def get_status_options():
    """Return list of possible EVSE statuses."""
    return [status.value for status in ConnectorStatusEnumType]

@app.patch("/evses/{index}/status")
async def update_evse_status(index: int, payload: dict):
    if 0 <= index < len(evse_list):
        new_status_str = payload.get("status", evse_list[index].status.value)
        try:
            evse_list[index].status = ConnectorStatusEnumType(new_status_str)

            # OCPP'e status bildir
            cp_id = f"CP_{evse_list[index].id}"
            cp = connected_charge_points.get(cp_id)
            if cp:
                await cp.send_status_notification(
                    evse_id=evse_list[index].id,
                    status=evse_list[index].status
                )

            # EV bağlama/ayırma mantığı aynı kalabilir
            if evse_list[index].status == ConnectorStatusEnumType.reserved:
                for ev in ev_list:
                    if ev.connected_evse_id is None:
                        ev.connected_evse_id = evse_list[index].name
                        break
            elif evse_list[index].status == ConnectorStatusEnumType.unavailable:
                for ev in ev_list:
                    if ev.connected_evse_id == evse_list[index].name:
                        ev.connected_evse_id = None
                        break

        except ValueError:
            return {"error": "Invalid status value"}
        return {"status": "updated"}
    return {"error": "Invalid EVSE index"}

@app.post("/evses/{evse_index}/plug")
async def plug_evse(evse_index: int):
    """Simulate plugging EV to EVSE and start ISO15118 EV client connection only."""
    from iso15118.ev_client import EVClient
    from state import ev_list, connected_charge_points, active_ev_clients

    try:
        evse = evse_list[evse_index]
    except IndexError:
        raise HTTPException(status_code=404, detail="EVSE not found.")

    if evse.status != ConnectorStatusEnumType.reserved:
        raise HTTPException(status_code=400, detail="EVSE is not reserved.")

    cp_id = f"CP_{evse.id}"
    cp = connected_charge_points.get(cp_id)
    if not cp:
        raise HTTPException(status_code=500, detail=f"Charge Point {cp_id} not connected.")

    # OCPP'e plug bildir
    await cp.plug_in_vehicle(evse.id)
    evse.status = ConnectorStatusEnumType.occupied

    # EV'i bul ve ISO15118 bağlantısını başlat
    ev = next((e for e in ev_list if e.connected_evse_id == evse.name), None)
    if ev:
        iso_port = 9001 + evse.id
        uri = f"ws://localhost:{iso_port}"
        client = EVClient(ev_id=ev.id, evse_id=evse.id, uri=uri)
        active_ev_clients[ev.id] = client
        asyncio.create_task(client.connect())
        logger.info("ISO15118 bağlantısı başlatıldı.")
    else:
        logger.warning("Bağlı EV bulunamadı.")

    return {"status": "occupied", "message": "EV plugged in and ISO connection established."}

@app.post("/evses/{evse_index}/disconnect")
async def disconnect_evse(evse_index: int):
    try:
        evse = evse_list[evse_index]
    except IndexError:
        raise HTTPException(status_code=404, detail="EVSE not found.")

    cp_id = f"CP_{evse.id}"
    cp = connected_charge_points.get(cp_id)

    if not cp:
        raise HTTPException(status_code=500, detail=f"Charge Point {cp_id} not connected.")

    evse.status = ConnectorStatusEnumType.unavailable
    cp.initial_status = ConnectorStatusEnumType.unavailable

    await cp.send_status_notification(evse_id=evse.id, status=ConnectorStatusEnumType.unavailable)

    return {"status": "unavailable", "message": "EVSE status set to unavailable."}

@app.post("/evses/{evse_index}/connect")
async def connect_evse(evse_index: int):
    try:
        evse = evse_list[evse_index]
        cp_id = f"CP_{evse.id}"
        cp = connected_charge_points.get(cp_id)

        if not cp:
            raise HTTPException(status_code=500, detail="Charge Point not connected.")

        evse.status = ConnectorStatusEnumType.available
        cp.initial_status = ConnectorStatusEnumType.available
        await cp.send_status_notification(evse_id=evse.id, status=ConnectorStatusEnumType.available)

        return {"status": "available", "message": "EVSE connected and status set to Available."}

    except IndexError:
        raise HTTPException(status_code=404, detail="EVSE not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evses/{evse_index}/start")
async def start_evse_transaction(evse_index: int):
    from state import ev_list, connected_charge_points, active_ev_clients

    try:
        evse = evse_list[evse_index]
        cp = connected_charge_points.get(f"CP_{evse.id}")
        if not cp:
            raise HTTPException(status_code=500, detail="Charge Point not connected.")

        # OCPP üzerinden şarj başlat
        await cp.send_transaction_event_started(evse.id)
        logger.info(f"OCPP üzerinden şarj başlatıldı: EVSE {evse.id}")

        ev = next((e for e in ev_list if e.connected_evse_id == evse.name), None)
        if not ev:
            raise HTTPException(status_code=404, detail="EV not connected to this EVSE.")

        # Daha önce başlatılmış bağlantıyı kullanarak ISO15118 şarj başlatma mesajı gönder
        client = active_ev_clients.get(ev.id)
        if not client:
            raise HTTPException(status_code=500, detail="ISO15118 client not active for this EV.")

        await client.send_charging_start_request()
        logger.info("ChargingStartRequest ISO15118 üzerinden gönderildi.")

        return {"status": "started", "evse": evse.id}

    except Exception as e:
        logger.error(f"Start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evses/{evse_index}/stop")
async def stop_evse_transaction(evse_index: int):
    try:
        evse = evse_list[evse_index]
        cp = connected_charge_points.get(f"CP_{evse.id}")
        if not cp:
            raise HTTPException(status_code=500, detail="Charge Point not connected.")

        # EV bulunmalı
        ev = next((e for e in ev_list if e.connected_evse_id == evse.name), None)
        if not ev:
            raise HTTPException(status_code=404, detail="No EV connected to this EVSE.")

        # ISO15118 bağlantısı varsa client çek
        ev_client: EVClient = active_ev_clients.get(ev.id)
        if not ev_client or not ev_client.websocket:
            raise HTTPException(status_code=500, detail="ISO15118 client not connected.")

        # 1️⃣ OCPP transaction stop gönder
        await cp.send_transaction_event_ended(evse.id)
        logger.info(f"OCPP üzerinden şarj durduruldu: EVSE {evse.id}")

        # 2️⃣ ISO15118 üzerinden ChargingStopRequest gönder
        await ev_client.send_charging_stop_request(ev_client.websocket, reason="UserStopped")
        logger.info("Main: ISO15118 ChargingStopRequest gönderildi.")

        return {"status": "stopped", "evse": evse.id}

    except Exception as e:
        logger.error(f"Stop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# =======================================================
# EV İŞLEMLERİ
# =======================================================

@app.get("/evs")
def list_evs():
    """Return list of all EVs."""
    return [ev.to_dict() for ev in ev_list]

@app.get("/evs/{ev_id}")
def get_ev(ev_id: str):
    """Return EV by ID."""
    for ev in ev_list:
        if ev.id == ev_id:
            return ev.to_dict()
    return {"error": "EV not found"}

@app.patch("/evs/{ev_id}/soc")
def update_ev_soc(ev_id: str, payload: dict):
    """Update EV's current state of charge."""
    new_soc = payload.get("current_soc")
    if new_soc is None:
        raise HTTPException(status_code=400, detail="Missing current_soc")

    for ev in ev_list:
        if ev.id == ev_id:
            ev.current_soc = max(0, min(100, new_soc))
            return {"status": "updated", "current_soc": ev.current_soc}

    raise HTTPException(status_code=404, detail="EV not found")

# =======================================================
# REZERVASYON & OCPP İŞLEMLERİ
# =======================================================

@app.get("/reservation/estimate")
def get_estimated_time(ev_id: str, evse_index: int):
    """Estimate reservation time for given EV and EVSE."""
    try:
        ev = next((e for e in ev_list if e.id == ev_id), None)
        evse = evse_list[evse_index]

        if ev:
            logger.info(f"Estimate requested: EV={ev.id}, connected={ev.connected_evse_id}, target={evse.name}")
        else:
            logger.warning(f"Estimate requested for unknown EV: {ev_id}")

        if not ev or evse.status not in [
            ConnectorStatusEnumType.available,
            ConnectorStatusEnumType.reserved
        ]:
            return {"reservable": False, "reason": "EVSE not available"}

        required_energy = ev.get_required_energy_kWh()
        if evse.max_power_kW <= 0 or required_energy == 0:
            return {"reservable": False, "reason": "Cannot calculate charging time"}

        estimated_time_min = int((required_energy / evse.max_power_kW) * 60)
        return {"reservable": True, "estimated_time_min": estimated_time_min}

    except Exception as e:
        return {"reservable": False, "reason": str(e)}

@app.post("/reservation/assign")
def assign_reservation(ev_id: str = Query(...), evse_index: int = Query(...)):
    """Assign EVSE to EV if it is available."""
    try:
        ev = next((e for e in ev_list if e.id == ev_id), None)
        if not ev or not (0 <= evse_index < len(evse_list)):
            raise HTTPException(status_code=404, detail="EV or EVSE not found")

        evse = evse_list[evse_index]
        if evse.status != ConnectorStatusEnumType.available:
            return {"error": "EVSE not idle"}

        ev.connected_evse_id = evse.name
        evse.status = ConnectorStatusEnumType.reserved

        return {"status": "reserved", "evse": evse.name, "ev": ev.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ocpp/reserve")
async def ocpp_reserve(payload: dict):
    """Send OCPP ReserveNow request."""
    ev_id = payload.get("ev_id")
    evse_index = payload.get("evse_index")

    target_ev = next((e for e in ev_list if e.id == ev_id), None)
    if not target_ev:
        raise HTTPException(status_code=404, detail="EV not found")

    evse = evse_list[evse_index]
    result = await reserve_evse_by_id(evse_id=evse.id, ev_id=ev_id)

    if result["status"] == "Accepted":
        target_ev.connected_evse_id = evse.name

    return result
