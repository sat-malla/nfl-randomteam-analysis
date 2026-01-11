import { Box } from "@/components/ui/box";
import {
  FormControl,
  FormControlLabel,
  FormControlLabelText,
} from "@/components/ui/form-control";
import { Heading } from "@/components/ui/heading";
import { ChevronDownIcon } from "@/components/ui/icon";
import { Input, InputField } from "@/components/ui/input";
import {
  Select,
  SelectBackdrop,
  SelectContent,
  SelectDragIndicator,
  SelectDragIndicatorWrapper,
  SelectIcon,
  SelectInput,
  SelectItem,
  SelectPortal,
  SelectTrigger,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableData,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { VStack } from "@/components/ui/vstack";
import { useState } from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  useColorScheme,
  View,
} from "react-native";

const GenerateTeam = () => {
  const [formData, setFormData] = useState({
    teamName: "",
    defenseType: "",
  });
  const [generateTeam, setGenerateTeam] = useState(false);
  const colorScheme = useColorScheme();

  const isFormFilled = !formData.teamName || !formData.defenseType;

  const themeContainerStyle =
    colorScheme === "light" ? styles.lightContainer : styles.darkContainer;
  const themeTextStyle =
    colorScheme === "light" ? styles.lightText : styles.darkText;

  return (
    <ScrollView
      style={[styles.container, themeContainerStyle]}
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator={true}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={[styles.text, themeTextStyle]}>Generate a New NFL Team</Text>
      <Text style={[styles.subText, themeTextStyle]}>
        Generate a new NFL randomly-generated team picking across all 32 NFL
        Teams and various positions.
      </Text>
      <Text style={[styles.subText, themeTextStyle]}>
        Choose your preferences below to generate your team!
      </Text>
      <View style={styles.formContainer}>
        <FormControl size="lg">
          <VStack space="md">
            <Heading size="lg">Team Preferences</Heading>
            <FormControlLabel style={{ marginTop: 15 }}>
              <FormControlLabelText>Team Name</FormControlLabelText>
            </FormControlLabel>
            <Input size="lg">
              <InputField
                type="text"
                placeholder="Team Name"
                value={formData.teamName}
                style={styles.inputField}
                onChangeText={(text) =>
                  setFormData({ ...formData, teamName: text })
                }
              />
            </Input>
            <FormControlLabel style={{ marginTop: 15 }}>
              <FormControlLabelText>Type of Defense</FormControlLabelText>
            </FormControlLabel>
            <Select
              onValueChange={(value) =>
                setFormData({ ...formData, defenseType: value })
              }
            >
              <SelectTrigger
                variant="outline"
                size="lg"
                style={{
                  flexDirection: "row",
                  justifyContent: "space-between",
                }}
              >
                <SelectInput placeholder="Select option" style={{ flex: 1 }} />
                <SelectIcon style={{ marginRight: 10 }} as={ChevronDownIcon} />
              </SelectTrigger>
              <SelectPortal>
                <SelectBackdrop />
                <SelectContent>
                  <SelectDragIndicatorWrapper>
                    <SelectDragIndicator />
                  </SelectDragIndicatorWrapper>
                  <SelectItem
                    label="4-3 Base Defense"
                    value="4-3 Base Defense"
                  />
                  <SelectItem
                    label="3-4 Base Defense"
                    value="3-4 Base Defense"
                  />
                </SelectContent>
              </SelectPortal>
            </Select>
          </VStack>
        </FormControl>
        <TouchableOpacity
          style={[styles.button, isFormFilled && styles.disabledButton]}
          disabled={isFormFilled}
          onPress={() => setGenerateTeam(true)}
        >
          <Text style={styles.buttonText}>Generate Team</Text>
        </TouchableOpacity>
      </View>
      {generateTeam && (
        <Box style={styles.tableContainer}>
          <Table style={{ width: "100%" }}>
            <TableHeader>
              <TableRow>
                <TableHead>Position</TableHead>
                <TableHead>Player Name</TableHead>
                <TableHead>NFL Team</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableData>Rajesh Kumar</TableData>
                <TableData>10</TableData>
                <TableData>$130</TableData>
              </TableRow>
              <TableRow>
                <TableData>Priya Sharma</TableData>
                <TableData>12</TableData>
                <TableData>$210</TableData>
              </TableRow>
            </TableBody>
          </Table>
        </Box>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    alignItems: "center",
    paddingHorizontal: 5,
    paddingBottom: 40,
  },
  text: {
    fontSize: 29,
    fontWeight: "bold",
    marginTop: 40,
  },
  subText: {
    fontSize: 16,
    marginTop: 10,
    textAlign: "center",
  },
  formContainer: {
    flexDirection: "column",
    gap: 12,
    borderWidth: 1,
    borderColor: "#02080f",
    borderRadius: 10,
    padding: 15,
    marginTop: 20,
    width: "90%",
  },
  tableContainer: {
    width: "95%",
    marginTop: 20,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#02080f",
    overflow: "hidden",
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
  inputField: {
    color: "#02080f",
    width: "100%",
  },
  button: {
    backgroundColor: "#02080f",
    padding: 10,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  disabledButton: {
    backgroundColor: "#d4d4d4",
  },
  buttonText: {
    color: "#edf5ff",
  },
});

export default GenerateTeam;
