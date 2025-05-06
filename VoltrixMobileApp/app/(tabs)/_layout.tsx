import React, { useEffect } from 'react';
import { Tabs } from 'expo-router';
import { View, TouchableOpacity, StyleSheet, Platform } from 'react-native';
import { Ionicons, MaterialCommunityIcons, FontAwesome } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { BASE_URL } from '../../constants/config'; // GÜNCELLENMİŞ YOL

export default function TabLayout() {
  const router = useRouter();

  useEffect(() => {
    const interval = setInterval(() => {
      fetch(`${BASE_URL}/cleanup-expired-reservations`)
        .then(() => console.log('[✓] Temizlik endpointi çağrıldı'))
        .catch(err => console.warn('[!] Temizlik hatası:', err));
    }, 60000); // 60 saniye

    return () => clearInterval(interval);
  }, []);

  return (
    <Tabs
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarShowLabel: true,
        tabBarStyle: {
          height: 70,
          borderTopWidth: 0,
          elevation: 0,
        },
        tabBarIcon: ({ color, focused }) => {
          if (route.name === 'index') {
            return <Ionicons name="home-outline" size={24} color={color} />;
          } else if (route.name === 'reservations') {
            return <FontAwesome name="calendar-check-o" size={24} color={color} />;
          } else if (route.name === 'history') {
            return <Ionicons name="time-outline" size={24} color={color} />;
          } else if (route.name === 'account') {
            return <Ionicons name="person-outline" size={24} color={color} />;
          }
          return null;
        },
      })}
    >
      <Tabs.Screen name="index" options={{ title: 'Home' }} />
      <Tabs.Screen name="reservations" options={{ title: 'Reservations' }} />
      <Tabs.Screen
        name="quick-action"
        options={{
          title: '',
          tabBarIcon: ({ color }) => (
            <View style={styles.quickButtonWrapper}>
              <TouchableOpacity
                style={styles.quickButton}
                onPress={() => router.push('/quick-action')}
              >
                <MaterialCommunityIcons name="flash" size={30} color="white" />
              </TouchableOpacity>
            </View>
          ),
        }}
      />
      <Tabs.Screen name="history" options={{ title: 'History' }} />
      <Tabs.Screen name="account" options={{ title: 'Account' }} />
      {/* smart-stations burada listelenmediği için tab menüsünde görünmez */}
    </Tabs>
  );
}

const styles = StyleSheet.create({
  quickButtonWrapper: {
    position: 'absolute',
    bottom: Platform.OS === 'android' ? 0 : 0,
    justifyContent: 'center',
    alignItems: 'center',
  },
  quickButton: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: '#ff3b30',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.25,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 6,
    elevation: 5,
  },
});
