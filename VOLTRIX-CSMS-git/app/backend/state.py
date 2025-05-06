from typing import List
from models.ev import EV
from models.evse import EVSE

ev_list: List[EV] = []
evse_list: List[EVSE] = []
evse_id_counter = 1
reservation_id_counter = 1000
connected_charge_points = {}
active_ev_clients = {}