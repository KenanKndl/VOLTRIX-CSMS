import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView } from 'react-native';
import MapView, { Marker } from 'react-native-maps';
import { BASE_URL } from '../constants/config';

const HomeScreen = () => {
  const [stations, setStations] = useState([]);
  const [selectedStation, setSelectedStation] = useState(null);

  const fetchStations = async () => {
    try {
      const response = await fetch(`${BASE_URL}/stations`);
      const data = await response.json();
      setStations(data);
    } catch (error) {
      console.error('Failed to fetch stations:', error);
    }
  };

  useEffect(() => {
    fetchStations();
    const interval = setInterval(fetchStations, 15000); // Her 15 saniyede bir güncelle
    return () => clearInterval(interval);
  }, []);

  const getPinColor = (status) => {
    switch (status) {
      case 'available': return 'green';
      case 'reserved': return 'orange';
      case 'occupied': return 'red';
      case 'offline': return 'gray';
      default: return 'blue';
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.searchContainer}>
        <TouchableOpacity style={styles.searchBox}>
          <Text style={styles.searchText}>Search Station</Text>
        </TouchableOpacity>
      </View>

      <MapView
        style={styles.map}
        initialRegion={{
          latitude: 39.7767,
          longitude: 30.5206,
          latitudeDelta: 0.05,
          longitudeDelta: 0.05,
        }}
        showsUserLocation
      >
        {stations.map((station) => (
          <Marker
            key={`${station.id}-${station.status}`}
            coordinate={{ latitude: station.latitude, longitude: station.longitude }}
            title={station.name}
            pinColor={getPinColor(station.status)}
            onPress={() => setSelectedStation(station)}
          />
        ))}
      </MapView>

      {selectedStation && (
        <View style={styles.bottomPanel}>
          <Text style={styles.stationName}>{selectedStation.name}</Text>
          <Text>Status: {selectedStation.status}</Text>
        </View>
      )}
    </SafeAreaView>
  );
};

export default HomeScreen;

const styles = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },
  searchContainer: {
    position: 'absolute',
    top: 70,
    width: '100%',
    alignItems: 'center',
    zIndex: 10,
  },
  searchBox: {
    backgroundColor: '#fff',
    width: '90%',
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 16,
    elevation: 5,
  },
  searchText: {
    color: '#888',
  },
  bottomPanel: {
    position: 'absolute',
    bottom: 0,
    width: '100%',
    padding: 16,
    backgroundColor: 'white',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    elevation: 10,
  },
  stationName: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 8,
  },
});