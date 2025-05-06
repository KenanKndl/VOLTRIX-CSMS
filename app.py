from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import datetime, timedelta
import math
import threading
# Otomata sistemi için import ekleyelim
from automata.automata_loader import AutomataLoader
from automata.engine import AutomataEngine
from automata.conditions import register_condition_handlers
from automata.actions import register_action_handlers

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Otomata sistemini yükle
automata_loader = AutomataLoader()
# Sadece gerekli olan otomataları yükleyelim
automata_definitions = automata_loader.load_automatas([
    "automata/dfa/smart_suggestion_dfa.xml",
    "automata/dfa/charge_station_dfa.xml"
])

# Otomata motorlarını oluştur
automatas = {}
for automata_id, automata_def in automata_definitions.items():
    try:
        engine = AutomataEngine(automata_def)
        automatas[automata_id] = engine
        print(f"✅ {automata_id} otomatası başarıyla başlatıldı")
    except Exception as e:
        print(f"❌ {automata_id} otomatası oluşturulurken hata: {str(e)}")

# Desteklenen istasyon durumları
VALID_STATUSES = ['available', 'occupied', 'reserved', 'unavailable', 'faulted']

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

# Araç tablosu
class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    battery_capacity_kWh = db.Column(db.Float, nullable=False)
    charge_power_kW = db.Column(db.Float, nullable=False)
    latitude = db.Column(db.Float, nullable=True)   # ✅ YENİ
    longitude = db.Column(db.Float, nullable=True)  # ✅ YENİ
    current_soc = db.Column(db.Float, default=20.0)  # ✅ Yeni alan

class ChargingStation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='available')  # ✅ YENİ
    brand = db.Column(db.String(100), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    vendor = db.Column(db.String(100), nullable=True)
    max_power_kW = db.Column(db.Float, nullable=True)  # ✅ Yeni eklenen alan

class UserVehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # Hangi kullanıcıya ait
    vehicle_id = db.Column(db.Integer, nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    battery_capacity_kWh = db.Column(db.Float, nullable=False)
    charge_power_kW = db.Column(db.Float, nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    station_id = db.Column(db.Integer, nullable=False)
    vehicle_id = db.Column(db.Integer, nullable=False)
    current_battery_percent = db.Column(db.Float, nullable=False)
    target_battery_percent = db.Column(db.Float, nullable=False)
    duration_minutes = db.Column(db.Float, nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    expected_end_time = db.Column(db.DateTime, nullable=False)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email zaten kayıtlı"}), 400
    user = User(
        name=data['name'],
        email=data['email'],
        password_hash=generate_password_hash(data['password'])
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Kayıt başarılı"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if user and check_password_hash(user.password_hash, data['password']):
        return jsonify({"message": "Giriş başarılı", "user_id": user.id}), 200
    return jsonify({"error": "Geçersiz email ya da şifre"}), 401

# Tüm araçları listeleme endpoint'i
@app.route('/vehicles', methods=['GET'])
def get_vehicles():
    vehicles = Vehicle.query.all()
    vehicles_list = []

    for v in vehicles:
        vehicles_list.append({
            "id": v.id,
            "brand": v.brand,
            "model": v.model,
            "year": v.year,
            "battery_capacity_kWh": v.battery_capacity_kWh,
            "charge_power_kW": v.charge_power_kW,
            "latitude": v.latitude,    # ✅ yeni eklendi
            "longitude": v.longitude   # ✅ yeni eklendi
        })

    return jsonify(vehicles_list), 200

# Şarj istasyonlarını listeleme endpoint'i
@app.route('/stations', methods=['GET'])
def get_stations():
    stations = ChargingStation.query.all()
    station_list = []

    for station in stations:
        station_list.append({
            "id": station.id,
            "name": station.name,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "status": station.status,  # ✅ Durumu da döndürüyoruz
            "brand": station.brand,
            "model": station.model,
            "vendor": station.vendor
        })

    return jsonify(station_list), 200

# Quick Action endpoint'i (güncellenmiş ve temizlenmiş hali)
@app.route('/quick_action', methods=['POST'])
def quick_action():
    data = request.get_json()

    vehicle_id = data.get('vehicle_id')

    if vehicle_id is None:
        return jsonify({"error": "vehicle_id gerekli"}), 400

    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return jsonify({"error": "Araç bulunamadı"}), 404

    vehicle_lat = vehicle.latitude
    vehicle_lon = vehicle.longitude

    stations = ChargingStation.query.all()
    reachable_stations = []

    for station in stations:
        distance_km = simple_distance(vehicle_lat, vehicle_lon, station.latitude, station.longitude)

        reachable_stations.append({
            "id": station.id,
            "name": station.name,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "distance_km": round(distance_km, 2)
        })

    # 🔥 Sadece bir defa mesafe bilgilerini yazdırıyoruz:
    print("\n=== Reachable Stations Mesafeler ===")
    for station in reachable_stations:
        print(f"{station['name']}: {station['distance_km']} km")
    print("====================================\n")

    # 🔥 Mesafeye göre en yakını seçiyoruz
    nearest_station = min(reachable_stations, key=lambda x: x['distance_km']) if reachable_stations else None

    return jsonify({
        "reachable_stations": reachable_stations,
        "nearest_station": nearest_station
    }), 200

@app.route('/user-vehicles', methods=['POST'])
def add_user_vehicle():
    data = request.get_json()

    vehicle_id = data.get('vehicle_id')

    # Aynı marka + model + yıl var mı kontrol et
    existing_vehicle = UserVehicle.query.filter_by(
        user_id=data['user_id'],
        brand=data['brand'],
        model=data['model'],
        year=data['year']
    ).first()

    if existing_vehicle:
        return jsonify({"error": "This vehicle already exists in your list."}), 400

    new_vehicle = UserVehicle(
        user_id=data['user_id'],
        vehicle_id=vehicle_id,
        brand=data['brand'],
        model=data['model'],
        year=data['year'],
        battery_capacity_kWh=data['battery_capacity_kWh'],
        charge_power_kW=data['charge_power_kW'],
        latitude=data.get('latitude'),
        longitude=data.get('longitude')
    )
    db.session.add(new_vehicle)
    db.session.commit()

    return jsonify({"message": "Araç başarıyla kaydedildi."}), 201

@app.route('/user-vehicles', methods=['GET'])
def get_user_vehicles():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "user_id gerekli."}), 400

    vehicles = UserVehicle.query.filter_by(user_id=user_id).all()
    vehicle_list = []

    for v in vehicles:
        vehicle_list.append({
            "id": v.id,
            "brand": v.brand,
            "model": v.model,
            "year": v.year,
            "battery_capacity_kWh": v.battery_capacity_kWh,
            "charge_power_kW": v.charge_power_kW,
            "latitude": v.latitude,
            "longitude": v.longitude
        })

    return jsonify(vehicle_list), 200

@app.route('/user-vehicles/<int:vehicle_id>', methods=['DELETE'])
def delete_user_vehicle(vehicle_id):
    vehicle = UserVehicle.query.get(vehicle_id)

    if not vehicle:
        return jsonify({"error": "Araç bulunamadı."}), 404

    db.session.delete(vehicle)
    db.session.commit()

    return jsonify({"message": "Araç başarıyla silindi."}), 200

@app.route('/stations/<int:station_id>/status', methods=['PUT'])
def update_station_status(station_id):
    data = request.get_json()
    new_status = data.get('status')

    # 1) Durum geçerli mi kontrol et
    if new_status not in VALID_STATUSES:
        return jsonify({"error": f"Geçersiz status. Geçerli değerler: {VALID_STATUSES}"}), 400


    # 2) İstasyon var mı kontrol et
    station = ChargingStation.query.get(station_id)
    if not station:
        return jsonify({"error": "Şarj istasyonu bulunamadı"}), 404

    # 3) Güncelle ve kaydet
    station.status = new_status
    db.session.commit()

    return jsonify({"message": f"{station.name} durum güncellendi: {new_status}"}), 200

@app.route('/reservations', methods=['POST'])
def create_reservation():
    data = request.get_json()
    
    user_id = data.get('user_id')
    station_id = data.get('station_id')
    vehicle_id = data.get('vehicle_id')
    current_percent = data.get('current_battery_percent')
    target_percent = data.get('target_battery_percent')

    if None in [user_id, station_id, vehicle_id, current_percent, target_percent]:
        return jsonify({"error": "Eksik veri gönderildi."}), 400

    # Araç bilgilerini al
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return jsonify({"error": "Araç bulunamadı."}), 404

    # Şarj süresi hesapla (dakika cinsinden)
    energy_needed = vehicle.battery_capacity_kWh * ((target_percent - current_percent) / 100)
    charging_time_minutes = (energy_needed / vehicle.charge_power_kW) * 60

    # Zamanları ayarla
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(minutes=charging_time_minutes)

    # Rezervasyon kaydet
    reservation = Reservation(
        user_id=user_id,
        station_id=station_id,
        vehicle_id=vehicle_id,
        current_battery_percent=current_percent,
        target_battery_percent=target_percent,
        duration_minutes=charging_time_minutes,
        start_time=start_time,
        expected_end_time=end_time
    )
    db.session.add(reservation)

    # Şarj istasyonunu 'Reserved' yap
    station = ChargingStation.query.get(station_id)
    if not station:
        return jsonify({"error": "İstasyon bulunamadı."}), 404
    station.status = 'Reserved'
    db.session.commit()

    # Süre dolunca istasyonu 'Disconnected' yapacak görev
    def release_station():
        with app.app_context():
            station_to_free = ChargingStation.query.get(station_id)
            if station_to_free and station_to_free.status != 'available':
                station_to_free.status = 'available'
                db.session.commit()
                print(f"[✓] İstasyon #{station_id} otomatik olarak Disconnected oldu.")

    timer = threading.Timer(charging_time_minutes * 60, release_station)
    timer.start()

    return jsonify({
        "message": "Rezervasyon başarıyla oluşturuldu.",
        "reservation_id": reservation.id,
        "user_id": user_id,  # ✅ bunu ekliyoruz
        "estimated_duration_min": round(charging_time_minutes, 2),
        "expected_end_time": end_time.isoformat()
    }), 201

@app.route('/smart-stations', methods=['POST'])
def smart_station_suggestions():
    data = request.get_json()

    user_lat = data.get('latitude')
    user_lon = data.get('longitude')
    travel_speed_kmh = data.get('speed_kmh', 30)  # Ortalama hız (varsayılan 30 km/h)

    if None in [user_lat, user_lon]:
        return jsonify({"error": "Konum bilgisi gerekli."}), 400

    stations = ChargingStation.query.all()
    suggestions = []

    for station in stations:
        distance_km = simple_distance(user_lat, user_lon, station.latitude, station.longitude)
        travel_minutes = (distance_km / travel_speed_kmh) * 60

        reservable = False
        reason = ""

        if station.status == 'available':
            reservable = True
            reason = "İstasyon zaten boş"
        elif station.status == 'reserved':
            active_res = Reservation.query.filter(
                Reservation.station_id == station.id, 
                Reservation.expected_end_time > datetime.utcnow()
            ).order_by(Reservation.expected_end_time.desc()).first()
            if active_res:
                expected_free_time = active_res.expected_end_time
                arrival_time = datetime.utcnow() + timedelta(minutes=travel_minutes)
                if arrival_time >= expected_free_time:
                    reservable = True
                    reason = f"İstasyona ulaştığında boş olacak (~{int(travel_minutes)} dk sonra)"

        suggestions.append({
            "id": station.id,
            "name": station.name,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "status": station.status,
            "distance_km": round(distance_km, 2),
            "travel_minutes": round(travel_minutes),
            "reservable": reservable,
            "note": reason if reservable else "Şu an ulaşıldığında hala dolu olacak"
        })

    return jsonify(suggestions), 200

@app.route('/reservations', methods=['GET'])
def get_user_reservations():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "user_id parametresi gerekli."}), 400

    reservations = Reservation.query.filter_by(user_id=user_id).order_by(Reservation.start_time.desc()).all()
    result = []

    for r in reservations:
        station = ChargingStation.query.get(r.station_id)
        vehicle = Vehicle.query.get(r.vehicle_id)

        result.append({
            "reservation_id": r.id,
            "station_name": station.name if station else "Bilinmiyor",
            "vehicle_model": f"{vehicle.brand} {vehicle.model}" if vehicle else "Bilinmiyor",
            "start_time": r.start_time.isoformat(),
            "end_time": r.expected_end_time.isoformat(),
            "duration_minutes": round(r.duration_minutes, 2),
            "status": station.status if station else "unknown"
        })

    return jsonify(result), 200

@app.route('/reservations/active', methods=['GET'])
def get_active_reservations():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "user_id parametresi gerekli."}), 400

    now = datetime.utcnow()
    active_reservations = Reservation.query.filter(
        Reservation.user_id == user_id,
        Reservation.expected_end_time > now
    ).order_by(Reservation.expected_end_time.asc()).all()

    result = []

    for res in active_reservations:
        station = ChargingStation.query.get(res.station_id)
        vehicle = Vehicle.query.get(res.vehicle_id)

        result.append({
            "id": res.id,
            "station_id": res.station_id,
            "station_name": station.name if station else "Bilinmiyor",
            "vehicle_id": res.vehicle_id,
            "vehicle_model": f"{vehicle.brand} {vehicle.model}" if vehicle else "Bilinmiyor",
            "status": station.status if station else "unknown",
            "expected_end_time": res.expected_end_time.isoformat()
        })

    return jsonify(result), 200

@app.route('/stations', methods=['POST'])
def add_station():
    data = request.get_json()

    status = data.get('status', 'available').lower()  # ✅ Küçük harfe çevir

    if status not in VALID_STATUSES:
        return jsonify({"error": f"Geçersiz status. Geçerli değerler: {VALID_STATUSES}"}), 400

    new_station = ChargingStation(
        name=data.get('name'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        status=status,  # ✅ küçük harf hali burada kullanılıyor
        brand=data.get('brand'),
        model=data.get('model'),
        vendor=data.get('vendor')
    )

    db.session.add(new_station)
    db.session.commit()


    return jsonify({
        "message": "Yeni istasyon eklendi.",
        "station_id": new_station.id
    }), 201

@app.route('/reservations/<int:reservation_id>', methods=['DELETE'])
def cancel_reservation(reservation_id):
    reservation = Reservation.query.get(reservation_id)

    if not reservation:
        return jsonify({"error": "Rezervasyon bulunamadı."}), 404

    station = ChargingStation.query.get(reservation.station_id)

    # 1. Rezervasyonu sil
    db.session.delete(reservation)

    # 2. İstasyonu tekrar available yap
    if station:
        station.status = 'available'

    db.session.commit()

    return jsonify({"message": "Rezervasyon iptal edildi ve istasyon tekrar available yapıldı."}), 200

@app.route('/cleanup-expired-reservations', methods=['GET'])
def cleanup_expired_reservations():
    now = datetime.utcnow()
    expired_reservations = Reservation.query.filter(Reservation.expected_end_time < now).all()

    cleaned_stations = []

    for r in expired_reservations:
        station = ChargingStation.query.get(r.station_id)
        if station and station.status in ['reserved', 'available', 'occupied']:
            station.status = 'available'
            cleaned_stations.append(station.id)

    db.session.commit()

    return jsonify({
        "message": "Süresi geçmiş rezervasyonlar işlendi.",
        "updated_stations": cleaned_stations
    }), 200

@app.route('/stations/<int:station_id>', methods=['DELETE'])
def delete_station(station_id):
    station = ChargingStation.query.get(station_id)
    if not station:
        return jsonify({"error": "İstasyon bulunamadı."}), 404

    db.session.delete(station)
    db.session.commit()

    return jsonify({"message": "İstasyon silindi."}), 200

@app.route('/stations/summary', methods=['GET'])
def station_summary():
    total = ChargingStation.query.count()
    connected = ChargingStation.query.filter(ChargingStation.status != 'Disconnected').count()

    return jsonify({
        "total": total,
        "connected": connected
    })

@app.route('/statuses', methods=['GET'])
def get_statuses():
    return jsonify(VALID_STATUSES), 200

@app.route('/reservations/estimate', methods=['GET'])
def estimate_reservation_time():
    station_id = request.args.get('station_id')
    vehicle_id = request.args.get('vehicle_id')
    current_percent = float(request.args.get('current_percent', 20))
    target_percent = float(request.args.get('target_percent', 80))

    if not station_id or not vehicle_id:
        return jsonify({"error": "Eksik parametre (station_id, vehicle_id)"}), 400

    vehicle = Vehicle.query.get(vehicle_id)
    station = ChargingStation.query.get(station_id)

    if not vehicle or not station:
        return jsonify({"error": "İstasyon veya araç bulunamadı."}), 404

    energy_needed = vehicle.battery_capacity_kWh * ((target_percent - current_percent) / 100)
    charging_time_minutes = (energy_needed / vehicle.charge_power_kW) * 60

    reservable = station.status == 'available'

    return jsonify({
        "reservable": reservable,
        "estimated_time_min": round(charging_time_minutes, 1),
        "station_status": station.status
    }), 200

@app.route('/stations/<int:station_id>/connect', methods=['POST'])
def connect_station(station_id):
    station = ChargingStation.query.get(station_id)
    if not station:
        return jsonify({"error": "İstasyon bulunamadı"}), 404

    station.status = 'available'
    db.session.commit()
    return jsonify({"message": "İstasyon bağlandı", "status": station.status}), 200


@app.route('/stations/<int:station_id>/disconnect', methods=['POST'])
def disconnect_station(station_id):
    station = ChargingStation.query.get(station_id)
    if not station:
        return jsonify({"error": "İstasyon bulunamadı"}), 404

    station.status = 'unavailable'
    db.session.commit()
    return jsonify({"message": "İstasyon bağlantısı kesildi", "status": station.status}), 200

@app.route('/stations/<int:station_id>/plug', methods=['POST'])
def plug_station(station_id):
    station = ChargingStation.query.get(station_id)
    if not station:
        return jsonify({"error": "İstasyon bulunamadı"}), 404

    if station.status != "reserved":
        return jsonify({"error": "İstasyon reserved değil"}), 400

    station.status = "occupied"
    db.session.commit()
    return jsonify({"message": "EVSE plugged in", "status": station.status}), 200

@app.route('/stations/<int:station_id>/start', methods=['POST'])
def start_charging(station_id):
    station = ChargingStation.query.get(station_id)
    if not station:
        return jsonify({"error": "İstasyon bulunamadı"}), 404

    if station.status != "occupied":
        return jsonify({"error": "Şarj başlatılamaz, EVSE occupied değil"}), 400

    station.status = "charging"
    db.session.commit()
    return jsonify({"message": "Şarj başlatıldı", "status": station.status}), 200

@app.route('/stations/<int:station_id>/stop', methods=['POST'])
def stop_charging(station_id):
    station = ChargingStation.query.get(station_id)
    if not station:
        return jsonify({"error": "İstasyon bulunamadı"}), 404

    station.status = "available"
    db.session.commit()
    return jsonify({"message": "Şarj durduruldu", "status": station.status}), 200

@app.route('/vehicles/<int:vehicle_id>', methods=['PATCH'])
def update_vehicle_location(vehicle_id):
    """Araç konumunu ve diğer bilgilerini günceller"""
    data = request.get_json()
    
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return jsonify({"error": "Araç bulunamadı"}), 404
    
    # Araç konumunu güncelle
    if 'latitude' in data and 'longitude' in data:
        vehicle.latitude = data['latitude']
        vehicle.longitude = data['longitude']
    
    # SOC'yi ayrı endpoint'ten güncellemek yerine burada da güncellenebilir
    if 'current_soc' in data:
        try:
            new_soc = float(data['current_soc'])
            if 0 <= new_soc <= 100:
                vehicle.current_soc = new_soc
            else:
                return jsonify({"error": "SOC değeri 0-100 arasında olmalıdır"}), 400
        except ValueError:
            return jsonify({"error": "Geçersiz SOC değeri"}), 400
    
    # Batarya kapasitesi güncellemesi
    if 'battery_capacity_kWh' in data:
        try:
            new_capacity = float(data['battery_capacity_kWh'])
            if new_capacity > 0:
                vehicle.battery_capacity_kWh = new_capacity
            else:
                return jsonify({"error": "Batarya kapasitesi pozitif olmalıdır"}), 400
        except ValueError:
            return jsonify({"error": "Geçersiz batarya kapasitesi"}), 400
    
    # Güncelleme işlemi
    db.session.commit()
    
    return jsonify({
        "message": "Araç bilgileri güncellendi",
        "vehicle": {
            "id": vehicle.id,
            "brand": vehicle.brand,
            "model": vehicle.model,
            "latitude": vehicle.latitude,
            "longitude": vehicle.longitude,
            "current_soc": vehicle.current_soc,
            "battery_capacity_kWh": vehicle.battery_capacity_kWh
        }
    }), 200

# Smart Action endpoint'i (akıllı öneri sisteminin entegrasyonu)
@app.route('/smart-suggestion', methods=['POST'])
def smart_suggestion():
    data = request.get_json()
    
    vehicle_id = data.get('vehicle_id')
    current_soc = data.get('current_soc', 20.0)  # Şu anki pil durumu
    target_soc = data.get('target_soc', 80.0)    # Hedeflenen pil durumu
    max_waiting_time = data.get('max_waiting_time', 30)  # Dakika cinsinden maksimum bekleme süresi
    
    if vehicle_id is None:
        return jsonify({"error": "vehicle_id gerekli"}), 400
    
    # Aracı bul
    vehicle = Vehicle.query.get(vehicle_id)
    if not vehicle:
        return jsonify({"error": "Araç bulunamadı"}), 404
    
    # Aracın konumunu al
    vehicle_lat = vehicle.latitude
    vehicle_lon = vehicle.longitude
    
    # Şarj istasyonlarını al
    stations = ChargingStation.query.all()
    
    # Otomata motorunu başlat
    if 'smart_suggestion_dfa' in automatas:
        suggestion_automata = automatas['smart_suggestion_dfa']
        suggestion_automata.trigger_event('START_SUGGESTION', {
            'vehicle': vehicle,
            'current_soc': current_soc,
            'target_soc': target_soc,
            'max_waiting_time': max_waiting_time
        })
    
    suggestions = []
    now = datetime.utcnow()
    
    # Her istasyon için hesaplamalar
    for station in stations:
        # Mesafe hesapla
        distance_km = simple_distance(vehicle_lat, vehicle_lon, station.latitude, station.longitude)
        
        # Kalan menzili hesapla (km cinsinden, basit bir hesaplama)
        battery_capacity = vehicle.battery_capacity_kWh
        # Her kWh başına ortalama 5 km menzil varsayalım (bu değer aracın verimliliğine göre değişebilir)
        km_per_kwh = 5  
        remaining_range = (current_soc / 100) * battery_capacity * km_per_kwh
        
        # İstasyona ulaşmak için gereken şarj yeterli mi?
        can_reach = remaining_range >= distance_km
        
        # Şarj süresi hesaplama (dakika cinsinden)
        charge_time_minutes = 0
        if station.max_power_kW and station.max_power_kW > 0:
            energy_needed = ((target_soc - current_soc) / 100) * battery_capacity
            charge_time_minutes = (energy_needed / station.max_power_kW) * 60
        
        # İstasyon şu anda müsait mi?
        is_available = station.status == 'available'
        
        # İstasyonda aktif rezervasyon var mı?
        active_reservation = Reservation.query.filter(
            Reservation.station_id == station.id, 
            Reservation.expected_end_time > now
        ).order_by(Reservation.expected_end_time.desc()).first()
        
        available_after = None
        waiting_time = 0
        
        if active_reservation:
            available_after = active_reservation.expected_end_time
            waiting_time = (available_after - now).total_seconds() / 60  # dakika cinsinden
        
        # Sonuçları hesapla
        suggestion = {
            "station_id": station.id,
            "name": station.name,
            "distance_km": round(distance_km, 2),
            "can_reach": can_reach,
            "is_available_now": is_available,
            "available_after": available_after.isoformat() if available_after else None,
            "waiting_time_minutes": round(waiting_time),
            "charge_time_minutes": round(charge_time_minutes),
            "total_time": round(waiting_time + charge_time_minutes),
            "latitude": station.latitude,
            "longitude": station.longitude,
            "max_power_kW": station.max_power_kW
        }
        
        # Beklemeden şarj olabilecek veya makul bekleme süresi olan istasyonları öner
        if is_available or (active_reservation and waiting_time <= max_waiting_time):
            suggestions.append(suggestion)
    
    # Şarj ve bekleme süresi toplamına göre sırala
    suggestions.sort(key=lambda x: x["total_time"])
    
    # Menzile göre erişilebilir istasyonları filtrele
    reachable_suggestions = [s for s in suggestions if s["can_reach"]]
    
    # Otomata işlem sonucunu güncelle
    if 'smart_suggestion_dfa' in automatas:
        suggestion_automata.trigger_event('DATA_COLLECTED', {
            'suggestions': suggestions,
            'reachable_suggestions': reachable_suggestions
        })
        
        if reachable_suggestions:
            suggestion_automata.trigger_event('NEED_ANALYZED', {})
            suggestion_automata.trigger_event('STATIONS_FOUND', {})
            suggestion_automata.trigger_event('RANKING_COMPLETE', {})
            suggestion_automata.trigger_event('SUGGESTIONS_READY', {})
        else:
            suggestion_automata.trigger_event('INSUFFICIENT_DATA', {})
    
    return jsonify({
        "current_soc": current_soc,
        "target_soc": target_soc,
        "suggestions": reachable_suggestions if reachable_suggestions else suggestions,
        "unreachable_stations": [s for s in suggestions if not s["can_reach"]],
        "total_suggestions": len(suggestions),
        "reachable_count": len(reachable_suggestions)
    }), 200

# Şarj hesaplama fonksiyonları
def calculate_charge_time(battery_capacity_kWh, current_soc, target_soc, charge_power_kW):
    """Şarj için gereken süreyi hesaplar (dakika cinsinden)"""
    if not charge_power_kW or charge_power_kW <= 0:
        return 0
    
    energy_needed = ((target_soc - current_soc) / 100) * battery_capacity_kWh
    hours = energy_needed / charge_power_kW
    return hours * 60  # dakika cinsinden

def calculate_range(battery_capacity_kWh, soc_percent, efficiency_km_per_kwh=5):
    """Mevcut şarj seviyesi ile gidebileceği menzili hesaplar (km cinsinden)"""
    available_energy = (soc_percent / 100) * battery_capacity_kWh
    return available_energy * efficiency_km_per_kwh

def is_station_reachable(vehicle_lat, vehicle_lon, station_lat, station_lon, 
                        battery_capacity_kWh, current_soc, efficiency_km_per_kwh=5):
    """İstasyonun mevcut şarj ile erişilebilir olup olmadığını kontrol eder"""
    distance = simple_distance(vehicle_lat, vehicle_lon, station_lat, station_lon)
    max_range = calculate_range(battery_capacity_kWh, current_soc, efficiency_km_per_kwh)
    return max_range >= distance

def seed_vehicles():
    vehicles = [
        {"brand": "Tesla", "model": "Model 3", "year": 2022, "battery_capacity_kWh": 82, "charge_power_kW": 250, "latitude": 39.758559, "longitude": 30.499763},
        {"brand": "Tesla", "model": "Model Y", "year": 2023, "battery_capacity_kWh": 75, "charge_power_kW": 250, "latitude": 39.756459, "longitude": 30.480146},
        {"brand": "Tesla", "model": "Model S", "year": 2022, "battery_capacity_kWh": 100, "charge_power_kW": 250, "latitude": 39.756881, "longitude": 30.498884},
        {"brand": "Tesla", "model": "Model X", "year": 2022, "battery_capacity_kWh": 100, "charge_power_kW": 250, "latitude": 39.764181, "longitude": 30.524443},
        {"brand": "Porsche", "model": "Taycan", "year": 2021, "battery_capacity_kWh": 93.4, "charge_power_kW": 270, "latitude": 39.750976, "longitude": 30.587070},
        {"brand": "Hyundai", "model": "Ioniq 5", "year": 2022, "battery_capacity_kWh": 77.4, "charge_power_kW": 220, "latitude": 39.769446, "longitude": 30.496591},
        {"brand": "Hyundai", "model": "Kona Electric", "year": 2021, "battery_capacity_kWh": 64, "charge_power_kW": 100, "latitude": 39.754007, "longitude": 30.498004},
        {"brand": "Kia", "model": "EV6", "year": 2022, "battery_capacity_kWh": 77.4, "charge_power_kW": 240, "latitude": 39.784104, "longitude": 30.497901},
        {"brand": "Ford", "model": "Mustang Mach-E", "year": 2022, "battery_capacity_kWh": 88, "charge_power_kW": 150, "latitude": 39.783497, "longitude": 30.512916},
        {"brand": "Volkswagen", "model": "ID.4", "year": 2022, "battery_capacity_kWh": 82, "charge_power_kW": 135, "latitude": 39.783408, "longitude": 30.526231},
        {"brand": "BMW", "model": "i4", "year": 2022, "battery_capacity_kWh": 83.9, "charge_power_kW": 200, "latitude": 39.786492, "longitude": 30.538684},
        {"brand": "BMW", "model": "iX3", "year": 2021, "battery_capacity_kWh": 80, "charge_power_kW": 150, "latitude": 39.789645, "longitude": 30.500814},
        {"brand": "Mercedes", "model": "EQC 400", "year": 2021, "battery_capacity_kWh": 80, "charge_power_kW": 110, "latitude": 39.755684, "longitude": 30.532419},
        {"brand": "Audi", "model": "e-tron", "year": 2021, "battery_capacity_kWh": 95, "charge_power_kW": 150, "latitude": 39.741922, "longitude": 30.459595},
        {"brand": "Nissan", "model": "Leaf e+", "year": 2021, "battery_capacity_kWh": 62, "charge_power_kW": 100, "latitude": 39.815545, "longitude": 30.531786}
    ]

    for v in vehicles:
        vehicle = Vehicle(
            brand=v['brand'],
            model=v['model'],
            year=v['year'],
            battery_capacity_kWh=v['battery_capacity_kWh'],
            charge_power_kW=v['charge_power_kW'],
            latitude=v['latitude'],
            longitude=v['longitude']
        )
        db.session.add(vehicle)
    
    db.session.commit()
    print("Araçlar başarıyla Eskişehir konumlarıyla eklendi!")

def seed_charging_stations():
    if ChargingStation.query.first():
        print("Şarj istasyonları zaten ekli, yeniden eklenmedi.")
        return

    stations = [
        {"name": "Espark", "latitude": 39.782440, "longitude": 30.510626},
        {"name": "Eskişehir Tren İstasyonu", "latitude": 39.779302, "longitude": 30.507559},
        {"name": "Eskişehir Odunpazarı Evleri", "latitude": 39.763709, "longitude": 30.525812},
        {"name": "Eskişehir Sazova Parkı", "latitude": 39.762142, "longitude": 30.475369},
        {"name": "Eskişehir Osmangazi Üniversitesi", "latitude": 39.750579, "longitude": 30.477609},
        {"name": "Anadolu Üniversitesi", "latitude": 39.789803, "longitude": 30.500149},
        {"name": "Kentpark AVM", "latitude": 39.7791, "longitude": 30.5147},
        {"name": "Cassaba Modern", "latitude": 39.769446, "longitude": 30.496591},
        {"name": "Toyota Plaza Sara", "latitude": 39.764233, "longitude": 30.557210},
        {"name": "Şelale Park", "latitude": 39.756218, "longitude": 30.532072}
    ]

    for s in stations:
        station = ChargingStation(
            name=s['name'],
            latitude=s['latitude'],
            longitude=s['longitude'],
            status='Disconnected'  # ✅ Tüm istasyonlar başlangıçta boş kabul ediliyor
        )
        db.session.add(station)

    db.session.commit()
    print("Şarj istasyonları başarıyla eklendi.")

def simple_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Dünya'nın yarıçapı (km)

    # 1) Dereceleri radyana çevir
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # 2) Delta'ları bul
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # 3) Haversine formülünü uygula
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # 4) Mesafeyi hesapla
    distance = R * c
    return distance

# İşleyicileri kaydet
def register_handlers():
    """Otomata sistemine koşul ve eylem işleyicilerini kaydeder"""
    try:
        # Otomata işleyiciler mevcutsa
        if 'smart_suggestion_dfa' in automatas:
            suggestion_engine = automatas['smart_suggestion_dfa']
            
            # Koşul işleyicileri
            suggestion_engine.register_condition_handler('isSufficientData', 
                lambda context: len(context.get('suggestions', [])) > 0)
            
            suggestion_engine.register_condition_handler('hasStationResults', 
                lambda context: len(context.get('reachable_suggestions', [])) > 0)
            
            # Eylem işleyicileri
            suggestion_engine.register_action_handler('initializeSuggestionProcess', 
                lambda context: print(f"Akıllı öneri süreci başlatıldı: Araç ID={context.get('vehicle', {}).get('id')}"))
            
            suggestion_engine.register_action_handler('startDataCollection', 
                lambda context: print(f"Veri toplama başladı: Mevcut SOC={context.get('current_soc')}"))
            
            suggestion_engine.register_action_handler('analyzeUserNeeds', 
                lambda context: print(f"Kullanıcı ihtiyaçları analiz ediliyor: Hedef SOC={context.get('target_soc')}"))
            
            suggestion_engine.register_action_handler('generateSuggestionList', 
                lambda context: print(f"Öneri listesi oluşturuluyor: {len(context.get('suggestions', []))} istasyon bulundu"))
            
        # İstasyon durum otomatası işleyicileri
        if 'charge_station_dfa' in automatas:
            station_engine = automatas['charge_station_dfa']
            
            # Koşul işleyicileri
            station_engine.register_condition_handler('isStationReservable', 
                lambda context: context.get('station_status') == 'available')
            
            station_engine.register_condition_handler('canPlugInWithoutReservation', 
                lambda context: context.get('station_status') == 'available')
            
            # Eylem işleyicileri
            station_engine.register_action_handler('createReservation', 
                lambda context: print(f"İstasyon rezerve edildi: {context.get('station_id')}"))
            
            station_engine.register_action_handler('startCharging', 
                lambda context: print(f"Şarj başlatıldı: {context.get('station_id')}"))
            
            station_engine.register_action_handler('logStateChange', 
                lambda context: print(f"İstasyon durumu değişti: {context.get('station_id')} - {context.get('new_status')}"))
        
        print("✅ Otomata işleyicileri başarıyla kaydedildi")
    except Exception as e:
        print(f"❌ Otomata işleyicileri kaydedilirken hata: {str(e)}")

# Otomata sistemini test etmek için basit bir fonksiyon ekleyelim
def test_automata_system():
    """Otomata sistemini test eden basit fonksiyon"""
    print("\n====== Otomata Testi Başlatılıyor ======")
    
    for automata_id, engine in automatas.items():
        print(f"\nOtomata Testi: {automata_id}")
        print(f"Mevcut durum: {engine.get_current_state()}")
        
        # Mümkün olayları listele
        events = engine.get_possible_events()
        print(f"Olası olaylar: {events}")
        
        # İlk durumun metaverilerini al
        state_id = engine.get_current_state()
        metadata = engine.get_state_metadata(state_id)
        print(f"Durum metadata: {metadata}")
    
    print("\n====== Otomata Testi Tamamlandı ======\n")

if __name__ == '__main__':
    with app.app_context():
        print("\n====== Uygulama Başlatılıyor ======")
        
        db.create_all()
        print("✅ Veritabanı şeması oluşturuldu")
        
        # Testler için araç ve istasyon verileri oluştur
        if Vehicle.query.count() == 0:
            seed_vehicles()
            print(f"✅ {Vehicle.query.count()} adet araç veritabanına eklendi")
        else:
            print(f"ℹ️ Veritabanında zaten {Vehicle.query.count()} adet araç var")
            
        if ChargingStation.query.count() == 0:
            seed_charging_stations()
            print(f"✅ {ChargingStation.query.count()} adet şarj istasyonu veritabanına eklendi")
        else:
            print(f"ℹ️ Veritabanında zaten {ChargingStation.query.count()} adet şarj istasyonu var")
            
        # Otomata işleyicilerini kaydet
        try:
            register_handlers()
            print("✅ Otomata işleyicileri kaydedildi")
            
            # Otomata sistemini test et
            test_automata_system()
            
        except Exception as e:
            print(f"❌ Otomata sistemi başlatılırken hata: {str(e)}")
        
        print("✅ Uygulama başlatıldı. Otomata sistemi entegre edildi.")
        print("====== Uygulama Hazır ======\n")
        
    # Debug modunda uygulamayı başlat
    app.run(debug=True)

