import {
  Text,
  ScrollView,
  TouchableOpacity,
  View,
  Platform,
} from "react-native";
import { useColorScheme } from "react-native";
import { StyleSheet } from "react-native";
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
  FormControl,
  FormControlLabel,
  FormControlLabelText,
} from "@/components/ui/form-control";
import { Heading } from "@/components/ui/heading";
import { ChevronDownIcon } from "@/components/ui/icon";
import { Input, InputField } from "@/components/ui/input";
import { VStack } from "@/components/ui/vstack";
import { useState, useEffect } from "react";
import * as Application from "expo-application";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

const AnalyzeTeam = () => {
  const colorScheme = useColorScheme();
  const [teams, setTeams] = useState<{ id: number; team_name: string }[]>([]);

  const getDeviceUuid = async () => {
    let deviceUuid = "test-device-uuid";
    if (Platform.OS === "android") {
      deviceUuid = Application.getAndroidId() || "test-device-uuid";
    } else if (Platform.OS === "ios") {
      deviceUuid =
        (await Application.getIosIdForVendorAsync()) || "test-device-uuid";
    }
    return deviceUuid;
  };

  useEffect(() => {
    const fetchTeams = async () => {
      const deviceUuid = await getDeviceUuid();
      fetch(`${API_URL}/api/team/device/${deviceUuid}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      })
        .then((response) => response.json())
        .then((result) => {
          if (result.status === "Success" && result.data) {
            const teamNames = result.data.map(
              (team: { id: number; team_name: string }) => ({
                id: team.id,
                team_name: team.team_name,
              }),
            );
            setTeams(teamNames);
            console.log(teamNames);
          } else {
            console.log("No data found");
          }
        })
        .catch((error) => {
          console.log(error);
        });
    };
    fetchTeams();
  }, []);

  const [formData, setFormData] = useState({
    teamChosen: "",
  });

  const [analyzeTeam, setAnalyzeTeam] = useState(false);
  const [loading, setLoading] = useState(false);
  const [savedAnalysis, setSavedAnalysis] = useState(false);

  const isFormFilled = !formData.teamChosen;

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
  const themeGenerateButtonStyle =
    colorScheme === "light"
      ? styles.lightGenerateButton
      : styles.darkGenerateButton;
  const themeGenerateButtonTextStyle =
    colorScheme === "light" ? styles.lightButtonText : styles.darkButtonText;
  const themeSaveButtonStyle =
    colorScheme === "light" ? styles.lightSaveButton : styles.darkSaveButton;
  const themeSaveButtonTextStyle =
    colorScheme === "light"
      ? styles.lightSaveButtonText
      : styles.darkSaveButtonText;

  return (
    <ScrollView
      style={[styles.container, themeContainerStyle]}
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator={true}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={[styles.text, themeTextStyle]}>Analyze Your Team</Text>
      <Text style={[styles.subText, themeTextStyle]}>
        Analyze any of your generated teams' performance and statistics,
        including win rate, team and player performance, and more!
      </Text>
      <Text style={[styles.subText, themeTextStyle]}>
        Choose your team below to analyze.
      </Text>
      <View style={[styles.formContainer, themeFormStyle]}>
        <FormControl size="lg">
          <VStack space="md">
            <FormControlLabel style={{ marginTop: 15 }}>
              <FormControlLabelText>Choose Team</FormControlLabelText>
            </FormControlLabel>
            <Select
              onValueChange={(value) =>
                setFormData({ ...formData, teamChosen: value })
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
                  {teams.map((team) => (
                    <SelectItem
                      key={team.id}
                      label={team.team_name}
                      value={team.team_name}
                    />
                  ))}
                </SelectContent>
              </SelectPortal>
            </Select>
          </VStack>
        </FormControl>
        <TouchableOpacity
          style={[themeGenerateButtonStyle]} // {[styles.disabledGenerateButton : themeGenerateButtonStyle]}
          // disabled={isFormFilled}
          // onPress={handleGenerateTeam}
        >
          <Text style={themeGenerateButtonTextStyle}>Analyze Team</Text>
          {/* style={styles.lightButtonText : themeGenerateButtonTextStyle} */}
        </TouchableOpacity>
        {/* { generateTeam && (
          <TouchableOpacity
            style={savedTeam ? styles.disabledSaveButton : themeSaveButtonStyle}
            disabled={savedTeam}
            onPress={handleToast}
          >
            {savedTeam ? (
              <Text style={styles.disabledSaveButtonText}>Saved {'\u2713'}</Text>
            ) : (
              <Text style={themeSaveButtonTextStyle}>Save Team</Text>
            )}
          </TouchableOpacity>
        )} */}
      </View>
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
    borderRadius: 10,
  },
  lightForm: {
    backgroundColor: "#edf5ff",
    boxShadow: "rgba(0, 0, 0, 0.24) 0px 3px 8px",
  },
  darkForm: {
    backgroundColor: "#02080f",
    boxShadow: "rgba(250, 250, 250, 0.8) 0px 3px 8px",
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
  lightGenerateButton: {
    backgroundColor: "#02080f",
    padding: 10,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  darkGenerateButton: {
    backgroundColor: "#edf5ff",
    padding: 10,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  disabledGenerateButton: {
    backgroundColor: "#d4d4d4",
    padding: 10,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  lightSaveButton: {
    backgroundColor: "#008a33",
    padding: 10,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  darkSaveButton: {
    backgroundColor: "#34f77c",
    padding: 10,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  disabledSaveButton: {
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
  },
  lightSaveButtonText: {
    color: "#ffffff",
    fontWeight: "bold",
  },
  darkSaveButtonText: {
    color: "#000000",
    fontWeight: "bold",
  },
  disabledSaveButtonText: {
    color: "#ffffff",
    fontWeight: "bold",
  },
});

export default AnalyzeTeam;
