import { Button, ButtonIcon } from "@/components/ui/button";
import { GluestackUIProvider } from "@/components/ui/gluestack-ui-provider";
import { Heading } from "@/components/ui/heading";
import { CloseIcon, Icon, SettingsIcon, ArrowLeftIcon, InfoIcon } from "@/components/ui/icon";
import { Switch } from "react-native";
import { Text } from "@/components/ui/text";
import { Stack, useRouter } from "expo-router";
import { useState, useEffect } from "react";
import { useFonts, Montserrat_400Regular, Montserrat_700Bold } from "@expo-google-fonts/montserrat";
import { Appearance, StyleSheet, View, useColorScheme } from "react-native";
import * as SplashScreen from "expo-splash-screen";
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
                onPress={() => {}}
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
              <Text style={{ fontFamily: "Montserrat_700Bold" }} size="lg">Dark Mode</Text>
              <Switch
                trackColor={{ false: "#ccc", true: "#3b82f6" }}
                thumbColor="#fff"
                onValueChange={toggleTheme}
                value={isDark}
              />
            </View>
          </DrawerBody>
          <DrawerFooter />
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
});



