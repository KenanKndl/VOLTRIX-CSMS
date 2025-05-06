import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
  StyleSheet,
  ScrollView
} from 'react-native';
import * as Location from 'expo-location';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter } from 'expo-router';
import { BASE_URL } from '../constants/config';
import StationCard from '../components/StationCard';

type Station = {
  id: number;
  name: string;
  status: string;
  distance_km: number;
  can_reach: boolean;
  is_available_now: boolean;
  available_after: string | null;
  waiting_time_minutes: number;
  charge_time_minutes: number;
  total_time: number;
  latitude: number;
  longitude: number;
  max_power_kW: number;
};

const SmartStationsScreen = () => {
  const router = useRouter();
  const [stations, setStations] = useState<Station[]>([]);
  const [unreachableStations, setUnreachableStations] = useState<Station[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [vehicleData, setVehicleData] = useState<any>(null);
  const [currentSoc, setCurrentSoc] = useState<number>(30);
  const [targetSoc, setTargetSoc] = useState<number>(80);

  useEffect(() => {
    (async () => {
      try {
        // Kullanıcı verilerini yükle
        const userData = await AsyncStorage.getItem('user');
        const quickData = await AsyncStorage.getItem('quick_action_data');
        
        if (!userData || !quickData) {
          setError('Lütfen önce Quick Action ekranını doldurun');
          setLoading(false);
          return;
        }
        
        const vehicleInfo = JSON.parse(quickData);
        setVehicleData(vehicleInfo);
        
        if (vehicleInfo.currentCharge) {
          setCurrentSoc(parseFloat(vehicleInfo.currentCharge));
        }
        
        if (vehicleInfo.targetCharge) {
          setTargetSoc(parseFloat(vehicleInfo.targetCharge));
        }
        
        // Konum izni iste
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== 'granted') {
          setError('Konum izni verilmedi');
          setLoading(false);
          return;
        }

        const location = await Location.getCurrentPositionAsync({});
        fetchSmartSuggestions(location.coords.latitude, location.coords.longitude, vehicleInfo.vehicle_id);
      } catch (err) {
        console.error('Başlatma hatası:', err);
        setError('Veriler yüklenirken hata oluştu');
        setLoading(false);
      }
    })();
  }, []);

  const fetchSmartSuggestions = async (
    latitude: number,
    longitude: number,
    vehicle_id: number
  ): Promise<void> => {
    try {
      // Aracın konumunu güncelle
      await fetch(`${BASE_URL}/vehicles/${vehicle_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latitude, longitude }),
      });
      
      // Akıllı öneri API'sini çağır
      const response = await fetch(`${BASE_URL}/smart-suggestion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          vehicle_id,
          current_soc: currentSoc,
          target_soc: targetSoc,
          max_waiting_time: 30 // Dakika cinsinden maksimum bekleme süresi
        }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Akıllı öneriler alınamadı');
      }
      
      setStations(data.suggestions || []);
      setUnreachableStations(data.unreachable_stations || []);
    } catch (err: any) {
      console.error('Akıllı öneri hatası:', err);
      setError(err.message || 'İstasyonlar alınamadı');
    } finally {
      setLoading(false);
    }
  };

  const handleReserve = async (station: Station) => {
    if (!vehicleData) {
      Alert.alert('Hata', 'Araç bilgileri bulunamadı');
      return;
    }
    
    try {
      const userData = await AsyncStorage.getItem('user');
      if (!userData) {
        Alert.alert('Eksik Bilgi', 'Kullanıcı bilgileri bulunamadı');
        return;
      }

      const user = JSON.parse(userData);
      const vehicle_id = vehicleData.vehicle_id;

      const response = await fetch(`${BASE_URL}/reservations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          station_id: station.id,
          vehicle_id,
          current_battery_percent: currentSoc,
          target_battery_percent: targetSoc
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Rezervasyon başarısız');
      }

      Alert.alert(
        'Başarılı',
        `Rezervasyon oluşturuldu!\nTahmini şarj süresi: ${station.charge_time_minutes} dk\nBekleme süresi: ${station.waiting_time_minutes} dk\nToplam süre: ${station.total_time} dk`
      );
      
      // Başarılı rezervasyondan sonra geri dön
      router.back();
    } catch (err: any) {
      Alert.alert('Hata', err.message || 'Rezervasyon oluşturulamadı');
    }
  };

  const getStationStatusText = (station: Station) => {
    if (station.is_available_now) {
      return 'Şu an müsait';
    } else if (station.available_after) {
      return `${station.waiting_time_minutes} dakika sonra müsait olacak`;
    }
    return 'Meşgul';
  };

  if (loading) return (
    <View style={styles.centerContainer}>
      <ActivityIndicator size="large" color="#4CAF50" />
      <Text style={styles.loadingText}>Akıllı öneriler hesaplanıyor...</Text>
    </View>
  );
  
  if (error) return (
    <View style={styles.centerContainer}>
      <Text style={styles.errorText}>{error}</Text>
      <TouchableOpacity style={styles.button} onPress={() => router.back()}>
        <Text style={styles.buttonText}>Geri Dön</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <View style={styles.container}>
      {/* Kapat butonu */}
      <TouchableOpacity style={styles.closeButton} onPress={() => router.back()}>
        <Text style={styles.closeButtonText}>Kapat</Text>
      </TouchableOpacity>

      <View style={styles.statusBar}>
        <Text style={styles.statusBarText}>
          Mevcut Şarj: %{currentSoc} → Hedef: %{targetSoc}
        </Text>
      </View>

      <Text style={styles.sectionTitle}>Size Önerilen İstasyonlar:</Text>
      
      {stations.length === 0 ? (
        <Text style={styles.noStationText}>Erişim menzilinizde uygun şarj istasyonu bulunamadı</Text>
      ) : (
        <FlatList
          data={stations}
          keyExtractor={(item) => item.id.toString()}
          renderItem={({ item }) => (
            <TouchableOpacity 
              style={styles.stationCard}
              onPress={() => handleReserve(item)}
            >
              <View style={styles.stationHeader}>
                <Text style={styles.stationName}>{item.name}</Text>
                <Text style={[styles.statusChip, 
                  item.is_available_now ? styles.availableChip : styles.waitingChip
                ]}>
                  {getStationStatusText(item)}
                </Text>
              </View>
              
              <View style={styles.stationDetails}>
                <Text style={styles.detailText}>Mesafe: {item.distance_km.toFixed(1)} km</Text>
                <Text style={styles.detailText}>Şarj Gücü: {item.max_power_kW} kW</Text>
                <Text style={styles.detailText}>Şarj Süresi: {item.charge_time_minutes} dk</Text>
                {!item.is_available_now && item.waiting_time_minutes > 0 && (
                  <Text style={styles.detailText}>Bekleme Süresi: {item.waiting_time_minutes} dk</Text>
                )}
                <Text style={styles.totalTimeText}>Toplam Süre: {item.total_time} dk</Text>
              </View>
              
              <TouchableOpacity 
                style={styles.reserveButton}
                onPress={() => handleReserve(item)}
              >
                <Text style={styles.reserveButtonText}>Rezervasyon Yap</Text>
              </TouchableOpacity>
            </TouchableOpacity>
          )}
        />
      )}
      
      {unreachableStations.length > 0 && (
        <>
          <Text style={styles.unreachableTitle}>Erişilemeyen İstasyonlar:</Text>
          <Text style={styles.unreachableSubtitle}>
            Mevcut şarj seviyenizle bu istasyonlara ulaşamazsınız
          </Text>
          
          <ScrollView style={styles.unreachableList}>
            {unreachableStations.map(station => (
              <View key={station.id} style={styles.unreachableCard}>
                <Text style={styles.unreachableName}>{station.name}</Text>
                <Text style={styles.unreachableDistance}>
                  Mesafe: {station.distance_km.toFixed(1)} km (menzil dışında)
                </Text>
              </View>
            ))}
          </ScrollView>
        </>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 16,
    paddingTop: 48,
    backgroundColor: '#fff',
    flex: 1,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#666',
  },
  errorText: {
    fontSize: 16,
    color: '#F44336',
    marginBottom: 20,
    textAlign: 'center',
  },
  closeButton: {
    alignSelf: 'flex-end',
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#eee',
    borderRadius: 8,
    marginBottom: 8,
  },
  closeButtonText: {
    fontSize: 14,
    color: '#333',
  },
  statusBar: {
    backgroundColor: '#E8F5E9',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },
  statusBarText: {
    fontSize: 16,
    color: '#2E7D32',
    fontWeight: '500',
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 12,
    color: '#333',
  },
  noStationText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginTop: 20,
  },
  stationCard: {
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    elevation: 2,
  },
  stationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  stationName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  statusChip: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 12,
    fontSize: 12,
    fontWeight: '500',
  },
  availableChip: {
    backgroundColor: '#C8E6C9',
    color: '#2E7D32',
  },
  waitingChip: {
    backgroundColor: '#FFECB3',
    color: '#FF8F00',
  },
  stationDetails: {
    marginBottom: 12,
  },
  detailText: {
    fontSize: 14,
    color: '#555',
    marginBottom: 4,
  },
  totalTimeText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 4,
  },
  reserveButton: {
    backgroundColor: '#4CAF50',
    borderRadius: 8,
    padding: 12,
    alignItems: 'center',
  },
  reserveButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 14,
  },
  unreachableTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: 20,
    marginBottom: 4,
    color: '#555',
  },
  unreachableSubtitle: {
    fontSize: 14,
    color: '#777',
    marginBottom: 12,
  },
  unreachableList: {
    maxHeight: 150,
  },
  unreachableCard: {
    backgroundColor: '#FFEBEE',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  unreachableName: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  unreachableDistance: {
    fontSize: 12,
    color: '#F44336',
    marginTop: 4,
  },
  button: {
    backgroundColor: '#2196F3',
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8,
    marginTop: 16,
  },
  buttonText: {
    color: 'white', 
    fontWeight: 'bold',
  },
});

export default SmartStationsScreen;
