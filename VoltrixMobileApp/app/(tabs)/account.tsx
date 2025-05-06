import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Alert, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function AccountTabScreen() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);
  const router = useRouter();

  useEffect(() => {
    const checkLoginStatus = async () => {
      const isLogged = await AsyncStorage.getItem('isLoggedIn');
      const userData = await AsyncStorage.getItem('user');
      if (isLogged === 'true' && userData) {
        setIsLoggedIn(true);
        setUser(JSON.parse(userData));
      } else {
        setIsLoggedIn(false);
        setUser(null);
      }
    };
    checkLoginStatus();
  }, []);

  const handleLogout = () => {
    Alert.alert('Log out', 'Are you sure you want to log out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log out',
        style: 'destructive',
        onPress: async () => {
          await AsyncStorage.removeItem('isLoggedIn');
          await AsyncStorage.removeItem('user');
          setIsLoggedIn(false);
          setUser(null);
        },
      },
    ]);
  };

  const goToProtected = (route: any) => {
    if (isLoggedIn) {
      router.push(route);
    } else {
      router.push('/login');
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.headerBox}>
        {isLoggedIn && user ? (
          <TouchableOpacity style={styles.profileContainer} onPress={() => router.push('/account/profile-info')}>
            <View>
              <Text style={styles.profileName}>{user.name}</Text>
              <Text style={styles.profileEmail}>{user.email}</Text>
            </View>
            <View style={styles.avatar} />
          </TouchableOpacity>
        ) : (
          <TouchableOpacity style={styles.loginButton} onPress={() => router.push('/login')}>
            <Text style={styles.loginText}>Log In / Register</Text>
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.section}>
        <TouchableOpacity style={styles.cardItem} onPress={() => goToProtected('/account/profile-info')}>
          <Text style={styles.itemText}>Profile</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.cardItem} onPress={() => goToProtected('/account/my-vehicles')}>
          <Text style={styles.itemText}>My Vehicles</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.cardItem} onPress={() => router.push('/account/support')}>
          <Text style={styles.itemText}>Support</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.cardItem} onPress={() => router.push('/account/about')}>
          <Text style={styles.itemText}>About</Text>
        </TouchableOpacity>
      </View>

      {isLoggedIn && (
        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Text style={styles.logoutText}>Log Out</Text>
        </TouchableOpacity>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#F9F9F9',
    padding: 20,
    paddingTop: Platform.OS === 'ios' ? 64 : 32,  // 🔥 iOS için üst boşluk artırıldı
    flexGrow: 1,
  },
  headerBox: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 16,
    marginBottom: 20,
    alignItems: 'center',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: Platform.OS === 'android' ? 0.25 : 0.1,
    shadowRadius: 6,
  },
  profileContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  profileName: {
    fontSize: 18,
    fontWeight: '600',
  },
  profileEmail: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#ccc',
    marginLeft: 12,
  },
  loginButton: {
    backgroundColor: '#007bff',
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 30,  // 🔥 Oval yapı
  },
  loginText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
  section: {
    marginBottom: 32,
  },
  cardItem: {
    backgroundColor: '#fff',
    borderRadius: 14,
    paddingVertical: 18,
    paddingHorizontal: 16,
    marginBottom: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: Platform.OS === 'android' ? 0.2 : 0.1,
    shadowRadius: 3,
  },
  itemText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  logoutButton: {
    backgroundColor: '#ff4d4d',
    paddingVertical: 14,
    borderRadius: 30,
    alignItems: 'center',
  },
  logoutText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
});
