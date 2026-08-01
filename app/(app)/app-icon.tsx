import { useState, useEffect } from "react";
import {
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  useColorScheme,
  ActivityIndicator,
  Alert,
} from "react-native";

const FOREGROUND = require("../../assets/images/official-PF-RTGA-icon-foreground.png");
let getAppIconName: () => string | null = () => null;
let setAlternateAppIcon: (name: string | null) => Promise<string | null> = async () => null;
let supportsAlternateIcons = false;
try {
  const mod = require("expo-alternate-app-icons");
  getAppIconName = mod.getAppIconName;
  setAlternateAppIcon = mod.setAlternateAppIcon;
  supportsAlternateIcons = mod.supportsAlternateIcons;
} catch {};

const ICONS: { name: string | null; label: string; color: string; position: string }[] = [
  { name: null, label: "Default (Blue)", color: "#1f55ed", position: "RB" },
  { name: "iconRed", label: "Red", color: "#dc2626", position: "QB" },
  { name: "iconGreen", label: "Green", color: "#059669", position: "WR" },
  { name: "iconAmber", label: "Amber", color: "#d97706", position: "TE" },
  { name: "iconOrange", label: "Orange", color: "#ea580c", position: "DE" },
  { name: "iconPink", label: "Pink", color: "#db2777", position: "LB" },
  { name: "iconCyan", label: "Cyan", color: "#0891b2", position: "CB" },
  { name: "iconNavy", label: "Navy", color: "#004c75", position: "S" },
  { name: "iconLime", label: "Lime", color: "#1ec95d", position: "K" },
  { name: "iconTeal", label: "Teal", color: "#21ccb2", position: "P" },
  { name: "iconMaroon", label: "Maroon", color: "#4d2325", position: "RS" },
];

export default function AppIcon() {
  const isDark = useColorScheme() === "dark";
  const c = {
    bg: isDark ? "#132130" : "#edf5ff",
    card: isDark ? "#02080f" : "#ffffff",
    text: isDark ? "#edf5ff" : "#02080f",
    subtext: isDark ? "#a0b4c8" : "#4a5568",
    border: isDark ? "#1e3a52" : "#bfdbfe",
    shadow: isDark ? "rgba(250,250,250,0.8) 0px 3px 8px" : "rgba(0,0,0,0.24) 0px 3px 8px",
  };

  const [current, setCurrent] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const active = getAppIconName();
    setCurrent(active);
    setSelected(active);
  }, []);

  const activeIcon = ICONS.find(i => i.name === selected) ?? ICONS[0];
  const hasChanged = selected !== current;

  const handleSave = async () => {
    if (!supportsAlternateIcons) {
      Alert.alert("Not supported", "Alternate app icons are not supported on this device.");
      return;
    }
    setSaving(true);
    try {
      await setAlternateAppIcon(selected);
      setCurrent(selected);
    } catch (e) {
      Alert.alert("Error", "Failed to change app icon. This requires a native build.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: c.bg }}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
        <Text style={[styles.cardLabel, { color: c.subtext }]}>CURRENT ICON</Text>
        <View style={styles.previewCol}>
          <View style={[styles.previewSwatch, { backgroundColor: activeIcon.color }]}>
            <Image source={FOREGROUND} style={styles.previewImg} />
          </View>
          <Text style={[styles.previewName, { color: c.text }]}>{activeIcon.label}</Text>
          <Text style={[styles.previewSub, { color: c.subtext }]}>{activeIcon.position} position color</Text>
        </View>
      </View>


      <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
        <Text style={[styles.cardLabel, { color: c.subtext }]}>Choose an Icon. Colors are based on position badge colors, so choose your favorite position's color if you would like!</Text>
        <View style={styles.grid}>
          {ICONS.map((icon) => {
            const isSelected = selected === icon.name;
            return (
              <TouchableOpacity
                key={icon.label}
                style={[
                  styles.gridItem,
                  {
                    borderColor: isSelected ? icon.color : c.border,
                    borderWidth: isSelected ? 2.5 : 1,
                    backgroundColor: c.bg,
                  },
                ]}
                onPress={() => setSelected(icon.name)}
                activeOpacity={0.75}
              >
                <View style={[styles.swatch, { backgroundColor: icon.color }]}>
                  <Image source={FOREGROUND} style={styles.swatchImg} />
                </View>
                <Text style={[styles.gridLabel, { color: isSelected ? icon.color : c.subtext }]} numberOfLines={1}>
                  {icon.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      <TouchableOpacity
        style={[
          styles.saveBtn,
          { backgroundColor: hasChanged ? activeIcon.color : "#9ca3af", opacity: saving ? 0.7 : 1 },
        ]}
        onPress={handleSave}
        disabled={!hasChanged || saving}
        activeOpacity={0.85}
      >
        {saving ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.saveBtnText}>{hasChanged ? "Save Icon" : "No Changes"}</Text>
        )}
      </TouchableOpacity>

      <Text style={[styles.note, { color: c.subtext }]}>
        *Note: iOS will briefly display a system notification when the icon changes.
      </Text>
      <Text style={[styles.footer, { color: c.subtext }]}>
        © {new Date().getFullYear()} Pro Football RTGA. All rights reserved.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingHorizontal: 16,
    paddingTop: 24,
    paddingBottom: 60,
    gap: 16,
  },
  card: {
    borderRadius: 14,
    borderWidth: 1,
    padding: 18,
    gap: 14,
  },
  cardLabel: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 12,
    opacity: 0.8,
  },
  previewCol: {
    alignItems: "center",
    gap: 12,
  },
  previewSwatch: {
    width: "100%",
    aspectRatio: 1,
    borderRadius: 28,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  previewImg: {
    width: "85%",
    height: "85%",
    resizeMode: "contain",
  },
  previewName: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 20,
  },
  previewSub: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
    marginTop: -4,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  gridItem: {
    width: "28%",
    borderRadius: 12,
    padding: 10,
    alignItems: "center",
    gap: 6,
    position: "relative",
  },
  swatch: {
    width: 52,
    height: 52,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  swatchImg: {
    width: 42,
    height: 42,
    resizeMode: "contain",
  },
  gridLabel: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 11,
  },
  checkDot: {
    position: "absolute",
    top: 6,
    right: 6,
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  saveBtn: {
    padding: 15,
    borderRadius: 12,
    alignItems: "center",
  },
  saveBtnText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 16,
    color: "#fff",
  },
  note: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 12,
    textAlign: "center",
    lineHeight: 18,
    opacity: 0.6,
  },
  footer: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 11,
    textAlign: "center",
    opacity: 0.5,
    marginTop: 4,
  },
});
