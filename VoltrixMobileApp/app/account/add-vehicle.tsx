import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, StyleSheet, TouchableOpacity, Alert, ScrollView, KeyboardAvoidingView, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { BASE_URL } from '../../constants/config';

interface Vehicle {
  id: number; // vehicle_id (gerçek araç ID'si)
  brand: string;
  model: string;
  year: number;
  battery_capacity_kWh: number;
  charge_power_kW: number;
  latitude: number;
  longitude: number;
}

const AddVehicleScreen = () => {
  const router = useRouter();
  const [vehiclesList, setVehiclesList] = useState<Vehicle[]>([]);
  const [brand, setBrand] = useState<string | undefined>();
  const [model, setModel] = useState<string | undefined>();
  const [year, setYear] = useState<number | undefined>();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchVehicles = async () => {
      try {
        const response = await fetch(`${BASE_URL}/vehicles`);
        const data = await response.json();
        setVehiclesList(data);
      } catch (error) {
        console.error('Failed to fetch vehicles:', error);
      }
    };
    fetchVehicles();
  }, []);

  const handleSubmit = async () => {
    if (!brand || !model || !year) {
      Alert.alert('Missing Fields', 'Please select brand, model, and year.');
      return;
    }
  
    try {
      const userData = await AsyncStorage.getItem('user');
      if (!userData) {
        Alert.alert('Error', 'User information not found.');
        return;
      }
  
      const user = JSON.parse(userData);
  
      const selectedVehicle = vehiclesList.find(
        (v) => v.brand === brand && v.model === model && v.year === year
      );
  
      if (!selectedVehicle) {
        Alert.alert('Error', 'Selected vehicle not found.');
        return;
      }
  
      const existingResponse = await fetch(`${BASE_URL}/user-vehicles?user_id=${user.id}`);
      const existingVehicles = await existingResponse.json();
  
      const alreadyExists = existingVehicles.some(
        (v: Vehicle) => v.brand === selectedVehicle.brand && v.model === selectedVehicle.model && v.year === selectedVehicle.year
      );
  
      if (alreadyExists) {
        Alert.alert('Duplicate Vehicle', 'This vehicle already exists in your list.');
        return;
      }
  
      const response = await fetch(`${BASE_URL}/user-vehicles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          vehicle_id: selectedVehicle.id, // 🔥 Gerçek backend vehicle_id
          brand: selectedVehicle.brand,
          model: selectedVehicle.model,
          year: selectedVehicle.year,
          battery_capacity_kWh: selectedVehicle.battery_capacity_kWh,
          charge_power_kW: selectedVehicle.charge_power_kW,
          latitude: selectedVehicle.latitude,
          longitude: selectedVehicle.longitude,
        }),
      });
  
      const result = await response.json();
  
      if (!response.ok) {
        throw new Error(result.error || 'Failed to add vehicle.');
      }
  
      Alert.alert('Success', 'Vehicle added successfully.');
      router.back();
    } catch (error: any) {
      console.error('Add vehicle error:', error.message);
      Alert.alert('Error', error.message || 'Failed to add vehicle.');
    }
  };
  
  

  const availableBrands = [...new Set(vehiclesList.map(v => v.brand))];
  const availableModels = brand ? [...new Set(vehiclesList.filter(v => v.brand === brand).map(v => v.model))] : [];
  const availableYears = brand && model ? [...new Set(vehiclesList.filter(v => v.brand === brand && v.model === model).map(v => v.year))] : [];

  return (
    <KeyboardAvoidingView
      style={{ flex: 1 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.backButton}>{'< Back'}</Text>
        </TouchableOpacity>

        <Text style={styles.title}>Add Vehicle</Text>

        {/* Marka Seçimi */}
        <Text style={styles.label}>Brand</Text>
        {availableBrands.map((b) => (
          <TouchableOpacity
            key={b}
            style={styles.selector}
            onPress={() => {
              setBrand(b);
              setModel(undefined);
              setYear(undefined);
            }}
          >
            <Text style={styles.selectorText}>{b}</Text>
          </TouchableOpacity>
        ))}

        {/* Model Seçimi */}
        {brand && (
          <>
            <Text style={styles.label}>Model</Text>
            {availableModels.map((m) => (
              <TouchableOpacity
                key={m}
                style={styles.selector}
                onPress={() => {
                  setModel(m);
                  setYear(undefined);
                }}
              >
                <Text style={styles.selectorText}>{m}</Text>
              </TouchableOpacity>
            ))}
          </>
        )}

        {/* Yıl Seçimi */}
        {model && (
          <>
            <Text style={styles.label}>Year</Text>
            {availableYears.map((y) => (
              <TouchableOpacity
                key={y}
                style={styles.selector}
                onPress={() => setYear(y)}
              >
                <Text style={styles.selectorText}>{y}</Text>
              </TouchableOpacity>
            ))}
          </>
        )}

        <TouchableOpacity style={styles.button} onPress={handleSubmit}>
          <Text style={styles.buttonText}>Save Vehicle</Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    justifyContent: 'flex-start',
    padding: 24,
    backgroundColor: '#fff',
  },
  backButton: {
    color: '#007bff',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 24,
    textAlign: 'center',
  },
  label: {
    fontSize: 16,
    marginTop: 16,
    marginBottom: 8,
    fontWeight: '500',
  },
  selector: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    marginBottom: 8,
  },
  selectorText: {
    fontSize: 16,
  },
  button: {
    backgroundColor: '#007bff',
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 24,
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
});

export default AddVehicleScreen;
