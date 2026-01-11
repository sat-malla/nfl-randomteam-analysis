import { GluestackUIProvider } from "@/components/ui/gluestack-ui-provider";
import { Slot } from "expo-router";
import { useState } from "react";
import { Appearance, StyleSheet, useColorScheme } from "react-native";

import "@/global.css";

export default function RootLayout() {
  const [showDrawer, setShowDrawer] = useState(false);
  const [theme, setTheme] = useState(false);

  const colorScheme = useColorScheme();

  const themeContainerStyle = colorScheme === 'light' ? styles.lightContainer : styles.darkContainer;
  const themeTextStyle = colorScheme === 'light' ? styles.lightText : styles.darkText;

  const toggleTheme = (newValue: boolean) => {
    setTheme(newValue);
    Appearance.setColorScheme(newValue ? 'dark' : 'light');
  }

  return (
    <GluestackUIProvider>
      <Slot />
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



