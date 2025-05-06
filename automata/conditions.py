"""
Otomata Koşul Fonksiyonları.

Bu modül, sistemdeki otomata yapılarının geçişlerinde kullanılacak 
koşul (condition) fonksiyonlarını içerir.
"""

import logging
from typing import Dict, Any
from datetime import datetime, timedelta

# Logger oluştur
logger = logging.getLogger("automata-conditions")

# -----------------------------------------------------------------------
# Şarj İstasyonu Durum Otomatası Koşul Fonksiyonları
# -----------------------------------------------------------------------

def isStationReservable(context: Dict[str, Any]) -> bool:
    """İstasyonun rezerve edilebilir olup olmadığını kontrol eden fonksiyon
    
    Returns:
        bool: İstasyon rezerve edilebilir ise True, değilse False
    """
    station_id = context.get("station_id", "unknown")
    is_available = context.get("is_available", False)
    
    if not is_available:
        logger.info(f"İstasyon rezerve edilemez: {station_id} (Durum: Müsait Değil)")
        return False
        
    return True

def canPlugInWithoutReservation(context: Dict[str, Any]) -> bool:
    """Rezervasyon olmadan bağlantı kurulabilir mi kontrol eden fonksiyon
    
    Returns:
        bool: Rezervasyon olmadan bağlantı kurulabilir ise True, değilse False
    """
    station_id = context.get("station_id", "unknown")
    allow_direct_plugin = context.get("allow_direct_plugin", True)
    
    if not allow_direct_plugin:
        logger.info(f"Doğrudan bağlantıya izin verilmiyor: {station_id}")
        return False
        
    return True

def isReservationValid(context: Dict[str, Any]) -> bool:
    """Rezervasyonun geçerli olup olmadığını kontrol eden fonksiyon
    
    Returns:
        bool: Rezervasyon geçerli ise True, değilse False
    """
    reservation_id = context.get("reservation_id", "unknown")
    user_id = context.get("user_id", "unknown")
    current_time = datetime.now()
    reservation_expiry = context.get("reservation_expiry", current_time - timedelta(minutes=1))
    
    # Rezervasyon süresi geçmiş mi kontrol et
    if current_time > reservation_expiry:
        logger.info(f"Rezervasyon süresi dolmuş: {reservation_id} (Kullanıcı: {user_id})")
        return False
    
    # Geçerli kullanıcı mı kontrol et
    if context.get("reservation_user_id") != user_id:
        logger.info(f"Kullanıcı eşleşmiyor: {reservation_id} (Beklenen: {context.get('reservation_user_id')}, Gelen: {user_id})")
        return False
        
    return True

# -----------------------------------------------------------------------
# İstasyon Bakım/Arıza Yönetim Otomatası Koşul Fonksiyonları
# -----------------------------------------------------------------------

def isAutoClearable(context: Dict[str, Any]) -> bool:
    """Arızanın otomatik olarak temizlenebilir olup olmadığını kontrol eden fonksiyon
    
    Returns:
        bool: Arıza otomatik temizlenebilir ise True, değilse False
    """
    fault_code = context.get("fault_code", "unknown")
    auto_clearable_codes = context.get("auto_clearable_codes", [])
    
    return fault_code in auto_clearable_codes

def isMaintenanceCompleted(context: Dict[str, Any]) -> bool:
    """Bakımın tamamlanıp tamamlanmadığını kontrol eden fonksiyon
    
    Returns:
        bool: Bakım tamamlandıysa True, değilse False
    """
    maintenance_id = context.get("maintenance_id", "unknown")
    maintenance_checks = context.get("maintenance_checks", {})
    
    # Tüm kontrollerin tamamlanmış olması gerekiyor
    for check, status in maintenance_checks.items():
        if not status:
            logger.info(f"Bakım tamamlanmadı: {maintenance_id} (Eksik Kontrol: {check})")
            return False
            
    return True

def isMaintenanceCancellable(context: Dict[str, Any]) -> bool:
    """Bakımın iptal edilebilir olup olmadığını kontrol eden fonksiyon
    
    Returns:
        bool: Bakım iptal edilebilir ise True, değilse False
    """
    maintenance_id = context.get("maintenance_id", "unknown")
    maintenance_status = context.get("maintenance_status", "scheduled")
    
    # Sadece henüz başlamamış bakımlar iptal edilebilir
    if maintenance_status != "scheduled":
        logger.info(f"Bakım iptal edilemez: {maintenance_id} (Durum: {maintenance_status})")
        return False
        
    return True

# -----------------------------------------------------------------------
# Kullanıcı Rezervasyon Süreci Otomatası Koşul Fonksiyonları
# -----------------------------------------------------------------------

def isStationAvailable(context: Dict[str, Any]) -> bool:
    """İstasyonun müsait olup olmadığını kontrol eden fonksiyon
    
    Returns:
        bool: İstasyon müsait ise True, değilse False
    """
    station_id = context.get("station_id", "unknown")
    station_status = context.get("station_status", "unknown")
    
    if station_status != "AVAILABLE":
        logger.info(f"İstasyon müsait değil: {station_id} (Durum: {station_status})")
        return False
        
    return True

def isWithinReservationTime(context: Dict[str, Any]) -> bool:
    """Rezervasyon süresi içinde olup olmadığını kontrol eden fonksiyon
    
    Returns:
        bool: Rezervasyon süresi içindeyse True, değilse False
    """
    reservation_id = context.get("reservation_id", "unknown")
    current_time = datetime.now()
    reservation_expiry = context.get("reservation_expiry", current_time - timedelta(minutes=1))
    
    if current_time > reservation_expiry:
        logger.info(f"Rezervasyon süresi dolmuş: {reservation_id}")
        return False
        
    return True

def canStartCharging(context: Dict[str, Any]) -> bool:
    """Şarj işleminin başlatılabilir olup olmadığını kontrol eden fonksiyon
    
    Returns:
        bool: Şarj başlatılabilir ise True, değilse False
    """
    vehicle_id = context.get("vehicle_id", "unknown")
    station_id = context.get("station_id", "unknown")
    vehicle_connected = context.get("vehicle_connected", False)
    
    if not vehicle_connected:
        logger.info(f"Araç bağlı değil: {vehicle_id} (İstasyon: {station_id})")
        return False
        
    return True

# -----------------------------------------------------------------------
# Bildirim Akış Otomatası Koşul Fonksiyonları
# -----------------------------------------------------------------------

def canRetry(context: Dict[str, Any]) -> bool:
    """Bildirim tekrar denemesi yapılabilir mi kontrol eden fonksiyon
    
    Returns:
        bool: Tekrar denemesi yapılabilir ise True, değilse False
    """
    notification_id = context.get("notification_id", "unknown")
    max_retries = context.get("max_retries", 3)
    current_retry = context.get("retry_count", 0)
    
    if current_retry >= max_retries:
        logger.info(f"Maksimum deneme sayısına ulaşıldı: {notification_id} (Denemeler: {current_retry}/{max_retries})")
        return False
        
    return True

# -----------------------------------------------------------------------
# Akıllı Rezervasyon Öneri Süreci Otomatası Koşul Fonksiyonları
# -----------------------------------------------------------------------

def isSufficientData(context: Dict[str, Any]) -> bool:
    """Yeterli veri toplanıp toplanmadığını kontrol eden fonksiyon
    
    Returns:
        bool: Yeterli veri varsa True, değilse False
    """
    user_id = context.get("user_id", "unknown")
    required_fields = ["user_location", "battery_level", "destination"]
    collected_data = context.get("collected_data", {})
    
    for field in required_fields:
        if field not in collected_data or not collected_data[field]:
            logger.info(f"Eksik veri: {field} (Kullanıcı: {user_id})")
            return False
            
    return True

def hasStationResults(context: Dict[str, Any]) -> bool:
    """İstasyon sonuçları olup olmadığını kontrol eden fonksiyon
    
    Returns:
        bool: İstasyon sonuçları varsa True, değilse False
    """
    user_id = context.get("user_id", "unknown")
    stations = context.get("found_stations", [])
    
    if not stations:
        logger.info(f"İstasyon sonucu bulunamadı (Kullanıcı: {user_id})")
        return False
        
    return True

# -----------------------------------------------------------------------
# Koşul Kayıt Fonksiyonu
# -----------------------------------------------------------------------

def register_condition_handlers(automata_engine, context=None):
    """
    Otomata motoruna koşul işleyicilerini kaydeder.
    
    Args:
        automata_engine: Koşulların kaydedileceği otomata motoru
        context: Koşulların değerlendirilmesi için gerekli bağlam verileri
    """
    if not automata_engine:
        logger.error("Otomata motoru null, koşullar kaydedilemedi")
        return
        
    # Şarj İstasyonu koşulları
    automata_engine.register_condition_handler('isStationReservable', isStationReservable)
    automata_engine.register_condition_handler('canPlugInWithoutReservation', canPlugInWithoutReservation)
    automata_engine.register_condition_handler('isReservationValid', isReservationValid)
    
    # Bakım/Arıza koşulları
    automata_engine.register_condition_handler('isAutoClearable', isAutoClearable)
    automata_engine.register_condition_handler('isMaintenanceCompleted', isMaintenanceCompleted)
    automata_engine.register_condition_handler('isMaintenanceCancellable', isMaintenanceCancellable)
    
    # Rezervasyon süreci koşulları
    automata_engine.register_condition_handler('isStationAvailable', isStationAvailable)
    automata_engine.register_condition_handler('isWithinReservationTime', isWithinReservationTime)
    automata_engine.register_condition_handler('canStartCharging', canStartCharging)
    
    # Bildirim akışı koşulları
    automata_engine.register_condition_handler('canRetry', canRetry)
    
    # Akıllı öneri koşulları
    automata_engine.register_condition_handler('isSufficientData', isSufficientData)
    automata_engine.register_condition_handler('hasStationResults', hasStationResults)
    
    logger.info("Tüm koşul işleyicileri başarıyla kaydedildi") 