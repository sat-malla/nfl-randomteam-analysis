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
  const themeTableStyle =
    colorScheme === "light" ? styles.lightTable : styles.darkTable;
  const themeFormStyle =
    colorScheme === "light" ? styles.lightForm : styles.darkForm;
  const themeInputTextStyle =
    colorScheme === "light" ? styles.lightInputText : styles.darkInputText;
  const themeButtonStyle =
    colorScheme === "light" ? styles.lightButton : styles.darkButton;
  const themeButtonTextStyle =
    colorScheme === "light" ? styles.lightButtonText : styles.darkButtonText;
  
  const handleGenerateTeam = async () => {
    const players = [
      { position: "QB", name: "Brock Purdy", nfl_team: "San Francisco 49ers" },
      { position: "WR", name: "Puka Nakua", nfl_team: "Los Angeles Rams" },
    ];

    const teamData = {
      team_name: formData.teamName,
      defense_type: formData.defenseType,
      players: players,
    };

    try {
      const response = await fetch("http://localhost:8000/api/team", {
        method: "POST",
        headers: { "Content-Type": "application/json"},
        body: JSON.stringify(teamData),
      });
      const result = await response.json();
      console.log(result);
      setGenerateTeam(true);
    } catch (error) {
      console.error(error);
    }
  }

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
      <View style={[styles.formContainer, themeFormStyle]}>
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
                style={themeInputTextStyle}
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
          style={[isFormFilled ? styles.disabledButton : themeButtonStyle]}
          disabled={isFormFilled}
          onPress={handleGenerateTeam}
        >
          <Text style={isFormFilled ? styles.lightButtonText : themeButtonTextStyle}>Generate Team</Text>
        </TouchableOpacity>
      </View>
      { generateTeam && (
        <Text style={[themeTextStyle, {marginTop: 20, textAlign: "center" }]}>Team Generated and Saved!</Text>
      )}
      {generateTeam && (
        <Box style={themeTableStyle}>
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
                <TableData>QB</TableData>
                <TableData>Brock Purdy</TableData>
                <TableData>San Francisco 49ers</TableData>
              </TableRow>
              <TableRow>
                <TableData>WR</TableData>
                <TableData>Puka Nakua</TableData>
                <TableData>Los Angeles Rams</TableData>
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
    padding: 15,
    marginTop: 20,
    width: "90%",
    borderWidth: 1,
    borderRadius: 10,
  },
  lightForm: {
    borderColor: "#02080f",
    borderWidth: 1,
    borderRadius: 10,
  },
  darkForm: {
    borderColor: "#edf5ff",
    borderWidth: 1,
    borderRadius: 10,
  },
  lightTable: {
    width: "95%",
    marginTop: 20,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#02080f",
    overflow: "hidden",
  },
  darkTable: {
    width: "95%",
    marginTop: 20,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#edf5ff",
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
  lightInputText: {
    color: "#02080f",
    width: "100%",
  },
  darkInputText: {
    color: "#edf5ff",
    width: "100%",
  },
  lightButton: {
    backgroundColor: "#02080f",
    padding: 10,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  darkButton: {
    backgroundColor: "#edf5ff",
    padding: 10,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  disabledButton: {
    backgroundColor: "#d4d4d4",
    padding: 10,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  lightButtonText: {
    color: "#edf5ff",
  },
  darkButtonText: {
    color: "#02080f",
  }
});

export default GenerateTeam;
