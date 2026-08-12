import { Button, ButtonIcon } from "@/components/ui/button";
import { GluestackUIProvider } from "@/components/ui/gluestack-ui-provider";
import { Heading } from "@/components/ui/heading";
import { CloseIcon, Icon, SettingsIcon, ArrowLeftIcon, InfoIcon } from "@/components/ui/icon";
import { Switch } from "react-native";
import { Text } from "@/components/ui/text";
import { Stack, useRouter } from "expo-router";
import { useState, useEffect } from "react";
import { useFonts, Montserrat_400Regular, Montserrat_700Bold } from "@expo-google-fonts/montserrat";
import { Appearance, StyleSheet, TouchableOpacity, View, useColorScheme } from "react-native";
import * as SplashScreen from "expo-splash-screen";
import Ionicons from "react-native-vector-icons/Ionicons";
import {
  Drawer,
  DrawerBackdrop,
  DrawerBody,
  DrawerCloseButton,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
} from "@/components/ui/drawer";
import "@/global.css";

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const [showDrawer, setShowDrawer] = useState(false);
  const [fontsLoaded] = useFonts({
    Montserrat_400Regular,
    Montserrat_700Bold,
  });
  const colorScheme = useColorScheme();
  const isDark = colorScheme === 'dark';
  const router = useRouter();

  useEffect(() => {
    if (fontsLoaded) {
      SplashScreen.hideAsync();
    }
  }, [fontsLoaded]);

  if (!fontsLoaded) return null;

  const themeTextStyle = isDark ? styles.darkText : styles.lightText;

  const toggleTheme = (newValue: boolean) => {
    Appearance.setColorScheme(newValue ? 'dark' : 'light');
  }

  return (
    <GluestackUIProvider>
      <Stack
        screenOptions={{
          headerStyle: {
            backgroundColor: "#004ba1",
          },
          headerTintColor: "#fff",
          headerTitleStyle: {
            fontFamily: "Montserrat_700Bold",
            fontSize: 25,
          },
          headerTitleAlign: "center",
          headerLeft: () => (
            <Button
              size="sm"
              onPress={() => {
                router.back();
              }}
              style={{ backgroundColor: "transparent", gap: 6 }}
            >
              <ButtonIcon as={ArrowLeftIcon} style={{ color: "#fff", width: 25, height: 25, marginBottom: 4 }} />
            </Button>
          ),
          headerRight: () => (
            <Button
              size="sm"
              onPress={() => {
                setShowDrawer(true);
              }}
              style={{ backgroundColor: "transparent" }}
            >
              <ButtonIcon as={SettingsIcon} style={{ color: "#fff", width: 25, height: 25, marginBottom: 7 }} />
            </Button>
          ),
        }}
      >
        <Stack.Screen
          name="index"
          options={{
            title: "Home",
            headerLeft: () => (
              <Button
                size="sm"
                onPress={() => router.push("/info")}
                style={{ backgroundColor: "transparent" }}
              >
                <ButtonIcon as={InfoIcon} style={{ color: "#fff", width: 27, height: 27, marginBottom: 4 }} />
              </Button>
            ),
          }}
        />
        <Stack.Screen 
          name="generate-team"
          options={{
            title: "Generate"
          }}
        />
        <Stack.Screen
          name="analyze-team"
          options={{
            title: "Analyze",
          }}
        />
        <Stack.Screen
          name="view-teams"
          options={{
            title: "View Teams",
          }}
        />
        <Stack.Screen
          name="modes"
          options={{
            title: "Modes",
          }}
        />
        <Stack.Screen
          name="simulate-game"
          options={{
            title: "Simulate Game",
          }}
        />
        <Stack.Screen
          name="optimize-team"
          options={{
            title: "Optimal Team",
          }}
        />
        <Stack.Screen
          name="info"
          options={{
            title: "About",
          }}
        />
        <Stack.Screen
          name="app-icon"
          options={{
            title: "App Icon",
          }}
        />
        <Stack.Screen
          name="support"
          options={{
            title: "Support",
          }}
        />
        <Stack.Screen
          name="donate"
          options={{
            title: "Donate",
          }}
        />
        <Stack.Screen
          name="terms"
          options={{
            title: "Terms & Conditions",
          }}
        />
        <Stack.Screen
          name="privacy"
          options={{
            title: "Privacy Policy",
          }}
        />
      </Stack>
      <Drawer
        isOpen={showDrawer}
        size="md"
        anchor="left"
        onClose={() => {
          setShowDrawer(false);
        }}
      >
        <DrawerBackdrop />
        <DrawerContent>
          <DrawerHeader style={{ marginTop: 50 }}>
            <Heading size="xl" style={[styles.lightText, themeTextStyle]}>Settings</Heading>
            <DrawerCloseButton>
              <Icon as={CloseIcon} />
            </DrawerCloseButton>
          </DrawerHeader>
          <DrawerBody style={{ marginTop: 30 }}>
            <View style={{ flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 12 }}>
              <Text style={{ fontFamily: "Montserrat_700Bold" }} size="md">Dark Mode</Text>
              <Switch
                trackColor={{ false: "#ccc", true: "#3b82f6" }}
                thumbColor="#fff"
                onValueChange={toggleTheme}
                value={isDark}
              />
            </View>

            <View style={[styles.divider, { backgroundColor: isDark ? "#edf5ff" : "#02080f", marginTop: 28 }]} />
            <TouchableOpacity style={styles.supportRow} onPress={() => { setShowDrawer(false); router.push("/app-icon"); }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                <Text style={styles.supportLink}>App Icon</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color="#0099ff" />
            </TouchableOpacity>
            <View style={[styles.divider, { backgroundColor: isDark ? "#edf5ff" : "#02080f" }]} />
            <TouchableOpacity style={styles.supportRow} onPress={() => { setShowDrawer(false); router.push("/support"); }}>
              <Text style={styles.supportLink}>Support</Text>
              <Ionicons name="chevron-forward" size={16} color="#0099ff" />
            </TouchableOpacity>
            <View style={[styles.divider, { backgroundColor: isDark ? "#edf5ff" : "#02080f" }]} />
            <TouchableOpacity style={styles.supportRow} onPress={() => { setShowDrawer(false); router.push("/donate"); }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                <Ionicons name="heart" size={16} color="#f43f5e" />
                <Text style={styles.donateLink}>Donate</Text>
              </View>
              <Ionicons name="chevron-forward" size={16} color="#f43f5e" />
            </TouchableOpacity>
            
            <Text style={[styles.legalLabel, { color: isDark ? "#edf5ff" : "#02080f" }]}>LEGAL</Text>

            <TouchableOpacity style={styles.legalRow} onPress={() => { setShowDrawer(false); router.push("/terms"); }}>
              <Text style={styles.legalLink}>Terms & Conditions</Text>
              <Ionicons name="chevron-forward" size={16} color="#0099ff" />
            </TouchableOpacity>
            <View style={[styles.divider, { backgroundColor: isDark ? "#edf5ff" : "#02080f" }]} />
            <TouchableOpacity style={styles.legalRow} onPress={() => { setShowDrawer(false); router.push("/privacy"); }}>
              <Text style={styles.legalLink}>Privacy Policy</Text>
              <Ionicons name="chevron-forward" size={16} color="#0099ff" />
            </TouchableOpacity>
          </DrawerBody>
          <DrawerFooter>
            <Text style={[styles.copyright, { color: isDark ? "#edf5ff" : "#02080f" }]}>
              © {new Date().getFullYear()} Pro Football RTGA. All rights reserved.
            </Text>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>
    </GluestackUIProvider>
  );
}

const styles = StyleSheet.create({
  lightText: {
    color: "#02080f",
    fontFamily: "Montserrat_400Regular",
  },
  darkText: {
    color: "#edf5ff",
    fontFamily: "Montserrat_400Regular",
  },
  divider: {
    height: 1,
    opacity: 0.2,
  },
  legalLabel: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 12,
    opacity: 0.5,
    marginTop: 16,
    marginBottom: 4,
    letterSpacing: 1,
  },
  supportRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 16,
  },
  supportLink: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 16,
    color: "#0099ff",
  },
  donateLink: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 16,
    color: "#f43f5e",
  },
  legalRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 16,
  },
  legalLink: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
    color: "#0099ff",
  },
  copyright: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 12,
    opacity: 0.45,
    textAlign: "center",
    paddingTop: 12,
    paddingBottom: 8,
  },
});



