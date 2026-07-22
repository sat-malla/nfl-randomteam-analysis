import { LinearGradient } from "expo-linear-gradient";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  useColorScheme,
  View,
} from "react-native";
import { useRouter } from "expo-router";

const SKEW = "-8deg";

const ModeButtons = [
  { id: 1, title: "Simulate Game", link: "/simulate-game" },
  { id: 2, title: "Optimal Team", link: null },
];

export default function Modes() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";
  const router = useRouter();

  const themeContainerStyle = isDark ? styles.darkContainer : styles.lightContainer;
  const themeTextStyle = isDark ? styles.darkText : styles.lightText;

  return (
    <ScrollView
      style={[styles.scrollView, themeContainerStyle]}
      contentContainerStyle={styles.container}
      showsVerticalScrollIndicator={false}
    >
      <Text style={[styles.title, themeTextStyle]}>Modes</Text>
      <Text style={[styles.subtitle, themeTextStyle]}>
        Select a game mode below to get started!
      </Text>

      <View style={styles.buttonList}>
        {ModeButtons.map((item) => (
          <TouchableOpacity
            key={item.id}
            activeOpacity={item.link ? 0.8 : 0.5}
            style={styles.buttonWrapper}
            onPress={() => item.link && router.push(item.link as any)}
          >
            <View style={styles.borderLayer} />
            <LinearGradient
              colors={["#b0d3ff", "#deedff"]}
              style={styles.button}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
            >
              <Text style={styles.buttonText}>{item.title}</Text>
              <Text style={styles.arrow}>▶</Text>
            </LinearGradient>
          </TouchableOpacity>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scrollView: {
    flex: 1,
  },
  container: {
    alignItems: "center",
    paddingHorizontal: 10,
    paddingBottom: 40,
  },
  lightContainer: {
    backgroundColor: "#edf5ff",
  },
  darkContainer: {
    backgroundColor: "#132130",
  },
  lightText: {
    color: "#02080f",
  },
  darkText: {
    color: "#edf5ff",
  },
  title: {
    fontSize: 28,
    fontFamily: "Montserrat_700Bold",
    marginTop: 40,
    textAlign: "center",
  },
  subtitle: {
    fontSize: 16,
    fontFamily: "Montserrat_400Regular",
    marginTop: 12,
    textAlign: "center",
  },
  buttonList: {
    width: "100%",
    marginTop: 40,
    gap: 20,
    paddingHorizontal: 16,
  },
  buttonWrapper: {
    width: "100%",
    height: 100,
    transform: [{ skewX: SKEW }],
  },
  borderLayer: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderWidth: 4,
    borderColor: "#000",
    borderStyle: "dashed",
    borderRadius: 4,
  },
  button: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 28,
    borderRadius: 4,
  },
  buttonText: {
    transform: [{ skewX: "8deg" }],
    fontSize: 20,
    fontFamily: "Montserrat_700Bold",
    color: "#02080f",
    letterSpacing: 0.5,
  },
  arrow: {
    transform: [{ skewX: "8deg" }],
    fontSize: 18,
    color: "#02080f",
  },
});
