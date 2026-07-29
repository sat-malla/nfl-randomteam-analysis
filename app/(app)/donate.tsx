import { useState } from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  useColorScheme,
  Linking,
  ActivityIndicator,
  Alert,
} from "react-native";
import { useRouter } from "expo-router";
import Ionicons from "react-native-vector-icons/Ionicons";
import FontAwesome5 from "react-native-vector-icons/FontAwesome5";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";
const PRESET_AMOUNTS = [1, 3, 5, 10];

const USES = [
  {
    icon: "server-outline" as const,
    text: "Keep the backend servers running 24/7",
  },
  {
    icon: "flask-outline" as const,
    text: "Compute power to train better ML models on more NFL data",
  },
  {
    icon: "game-controller-outline" as const,
    text: "Build new game modes and features",
  },
  {
    icon: "trending-up-outline" as const,
    text: "Scale the app to handle more users",
  },
  {
    icon: "construct-outline" as const,
    text: "Improve simulation and analysis accuracy over time",
  },
];

export default function Donate() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";
  const router = useRouter();
  const [customAmount, setCustomAmount] = useState("");
  const [selectedPreset, setSelectedPreset] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  const trimmed = customAmount.trim();
  const customError =
    trimmed === ""
      ? null
      : !/^\d+(\.\d{1,2})?$/.test(trimmed)
        ? "Please enter a valid amount (e.g. 2.50)."
        : parseFloat(trimmed) < 0.5
          ? "Minimum donation is $0.50."
          : null;
  const isCustomValid = trimmed !== "" && customError === null;
  const canDonate = selectedPreset !== null || isCustomValid;

  const handleDonate = async () => {
    let dollars: number;
    if (selectedPreset !== null) {
      dollars = selectedPreset;
    } else {
      const trimmed = customAmount.trim();
      const parsed = parseFloat(trimmed);
      if (!trimmed || isNaN(parsed) || !/^\d+(\.\d{1,2})?$/.test(trimmed)) {
        Alert.alert(
          "Invalid Amount",
          "Please enter a valid dollar amount (e.g. 2.50).",
        );
        return;
      }
      dollars = parsed;
    }
    if (dollars < 0.5) {
      Alert.alert(
        "Invalid Amount",
        "Please enter at least $0.50 to make a considerable donation. Thanks!",
      );
      return;
    }
    setLoading(true);
    try {
      const resp = await fetch(`${API_URL}/api/donate/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount_cents: Math.round(dollars * 100) }),
      });
      const data = await resp.json();
      if (data.url) {
        Linking.openURL(data.url);
      } else {
        Alert.alert("Error", "Could not create checkout session.");
      }
    } catch {
      Alert.alert("Error", "Failed to connect to server.");
    } finally {
      setLoading(false);
    }
  };

  const c = {
    bg: isDark ? "#132130" : "#edf5ff",
    card: isDark ? "#02080f" : "#ffffff",
    text: isDark ? "#edf5ff" : "#02080f",
    subtext: isDark ? "#a0b4c8" : "#4a5568",
    border: isDark ? "#1e3a52" : "#bfdbfe",
    shadow: isDark
      ? "rgba(250,250,250,0.8) 0px 3px 8px"
      : "rgba(0,0,0,0.24) 0px 3px 8px",
    inputBg: isDark ? "#0d1f2d" : "#f0f7ff",
    rose: "#f43f5e",
    roseDim: isDark ? "#2d0a12" : "#fff1f2",
    roseBorder: isDark ? "#7f1d1d" : "#fecdd3",
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: c.bg }}
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator={false}
    >
      <View
        style={[
          styles.heroCard,
          { backgroundColor: c.roseDim, borderColor: c.roseBorder },
        ]}
      >
        <Ionicons name="heart" size={36} color={c.rose} />
        <Text style={[styles.heroTitle, { color: c.rose }]}>
          Support NFL RTGA
        </Text>
        <Text style={[styles.heroBody, { color: c.subtext }]}>
          NFL RTGA is just a solo passion project! No company, no funding, no
          subscriptions. An app build with entirely free services with rate
          limits. If you had fun simulating games or building rosters, any
          contribution would be much appreciated to improve the quality of the
          app and services provided for you guys. Ultimately, these donations
          will be for you.
        </Text>
      </View>

      <View
        style={[
          styles.card,
          {
            backgroundColor: c.card,
            borderColor: c.border,
            boxShadow: c.shadow,
          },
        ]}
      >
        <View style={styles.cardHeader}>
          <Text style={[styles.cardTitle, { color: c.text }]}>
            Where it goes
          </Text>
        </View>
        {USES.map((item, i) => (
          <View key={i} style={styles.useRow}>
            <View
              style={[
                styles.useIconWrap,
                { backgroundColor: c.inputBg, borderColor: c.border },
              ]}
            >
              <Ionicons name={item.icon} size={16} color={c.rose} />
            </View>
            <Text style={[styles.useText, { color: c.subtext }]}>
              {item.text}
            </Text>
          </View>
        ))}
      </View>

      <View
        style={[
          styles.card,
          {
            backgroundColor: c.card,
            borderColor: c.border,
            boxShadow: c.shadow,
          },
        ]}
      >
        <View style={styles.cardHeader}>
          <Text style={[styles.cardTitle, { color: c.text }]}>
            Donate via Stripe
          </Text>
        </View>
        <Text style={[styles.platformHint, { color: c.subtext }]}>
          Any amount, even $0.50, helps a lot. Secure checkout powered by
          Stripe. And no, don't worry, it's not a scam. Minimum donation is
          $0.50.
        </Text>
        <View style={styles.presetRow}>
          {PRESET_AMOUNTS.map((amt) => (
            <TouchableOpacity
              key={amt}
              style={[
                styles.presetBtn,
                {
                  backgroundColor:
                    selectedPreset === amt ? "#635BFF" : c.inputBg,
                  borderColor: selectedPreset === amt ? "#635BFF" : c.border,
                },
              ]}
              onPress={() => {
                setSelectedPreset(amt);
                setCustomAmount("");
              }}
              activeOpacity={0.75}
            >
              <Text
                style={[
                  styles.presetBtnText,
                  { color: selectedPreset === amt ? "#ffffff" : c.text },
                ]}
              >
                ${amt}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.customRow}>
          <Text style={[styles.customLabel, { color: c.subtext }]}>$ </Text>
          <View style={styles.customInputWrapper}>
            <TextInput
              style={[
                styles.customInput,
                {
                  backgroundColor: c.inputBg,
                  borderColor: customError
                    ? "#f43f5e"
                    : isCustomValid
                      ? "#635BFF"
                      : c.border,
                  color: c.text,
                },
              ]}
              placeholder="Custom amount"
              placeholderTextColor={c.subtext}
              keyboardType="decimal-pad"
              value={customAmount}
              onChangeText={(val) => {
                setCustomAmount(val);
                setSelectedPreset(null);
              }}
            />
            {customAmount.length > 0 && (
              <TouchableOpacity
                style={styles.customClearBtn}
                onPress={() => {
                  setCustomAmount("");
                  setSelectedPreset(null);
                }}
              >
                <Ionicons name="close-circle" size={18} color={c.subtext} />
              </TouchableOpacity>
            )}
          </View>
        </View>
        {customError && <Text style={styles.errorText}>{customError}</Text>}

        <TouchableOpacity
          style={[
            styles.donateBtn,
            {
              backgroundColor: "#635BFF",
              opacity: !canDonate || loading ? 0.4 : 1,
            },
          ]}
          onPress={handleDonate}
          activeOpacity={0.85}
          disabled={!canDonate || loading}
        >
          <View style={styles.donateBtnLeft}>
            {loading ? (
              <ActivityIndicator color="#ffffff" size="small" />
            ) : (
              <FontAwesome5 name="stripe-s" size={22} color="#ffffff" />
            )}
            <View>
              <Text style={[styles.donateBtnLabel, { color: "#ffffff" }]}>
                {loading ? "Opening checkout..." : "Donate with Stripe"}
              </Text>
              <Text
                style={[
                  styles.donateBtnHandle,
                  { color: "#ffffff", opacity: 0.75 },
                ]}
              >
                Debit, Credit, or Apple Pay
              </Text>
            </View>
          </View>
          {!loading && (
            <Ionicons name="arrow-forward" size={18} color="#ffffff" />
          )}
        </TouchableOpacity>

        <View style={styles.privacyNote}>
          <Text style={[styles.privacyText, { color: c.subtext }]}>
            *Note: This app never sees or stores your card, bank, Apple Pay, or
            any personal payment information. Please read the{" "}
            <Text style={styles.link} onPress={() => router.push("/terms")}>
              Terms & Conditions
            </Text>{" "}
            and{" "}
            <Text style={styles.link} onPress={() => router.push("/privacy")}>
              Privacy Policy
            </Text>{" "}
            for more details.
          </Text>
        </View>
      </View>

      <View
        style={[
          styles.card,
          {
            backgroundColor: c.card,
            borderColor: c.border,
            boxShadow: c.shadow,
          },
        ]}
      >
        <Text style={[styles.closingText, { color: c.subtext }]}>
          Whether you donate or not, thank you for using the app. It means a lot
          to know that something I built out of love for football, ML, and AI is
          actually being used. Enjoy the game!
        </Text>
      </View>

      <Text style={[styles.footer, { color: c.subtext }]}>
        © {new Date().getFullYear()} NFL RTGA. All rights reserved.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 24,
    paddingBottom: 60,
    gap: 16,
  },
  heroCard: {
    borderRadius: 14,
    borderWidth: 1,
    padding: 22,
    alignItems: "center",
    gap: 10,
  },
  heroTitle: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 22,
    textAlign: "center",
  },
  heroBody: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
    lineHeight: 22,
    textAlign: "center",
  },
  card: {
    borderRadius: 14,
    borderWidth: 1,
    padding: 18,
    gap: 12,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginBottom: 2,
  },
  cardTitle: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 18,
  },
  useRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  useIconWrap: {
    width: 34,
    height: 34,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  useText: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
    flex: 1,
    lineHeight: 20,
  },
  link: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 11,
    color: "#3b82f6",
    textDecorationLine: "underline",
  },
  platformHint: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 13,
    lineHeight: 20,
    marginBottom: 2,
  },
  presetRow: {
    flexDirection: "row",
    gap: 8,
  },
  presetBtn: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 10,
    alignItems: "center",
  },
  presetBtnText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 14,
  },
  customRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  customLabel: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 16,
  },
  customInputWrapper: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
  },
  customInput: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    paddingRight: 36,
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
  },
  customClearBtn: {
    position: "absolute",
    right: 10,
  },
  errorText: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 12,
    color: "#f43f5e",
    marginTop: -4,
  },
  privacyNote: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 6,
    marginTop: 4,
  },
  privacyText: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 11,
    lineHeight: 17,
    flex: 1,
  },
  donateBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  donateBtnLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
  },
  donateBtnLabel: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 15,
  },
  donateBtnHandle: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 12,
    marginTop: 1,
  },
  closingText: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
    lineHeight: 22,
  },
  footer: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 11,
    textAlign: "center",
    opacity: 0.5,
    marginTop: 4,
  },
});
