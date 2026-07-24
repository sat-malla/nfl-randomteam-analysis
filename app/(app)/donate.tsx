import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  useColorScheme,
  Linking,
} from "react-native";
import Ionicons from "react-native-vector-icons/Ionicons";
import FontAwesome5 from "react-native-vector-icons/FontAwesome5";

// Replace with your Stripe payment link once created at dashboard.stripe.com/payment-links
const STRIPE_URL = "https://buy.stripe.com/your_payment_link";

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
          Any amount, even $1, helps a lot. Secure checkout powered by Stripe. And no, don't worry, it's not a scam. 
        </Text>
        <TouchableOpacity
          style={[styles.donateBtn, { backgroundColor: "#635BFF" }]}
          onPress={() => Linking.openURL(STRIPE_URL)}
          activeOpacity={0.85}
        >
          <View style={styles.donateBtnLeft}>
            <FontAwesome5 name="stripe-s" size={22} color="#ffffff" />
            <View>
              <Text style={[styles.donateBtnLabel, { color: "#ffffff" }]}>Donate with Stripe</Text>
              <Text style={[styles.donateBtnHandle, { color: "#ffffff", opacity: 0.75 }]}>
                Debit, credit, or Apple Pay
              </Text>
            </View>
          </View>
          <Ionicons name="arrow-forward" size={18} color="#ffffff" />
        </TouchableOpacity>
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
  platformHint: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 13,
    lineHeight: 20,
    marginBottom: 2,
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
