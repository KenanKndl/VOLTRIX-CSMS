import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Alert, ActivityIndicator } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { BASE_URL } from '../../constants/config';

interface Vehicle {
  id: number;
  brand: string;
  model: string;
  year: number;
  battery_capacity_kWh: number;
  charge_power_kW: number;
  latitude: number;
  longitude: number;
}

export default function MyVehiclesScreen() {
  const router = useRouter();
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(false);

  const loadVehicles = async () => {
    try {
      setLoading(true);

      const userData = await AsyncStorage.getItem('user');
      if (!userData) {
        Alert.alert('Error', 'User information not found.');
        return;
      }

      const user = JSON.parse(userData || '{}');
      console.log('MyVehicles - User ID:', user.id);

      const response = await fetch(`${BASE_URL}/user-vehicles?user_id=${user.id}`);
      const data = await response.json();

      console.log('MyVehicles - Fetched Vehicles:', data);

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch vehicles.');
      }

      setVehicles(data);
    } catch (error: any) {
      console.error('Failed to load vehicles:', error.message);
      Alert.alert('Error', error.message || 'Failed to load vehicles.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (vehicleId: number) => {
    Alert.alert(
      "Delete Vehicle",
      "Are you sure you want to delete this vehicle?",
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              const response = await fetch(`${BASE_URL}/user-vehicles/${vehicleId}`, {
                method: 'DELETE',
              });

              if (!response.ok) {
                throw new Error('Failed to delete vehicle.');
              }

              Alert.alert('Deleted', 'Vehicle deleted successfully.');
              loadVehicles(); // Listeyi yenile
            } catch (error: any) {
              console.error('Delete vehicle error:', error.message);
              Alert.alert('Error', error.message || 'Failed to delete vehicle.');
            }
          }
        }
      ],
      { cancelable: true }
    );
  };

  useFocusEffect(
    React.useCallback(() => {
      loadVehicles();
    }, [])
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007bff" />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <TouchableOpacity onPress={() => router.back()}>
        <Text style={styles.back}>{'<'} Back</Text>
      </TouchableOpacity>

      <Text style={styles.title}>My Vehicles</Text>

      {vehicles.length === 0 && <Text style={styles.empty}>No vehicles added.</Text>}

      {vehicles.map((v) => (
        <View key={v.id} style={styles.card}>
          <Text style={styles.label}>{v.brand} {v.model} ({v.year})</Text>

          <TouchableOpacity style={styles.deleteButton} onPress={() => handleDelete(v.id)}>
            <Text style={styles.deleteText}>Delete</Text>
          </TouchableOpacity>
        </View>
      ))}

      <TouchableOpacity style={styles.addButton} onPress={() => router.push('/account/add-vehicle')}>
        <Text style={styles.addButtonText}>+ Add New Vehicle</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, backgroundColor: '#fff' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#fff' },
  back: { color: '#007bff', fontSize: 16, marginBottom: 12 },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 24 },
  empty: { fontSize: 16, color: '#999', textAlign: 'center', marginBottom: 16 },
  card: { backgroundColor: '#F3F3F3', borderRadius: 12, padding: 16, marginBottom: 24 },
  label: { fontSize: 18, fontWeight: '600', marginBottom: 8 },
  deleteButton: { backgroundColor: '#ff4d4d', paddingVertical: 8, borderRadius: 8, alignItems: 'center', marginTop: 8 },
  deleteText: { color: 'white', fontWeight: 'bold' },
  addButton: { backgroundColor: '#007bff', paddingVertical: 12, borderRadius: 10, alignItems: 'center' },
  addButtonText: { color: 'white', fontWeight: 'bold' },
});
