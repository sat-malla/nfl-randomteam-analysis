import { LinearGradient } from "expo-linear-gradient";
import { Href, useRouter } from "expo-router";
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  useColorScheme,
  View,
} from "react-native";

export default function Index() {
  const colorScheme = useColorScheme();

  const themeContainerStyle =
    colorScheme === "light" ? styles.lightContainer : styles.darkContainer;
  const themeTextStyle =
    colorScheme === "light" ? styles.lightText : styles.darkText;

  const router = useRouter();

  const GridButtons = [
    { id: 1, title: "Generate New Team", link: "/generate-team" },
    { id: 2, title: "Analyze Team", link: "/analyze-team" },
    { id: 3, title: "How it Works", link: "/" },
    { id: 4, title: "About the Creator", link: "/" },
  ];

  return (
    <View style={[styles.container, themeContainerStyle]}>
      <Text
        style={[
          {
            fontSize: 25,
            fontWeight: "bold",
            marginTop: 40,
            textAlign: "center",
          },
          themeTextStyle,
        ]}
      >
        Welcome to the NFL Random Team Generator & Analysis
      </Text>
      <Text
        style={[
          {
            fontSize: 20,
            fontWeight: "semibold",
            marginTop: 15,
            textAlign: "center",
          },
          themeTextStyle,
        ]}
      >
        Click the Options Below to Explore!
      </Text>

      <View style={styles.buttonList}>
        {GridButtons.map((item) => (
          <TouchableOpacity
            key={item.id}
            onPress={() => router.navigate(item.link as Href)}
            activeOpacity={0.8}
            style={styles.buttonWrapper}
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
    </View>
  );
}

const SKEW = "-8deg";

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    paddingHorizontal: 10,
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
    fontWeight: "bold",
    color: "#02080f",
    letterSpacing: 0.5,
  },
  arrow: {
    transform: [{ skewX: "8deg" }],
    fontSize: 18,
    color: "#02080f",
  },
  text: {
    fontSize: 29,
    fontWeight: "bold",
    marginTop: 40,
  },
  gridRow: {
    flex: 1,
    justifyContent: "space-between",
    marginBottom: 30,
  },
});
