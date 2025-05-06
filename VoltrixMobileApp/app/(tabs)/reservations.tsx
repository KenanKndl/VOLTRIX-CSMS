import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator, TouchableOpacity, Alert, Linking } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { BASE_URL } from '../../constants/config';

// Tip tanımı
type Reservation = {
  id: number;
  station_id: number;
  station_name: string;
  vehicle_id: number;
  vehicle_model: string;
  status: string;
  expected_end_time: string;
};

const ReservationsScreen = () => {
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchReservations = async () => {
    try {
      const userData = await AsyncStorage.getItem('user');
      if (!userData) return;

      const user = JSON.parse(userData);

      const response = await fetch(`${BASE_URL}/reservations/active?user_id=${user.id}`);
      const data = await response.json();

      if (Array.isArray(data)) {
        const now = new Date();
        const active = data.filter(res => new Date(res.expected_end_time) > now);
        setReservations(active);
      }
    } catch (err) {
      console.error('Failed to fetch reservations:', err);
    } finally {
      setLoading(false);
    }
  };

  const cancelReservation = async (reservationId: number) => {
    try {
      const response = await fetch(`${BASE_URL}/reservations/${reservationId}`, {
        method: 'DELETE'
      });
      const result = await response.json();
      Alert.alert('Reservation Cancelled', result.message || 'Reservation has been cancelled.');
      fetchReservations();
    } catch (err) {
      Alert.alert('Error', 'Failed to cancel reservation.');
    }
  };

  const handleCreateRoute = async (item: Reservation) => {
    try {
      const quickData = await AsyncStorage.getItem('quick_action_data');
      if (!quickData) {
        Alert.alert('Error', 'Vehicle location not available. Use Quick Action first.');
        return;
      }

      const { vehicle_id } = JSON.parse(quickData);
      const vehicleRes = await fetch(`${BASE_URL}/vehicles`);
      const vehicleList = await vehicleRes.json();
      const vehicle = vehicleList.find((v: any) => v.id === vehicle_id);

      const stationRes = await fetch(`${BASE_URL}/stations`);
      const stations = await stationRes.json();
      const station = stations.find((s: any) => s.id === item.station_id);

      if (!vehicle || !station) {
        Alert.alert('Error', 'Location data not found.');
        return;
      }

      const url = `https://www.google.com/maps/dir/?api=1&origin=${vehicle.latitude},${vehicle.longitude}&destination=${station.latitude},${station.longitude}&travelmode=driving`;
      Linking.openURL(url);
    } catch (error) {
      Alert.alert('Error', 'Failed to create route.');
    }
  };

  useEffect(() => {
    fetchReservations();
    const interval = setInterval(fetchReservations, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <ActivityIndicator size="large" color="#007bff" style={{ marginTop: 32 }} />;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>My Reservations</Text>

      {reservations.length === 0 ? (
        <Text style={styles.emptyText}>You have no active reservations.</Text>
      ) : (
        <FlatList
          data={reservations}
          keyExtractor={(item) => item.id.toString()}
          renderItem={({ item }) => (
            <View style={styles.card}>
              <Text style={styles.station}>{item.station_name}</Text>
              <Text>Vehicle: {item.vehicle_model}</Text>
              <Text>Status: {item.status}</Text>
              <Text>Ends at: {new Date(item.expected_end_time).toLocaleTimeString()}</Text>

              <View style={styles.buttonRow}>
                <TouchableOpacity style={styles.cancelButton} onPress={() => cancelReservation(item.id)}>
                  <Text style={styles.buttonText}>Cancel</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.routeButton} onPress={() => handleCreateRoute(item)}>
                  <Text style={styles.buttonText}>Create Route</Text>
                </TouchableOpacity>
              </View>
            </View>
          )}
        />
      )}
    </View>
  );
};

export default ReservationsScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  emptyText: {
    textAlign: 'center',
    marginTop: 40,
    color: '#999',
  },
  card: {
    padding: 16,
    marginBottom: 12,
    backgroundColor: '#f4f4f4',
    borderRadius: 10,
    elevation: 2,
  },
  station: {
    fontWeight: 'bold',
    fontSize: 16,
    marginBottom: 4,
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 12,
  },
  cancelButton: {
    backgroundColor: '#ff3b30',
    padding: 10,
    borderRadius: 8,
    flex: 1,
    marginRight: 8,
    alignItems: 'center',
  },
  routeButton: {
    backgroundColor: '#007bff',
    padding: 10,
    borderRadius: 8,
    flex: 1,
    marginLeft: 8,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
  },
});