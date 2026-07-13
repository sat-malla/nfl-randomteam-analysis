import { Button, ButtonIcon, ButtonText } from "@/components/ui/button";
import { GluestackUIProvider } from "@/components/ui/gluestack-ui-provider";
import { Heading } from "@/components/ui/heading";
import { CloseIcon, Icon, SettingsIcon, ArrowLeftIcon } from "@/components/ui/icon";
import { Switch } from "@/components/ui/switch";
import { Text } from "@/components/ui/text";
import { Stack, useRouter } from "expo-router";
import { useState } from "react";
import { Appearance, StyleSheet, View, useColorScheme } from "react-native";

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

export default function RootLayout() {
  const [showDrawer, setShowDrawer] = useState(false);
  const [theme, setTheme] = useState(false);

  const colorScheme = useColorScheme();

  const router = useRouter();

  const themeTextStyle = colorScheme === 'light' ? styles.lightText : styles.darkText;

  const toggleTheme = (newValue: boolean) => {
    setTheme(newValue);
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
            fontWeight: "bold",
            fontSize: 25,
          },
          headerTitleAlign: "center",
          headerLeft: () => (
            <Button
              size="sm"
              onPress={() => {
                router.back();
              }}
              style={{ backgroundColor: "transparent" }}
            >
              <ButtonIcon as={ArrowLeftIcon} style={{ color: "#fff" }} size="xl" />
              <Text style={{ color: "#fff", fontWeight: "700" }}>Back</Text>
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
              <View style={{ width: 49 }} />
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
              <Text style={{ fontWeight: "bold" }} size="lg" >Dark Mode</Text>
              <Switch
                size="md"
                trackColor={{ false: "#d4d4d4", true: "#525252" }}
                thumbColor="#fafafa"
                ios_backgroundColor="#d4d4d4"
                onValueChange={toggleTheme}
                value={theme}
              />
            </View>
          </DrawerBody>
          <DrawerFooter>
            <Button
              variant="outline"
              onPress={() => {
                setShowDrawer(false);
              }}
            >
              <ButtonText>Cancel</ButtonText>
            </Button>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>
    </GluestackUIProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1
  },
  text: {
    fontSize: 29,
    fontWeight: "bold",
    marginTop: 40,
  },
  lightContainer: {
    backgroundColor: '#edf5ff'
  },
  darkContainer: {
    backgroundColor: "#132130"
  },
  lightText: {
    color: "#02080f"
  },
  darkText: {
    color: "#edf5ff"
  }
});



