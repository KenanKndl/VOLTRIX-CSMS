from enum import Enum

class MessageType(str, Enum):
    CONNECTION_REQUEST = "ConnectionRequest"  
    # EV, EVSE ile bağlantı kurmak istediğini bildirir.

    CONNECTION_RESPONSE = "ConnectionResponse"  
    # EVSE, bağlantı isteğini kabul eder veya reddeder.

    EV_INFORMATION_REQUEST = "EVInformationRequest"  
    # EV, batarya durumu gibi bilgilerini paylaşmak üzere EVSE’den bilgi gönderimini başlatır.

    EV_INFORMATION_RESPONSE = "EVInformationResponse"  
    # EVSE, EV’den gelen bilgi isteğine yanıt verir. Batarya kapasitesi, şarj gücü vb. döner.

    CHARGING_START_REQUEST = "ChargingStartRequest"  
    # EV, şarja başlamak istediğini belirtir. Şarj modu ve talep edilen enerji miktarı içerir.

    CHARGING_START_RESPONSE = "ChargingStartResponse"  
    # EVSE, şarj isteğini kabul eder ve şarjı başlattığını bildirir.

    CHARGING_STOP_REQUEST = "ChargingStopRequest"  
    # EV, şarjı sonlandırmak istediğini bildirir.

    CHARGING_STOP_RESPONSE = "ChargingStopResponse"  
    # EVSE, şarjın başarıyla durdurulduğunu bildirir.

    CHARGING_STATUS_UPDATE = "ChargingStatusUpdate"  
    # EV, periyodik olarak şarj durumu bilgilerini gönderir (şu anki SOC, güç tüketimi, süre vs.).

    CHARGING_COMPLETE_NOTIFICATION = "ChargingCompleteNotification"  
    # EV, hedef SOC'ye ulaştığını ve şarjı tamamladığını bildirir.

    DISCONNECTION_REQUEST = "DisconnectionRequest"  
    # EV, artık bağlantıyı sonlandırmak istediğini bildirir (fişi çekmek gibi düşünebilirsin).

    DISCONNECTION_RESPONSE = "DisconnectionResponse"  
    # EVSE, bağlantının sonlandırıldığını onaylar.
