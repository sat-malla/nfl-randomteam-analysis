import { LinearGradient } from 'expo-linear-gradient';
import {
  Dimensions,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  useColorScheme,
  View
} from "react-native";

const GridButtons = [
  {
    id: 1,
    title: "Generate",
  },
  {
    id: 2,
    title: "Generate",
  },
  {
    id: 3,
    title: "Generate",
  },
  {
    id: 4,
    title: "Generate",
  },
];

const { width } = Dimensions.get('window')
const gap = 16;
const itemWidth = (width - gap * 3) / 2;

export default function Index() {
  const colorScheme = useColorScheme();

  const themeContainerStyle =
    colorScheme === "light" ? styles.lightContainer : styles.darkContainer;
  const themeTextStyle =
    colorScheme === "light" ? styles.lightText : styles.darkText;

  return (
    <View
      style={[styles.container, themeContainerStyle]}
    >
      <Text
        style={{
          fontSize: 29,
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
          <TouchableOpacity style={styles.button}>
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
       style={{ marginTop: 30 }}
       columnWrapperStyle={styles.gridRow}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
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
    width: itemWidth
  },
  buttonBackground: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
    height: 70,
    width: 150,
    borderRadius: 10,
    justifyContent: "center",
    alignItems: "center",
  },
  gridRow: {
    flex: 1,
    justifyContent: 'space-between',
    marginBottom: 30
  },
});
