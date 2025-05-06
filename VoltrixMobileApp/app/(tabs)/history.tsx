import React, { useState } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useFocusEffect } from '@react-navigation/native';
import { BASE_URL } from '../../constants/config';

interface HistoryReservation {
  reservation_id: number;
  station_name: string;
  vehicle_model: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  status: string;
}

const HistoryScreen = () => {
  const [history, setHistory] = useState<HistoryReservation[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchHistory = async () => {
    try {
      const userData = await AsyncStorage.getItem('user');
      if (!userData) return;
      const user = JSON.parse(userData);

      const response = await fetch(`${BASE_URL}/reservations?user_id=${user.id}`);
      const data = await response.json();
      setHistory(data);
    } catch (err) {
      console.error('Failed to fetch history:', err);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    React.useCallback(() => {
      setLoading(true);
      fetchHistory();
    }, [])
  );

  if (loading) {
    return <ActivityIndicator size="large" color="#007bff" style={{ marginTop: 32 }} />;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Charging History</Text>

      {history.length === 0 ? (
        <Text style={styles.emptyText}>You have no completed reservations.</Text>
      ) : (
        <FlatList
          data={history}
          keyExtractor={(item) => item.reservation_id.toString()}
          renderItem={({ item }) => (
            <View style={styles.card}>
              <Text style={styles.label}>Station:</Text>
              <Text style={styles.value}>{item.station_name}</Text>

              <Text style={styles.label}>Vehicle:</Text>
              <Text style={styles.value}>{item.vehicle_model}</Text>

              <Text style={styles.label}>Start:</Text>
              <Text style={styles.value}>{new Date(item.start_time).toLocaleString()}</Text>

              <Text style={styles.label}>End:</Text>
              <Text style={styles.value}>{new Date(item.end_time).toLocaleString()}</Text>

              <Text style={styles.label}>Duration:</Text>
              <Text style={styles.value}>{item.duration_minutes} min</Text>

              <Text style={styles.label}>Status:</Text>
              <Text style={styles.value}>{item.status}</Text>
            </View>
          )}
        />
      )}
    </View>
  );
};

export default HistoryScreen;

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
  label: {
    fontWeight: 'bold',
  },
  value: {
    marginBottom: 6,
  },
});