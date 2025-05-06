import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';

export default function AboutScreen() {
  const router = useRouter();

  return (
    <View style={styles.container}>
      <TouchableOpacity onPress={() => router.back()}>
        <Text style={styles.back}>{'<'} Back</Text>
      </TouchableOpacity>

      <Text style={styles.title}>About This App</Text>
      <Text style={styles.text}>
        This mobile application helps users locate nearby EV charging stations, manage their electric vehicles, and
        monitor past charging sessions with ease.
      </Text>

      <Text style={styles.text}>
        Developed using React Native and Expo for a seamless cross-platform experience.
      </Text>

      <Text style={styles.text}>Version: 1.0.0</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    backgroundColor: '#fff',
  },
  back: {
    color: '#007bff',
    fontSize: 16,
    marginBottom: 12,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 24,
  },
  text: {
    fontSize: 16,
    marginBottom: 12,
  },
});
