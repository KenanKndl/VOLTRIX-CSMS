import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, StyleSheet, TouchableOpacity, Alert, KeyboardAvoidingView, ScrollView, Platform, ActivityIndicator, Linking } from 'react-native';
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

interface UserVehicle {
  id: number;
  brand: string;
  model: string;
  year: number;
  battery_capacity_kWh: number;
  charge_power_kW: number;
  latitude: number;
  longitude: number;
}

const QuickActionScreen = () => {
  const router = useRouter();
  const [vehicles, setVehicles] = useState<UserVehicle[]>([]);
  const [fullVehiclesList, setFullVehiclesList] = useState<Vehicle[]>([]);
  const [selectedVehicle, setSelectedVehicle] = useState<UserVehicle | undefined>();
  const [currentCharge, setCurrentCharge] = useState('');
  const [targetCharge, setTargetCharge] = useState('');
  const [loading, setLoading] = useState(false);

  useFocusEffect(
    React.useCallback(() => {
      const loadVehicles = async () => {
        try {
          setLoading(true);

          const userData = await AsyncStorage.getItem('user');
          if (!userData) {
            Alert.alert('Error', 'User information not found.');
            return;
          }

          const user = JSON.parse(userData || '{}');

          const response = await fetch(`${BASE_URL}/user-vehicles?user_id=${user.id}`);
          const data = await response.json();

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

      loadVehicles();
    }, [])
  );

  useEffect(() => {
    const fetchFullVehicles = async () => {
      try {
        const response = await fetch(`${BASE_URL}/vehicles`);
        const data = await response.json();
        setFullVehiclesList(data);
      } catch (error) {
        console.error('Failed to fetch full vehicles list:', error);
      }
    };

    fetchFullVehicles();
  }, []);

  const handleVehicleSelect = () => {
    if (vehicles.length === 0) {
      Alert.alert('No Vehicles', 'Please add a vehicle first.');
      return;
    }

    const options = vehicles.map(v => `${v.brand} ${v.model} (${v.year})`);
    options.push('Cancel');

    Alert.alert(
      "Select a Vehicle",
      "",
      options.map((option, index) => ({
        text: option,
        onPress: () => {
          if (option !== 'Cancel') {
            setSelectedVehicle(vehicles[index]);
          }
        },
        style: option === 'Cancel' ? 'cancel' : 'default'
      })),
      { cancelable: true }
    );
  };

  const handleReserve = async (station: any, vehicleId: number) => {
    try {
      const userData = await AsyncStorage.getItem('user');
      const user = JSON.parse(userData || '{}');

      const response = await fetch(`${BASE_URL}/reservations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          station_id: station.id,
          vehicle_id: vehicleId,
          current_battery_percent: Number(currentCharge),
          target_battery_percent: Number(targetCharge)
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Reservation failed');
      }

      Alert.alert('Success', `Reservation confirmed!\nEst. Duration: ${data.estimated_duration_min} min\nEnds at: ${new Date(data.expected_end_time).toLocaleTimeString()}`);
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to create reservation.');
    }
  };

  const handleFindStation = async () => {
    if (!selectedVehicle) {
      Alert.alert('Error', 'Selected vehicle not found.');
      return;
    }

    const current = Number(currentCharge);
    const target = Number(targetCharge);

    if (isNaN(current) || isNaN(target) || current < 0 || current > 100 || target < 0 || target > 100 || target <= current) {
      Alert.alert('Invalid Input', 'Please ensure charge levels are between 0-100 and target > current.');
      return;
    }

    const matchedVehicle = fullVehiclesList.find(
      (v) => v.brand === selectedVehicle.brand && v.model === selectedVehicle.model && v.year === selectedVehicle.year
    );

    if (!matchedVehicle) {
      Alert.alert('Error', 'Matched vehicle not found.');
      return;
    }

    const realVehicleId = matchedVehicle.id;

    await AsyncStorage.setItem('quick_action_data', JSON.stringify({
      currentCharge: current,
      targetCharge: target,
      vehicle_id: realVehicleId
    }));

    try {
      const response = await fetch(`${BASE_URL}/quick_action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vehicle_id: realVehicleId,
          current_battery_percentage: current,
          target_battery_percentage: target,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Station finding failed');
      }

      if (data.nearest_station) {
        Alert.alert(
          "Create Route",
          `Recommended Station: ${data.nearest_station.name}\n\nWould you like to create a route or reserve?`,
          [
            { text: 'Cancel', style: 'cancel' },
            {
              text: 'Create Route',
              onPress: () => {
                const url = `https://www.google.com/maps/dir/?api=1&origin=${selectedVehicle.latitude},${selectedVehicle.longitude}&destination=${data.nearest_station.latitude},${data.nearest_station.longitude}&travelmode=driving`;
                Linking.openURL(url);
              },
            },
            {
              text: 'Reserve',
              onPress: () => handleReserve(data.nearest_station, realVehicleId),
            },
          ],
          { cancelable: true }
        );
      } else {
        Alert.alert('No Stations Found', data.message || 'No reachable station found.');
      }
    } catch (error: any) {
      console.error('Find station error:', error.message);
      Alert.alert('Error', error.message || 'Failed to find the best station.');
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007bff" />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.backButton}>{'< Back'}</Text>
        </TouchableOpacity>

        <Text style={styles.title}>Quick Action</Text>

        <Text style={styles.label}>Selected Vehicle:</Text>
        <TouchableOpacity style={styles.selector} onPress={handleVehicleSelect}>
          <Text style={styles.selectorText}>
            {selectedVehicle ? `${selectedVehicle.brand} ${selectedVehicle.model} (${selectedVehicle.year})` : "Select a vehicle"}
          </Text>
        </TouchableOpacity>

        <Text style={styles.label}>Current Battery Level (%):</Text>
        <TextInput
          style={styles.input}
          placeholder="e.g. 35"
          placeholderTextColor="#999"
          value={currentCharge}
          onChangeText={setCurrentCharge}
          keyboardType="numeric"
        />

        <Text style={styles.label}>Target Battery Level (%):</Text>
        <TextInput
          style={styles.input}
          placeholder="e.g. 90"
          placeholderTextColor="#999"
          value={targetCharge}
          onChangeText={setTargetCharge}
          keyboardType="numeric"
        />

        <TouchableOpacity style={styles.button} onPress={handleFindStation}>
          <Text style={styles.buttonText}>Find Best Station</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#fff',
  },
  backButton: {
    color: '#007bff',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 26,
    fontWeight: 'bold',
    marginBottom: 32,
    textAlign: 'center',
  },
  label: {
    fontSize: 16,
    color: '#666',
    marginTop: 12,
  },
  selector: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: 12,
    marginTop: 4,
  },
  selectorText: {
    fontSize: 16,
    color: '#000',
  },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    marginTop: 4,
  },
  button: {
    marginTop: 32,
    backgroundColor: '#007bff',
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
});

export default QuickActionScreen;