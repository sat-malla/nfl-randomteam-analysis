import {
  FlatList,
  Modal,
  StyleSheet,
  Text,
  TouchableOpacity,
  useColorScheme,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { ChevronDownIcon, CheckIcon, Icon } from "@/components/ui/icon";

type PickerItem = { label: string; value: string };

type Props = {
  visible: boolean;
  onClose: () => void;
  title: string;
  items: PickerItem[];
  selectedValue: string;
  onSelect: (value: string) => void;
};

export default function PickerModal({ visible, onClose, title, items, selectedValue, onSelect }: Props) {
  const isDark = useColorScheme() === "dark";

  const c = {
    bg: isDark ? "#02080f" : "#ffffff",
    text: isDark ? "#edf5ff" : "#02080f",
    subtext: isDark ? "#a0b4c8" : "#4a5568",
    border: isDark ? "#1e3a52" : "#bfdbfe",
    selected: isDark ? "#1e3a52" : "#dbeafe",
    overlay: "rgba(0,0,0,0.45)",
  };

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={[styles.overlay, { backgroundColor: c.overlay }]}>
        <SafeAreaView style={[styles.sheet, { backgroundColor: c.bg }]}>
          <View style={[styles.header, { borderBottomColor: c.border }]}>
            <Text style={[styles.title, { color: c.text }]}>{title}</Text>
            <TouchableOpacity onPress={onClose} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
              <Text style={[styles.done, { color: c.subtext }]}>Done</Text>
            </TouchableOpacity>
          </View>
          <FlatList
            data={items}
            keyExtractor={(item) => item.value}
            renderItem={({ item }) => {
              const isSelected = item.value === selectedValue;
              return (
                <TouchableOpacity
                  style={[styles.item, { borderBottomColor: c.border, backgroundColor: isSelected ? c.selected : "transparent" }]}
                  onPress={() => { onSelect(item.value); onClose(); }}
                >
                  <Text style={[styles.itemText, { color: c.text, fontFamily: isSelected ? "Montserrat_700Bold" : "Montserrat_400Regular" }]}>
                    {item.label}
                  </Text>
                  {isSelected && <Text style={{ color: c.text, fontSize: 16 }}><Icon as={CheckIcon} size="sm" style={{ color: c.text }} /></Text>}
                </TouchableOpacity>
              );
            }}
          />
        </SafeAreaView>
      </View>
    </Modal>
  );
}

export function PickerTrigger({
  value,
  placeholder,
  onPress,
  borderColor,
  textColor,
  placeholderColor,
}: {
  value: string;
  placeholder: string;
  onPress: () => void;
  borderColor: string;
  textColor: string;
  placeholderColor: string;
}) {
  return (
    <TouchableOpacity onPress={onPress} style={[styles.trigger, { borderColor }]}>
      <Text
        numberOfLines={1}
        style={{
          flex: 1,
          fontFamily: "Montserrat_400Regular",
          fontSize: 16,
          color: value ? textColor : placeholderColor,
        }}
      >
        {value || placeholder}
      </Text>
      <Icon as={ChevronDownIcon} size="sm" style={{ color: placeholderColor }} />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
  },
  sheet: {
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    maxHeight: "80%",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
    borderBottomWidth: 1,
  },
  title: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 17,
  },
  done: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 15,
  },
  item: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 0.5,
  },
  itemText: {
    fontSize: 16,
    flex: 1,
  },
  trigger: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    height: 48,
  },
});
