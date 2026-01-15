import { LinearGradient } from "expo-linear-gradient";
import { Href, useRouter } from "expo-router";
import {
  Dimensions,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  useColorScheme,
  View,
} from "react-native";

const { width } = Dimensions.get("window");
const gap = 16;
const itemWidth = (width - gap * 3) / 2;

export default function Index() {
  const colorScheme = useColorScheme();

  const themeContainerStyle =
    colorScheme === "light" ? styles.lightContainer : styles.darkContainer;
  const themeTextStyle =
    colorScheme === "light" ? styles.lightText : styles.darkText;

  const router = useRouter();

  const GridButtons = [
    {
      id: 1,
      title: "Generate New Team",
      link: "/generate-team",
    },
    {
      id: 2,
      title: "Analyze Team",
      link: "/",
    },
    {
      id: 3,
      title: "How it Works",
      link: "/",
    },
    {
      id: 4,
      title: "About the Creator",
      link: "/",
    },
  ];

  return (
    <View style={[styles.container, themeContainerStyle]}>
      <Text
        style={{
          fontSize: 25,
          fontWeight: "bold",
          marginTop: 40,
          textAlign: "center",
        }}
      >
        Welcome to the NFL Random Team Generator & Analysis
      </Text>
      <Text
        style={{
          fontSize: 20,
          fontWeight: "semibold",
          marginTop: 15,
          textAlign: "center",
        }}
      >
        Click the Options Below to Explore!
      </Text>
      <FlatList
        data={GridButtons}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.button} onPress={() => router.navigate(item.link as Href)}>
            <LinearGradient
              colors={["#b0d3ff", "#deedff"]}
              style={styles.buttonBackground}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
            />
            <Text>{item.title}</Text>
          </TouchableOpacity>
        )}
        numColumns={2}
        style={{ marginTop: 40 }}
        columnWrapperStyle={styles.gridRow}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    paddingHorizontal: 10,
  },
  text: {
    fontSize: 29,
    fontWeight: "bold",
    marginTop: 40,
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
  button: {
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
    paddingTop: 25,
    width: itemWidth,
  },
  buttonBackground: {
    position: "absolute",
    top: 0,
    height: 70,
    width: 150,
    borderRadius: 10,
    justifyContent: "center",
    alignItems: "center",
  },
  gridRow: {
    flex: 1,
    justifyContent: "space-between",
    marginBottom: 30,
  },
});
