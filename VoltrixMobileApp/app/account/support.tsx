import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Linking } from 'react-native';
import { useRouter } from 'expo-router';

export default function SupportScreen() {
  const router = useRouter();

  const handleEmail = () => {
    Linking.openURL('mailto:support@example.com');
  };

  return (
    <View style={styles.container}>
      <TouchableOpacity onPress={() => router.back()}>
        <Text style={styles.back}>{'<'} Back</Text>
      </TouchableOpacity>

      <Text style={styles.title}>Support</Text>
      <Text style={styles.text}>If you need help, feel free to contact us:</Text>

      <TouchableOpacity onPress={handleEmail}>
        <Text style={styles.link}>support@example.com</Text>
      </TouchableOpacity>

      <Text style={styles.text}>We usually respond within 24 hours.</Text>
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
  link: {
    fontSize: 16,
    color: '#007bff',
    marginBottom: 16,
  },
});
