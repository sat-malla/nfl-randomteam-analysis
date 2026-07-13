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
import { Spinner } from '@/components/ui/spinner';
import {
  Table,
  TableBody,
  TableData,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Toast,
  ToastTitle,
  useToast,
} from '@/components/ui/toast';
import { VStack } from "@/components/ui/vstack";
import * as Application from 'expo-application';
import { useState } from "react";
import {
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  useColorScheme,
  View,
} from "react-native";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";


const GenerateTeam = () => {
  const [formData, setFormData] = useState({
    teamName: "",
    offenseType: "",
    defenseType: "",
  });
  const [generateTeam, setGenerateTeam] = useState(false);
  const [loading, setLoading] = useState(false);
  const [savedTeam, setSavedTeam] = useState(false);
  const colorScheme = useColorScheme();

  const isFormFilled = !formData.teamName || !formData.offenseType || !formData.defenseType;

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
    colorScheme === "light" ? styles.lightGenerateButton : styles.darkGenerateButton;
  const themeGenerateButtonTextStyle =
    colorScheme === "light" ? styles.lightButtonText : styles.darkButtonText;
  const themeSaveButtonStyle =
    colorScheme === "light" ? styles.lightSaveButton : styles.darkSaveButton;
  const themeSaveButtonTextStyle =
    colorScheme === "light" ? styles.lightSaveButtonText : styles.darkSaveButtonText;

  const [players, setPlayers] = useState([{ position: "", name: "", nfl_team: "" }]);

  const abbToTeamNames = {
      "ARI": "Arizona Cardinals",
      "ATL": "Atlanta Falcons",
      "BAL": "Baltimore Ravens",
      "BUF": "Buffalo Bills",
      "CAR": "Carolina Panthers",
      "CHI": "Chicago Bears",
      "CIN": "Cincinnati Bengals",
      "CLE": "Cleveland Browns",
      "DAL": "Dallas Cowboys",
      "DEN": "Denver Broncos",
      "DET": "Detroit Lions",
      "GB": "Green Bay Packers",
      "HOU": "Houston Texans",
      "IND": "Indianapolis Colts",
      "JAX": "Jacksonville Jaguars",
      "KC": "Kansas City Chiefs",
      "LAR": "Los Angeles Rams",
      "LAC": "Los Angeles Chargers",
      "LV": "Las Vegas Raiders",
      "MIA": "Miami Dolphins",
      "MIN": "Minnesota Vikings",
      "NE": "New England Patriots",
      "NO": "New Orleans Saints",
      "NYG": "New York Giants",
      "NYJ": "New York Jets",
      "PHI": "Philadelphia Eagles",
      "PIT": "Pittsburgh Steelers",
      "SF": "San Francisco 49ers",
      "SEA": "Seattle Seahawks",
      "TB": "Tampa Bay Buccaneers",
      "TEN": "Tennessee Titans",
      "WAS": "Washington Commanders",
  }

  const toast = useToast();
  const [toastId, setToastId] = useState("");
  const handleToast = () => {
    storePlayers();
    if (!toast.isActive(toastId)) {
      showNewToast();
    }
    setSavedTeam(true);
  };
  const showNewToast = () => {
    const newId = Math.random().toString();
    setToastId(newId);
    toast.show({
      id: newId,
      placement: 'top',
      duration: 3000,
      render: ({ id }) => {
        const uniqueToastId = 'toast-' + id;
        return (
          <Toast nativeID={uniqueToastId} action="success" variant="solid">
            <ToastTitle>Saved!</ToastTitle>
          </Toast>
        );
      },
    });
  };
  
  const handleGenerateTeam = async () => {
    setLoading(true);
    setGenerateTeam(false);
    const players = [];

    const positions = ["QB", "RB", "WR", "TE", "OT", "G", "C", "DE", "DT", "LB", "CB", "FS", "SS", "Nickel", "Dime", "K", "P", "RS", "LS"]

    try {
      if (formData.offenseType === "3 WR 1 TE" && formData.defenseType === "4-3 Base Defense") {
        for (const position of positions) {
          if (position == "RB" || position == "OT" || position == "G" || position == "DE" || position == "DT" || position == "CB") {
            const response = await fetch(`${API_URL}/api/players/random-players?position=${position}&count=2`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              for (const player of result.data) {
                players.push({
                  position: position,
                  name: player.full_name || player.first_name + " " + player.last_name,
                  nfl_team: player.nfl_team
                })
              }
            } else {
              console.log("No data found for position: " + position)
            }
          } else if (position == "WR" || position == "LB") {
            const response = await fetch(`${API_URL}/api/players/random-players?position=${position}&count=3`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              for (const player of result.data) {
                players.push({
                  position: position,
                  name: player.full_name || player.first_name + " " + player.last_name,
                  nfl_team: player.nfl_team
                })
              }
            } else {
              console.log("No data found for position: " + position)
            }
          } else if (position == "Nickel" || position == "Dime") {
            const response = await fetch(`${API_URL}/api/players/one-from-many-positions?positions=CB,SS,DB,S`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              players.push({
                position: position,
                name: result.data.full_name || result.data.first_name + " " + result.data.last_name,
                nfl_team: result.data.nfl_team
              })
            } else {
              console.log("No data found for position: " + position)
            }
          } else if (position == "FS") {
            const response = await fetch(`${API_URL}/api/players/random-player?position=S`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              players.push({
                position: position,
                name: result.data.full_name || result.data.first_name + " " + result.data.last_name,
                nfl_team: result.data.nfl_team
              })
            } else {
              console.log("No data found for position: " + position)
            }
          } else {
            const response = await fetch(`${API_URL}/api/players/random-player?position=${position}`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              players.push({
                position: position,
                name: result.data.full_name || result.data.first_name + " " + result.data.last_name,
                nfl_team: result.data.nfl_team
              })
            } else {
              console.log("No data found for position: " + position)
            }
          }
        }
      } else if (formData.offenseType === "2 WR 2 TE" && formData.defenseType === "4-3 Base Defense") {
        for (const position of positions) {
          if (position == "RB" || position == "WR" || position == "TE" || position == "OT" || position == "G" || position == "DE" || position == "DT" || position == "CB") {
            const response = await fetch(`${API_URL}/api/players/random-players?position=${position}&count=2`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              for (const player of result.data) {
                players.push({
                  position: position,
                  name: player.full_name || player.first_name + " " + player.last_name,
                  nfl_team: player.nfl_team
                })
              }
            } else {
              console.log("No data found for position: " + position)
            }
          } else if (position == "LB") {
            const response = await fetch(`${API_URL}/api/players/random-players?position=${position}&count=3`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              for (const player of result.data) {
                players.push({
                  position: position,
                  name: player.full_name || player.first_name + " " + player.last_name,
                  nfl_team: player.nfl_team
                })
              }
            } else {
              console.log("No data found for position: " + position)
            }
          } else if (position == "Nickel" || position == "Dime") {
            const response = await fetch(`${API_URL}/api/players/one-from-many-positions?positions=CB,SS,DB,S`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              players.push({
                position: position,
                name: result.data.full_name || result.data.first_name + " " + result.data.last_name,
                nfl_team: result.data.nfl_team
              })
            } else {
              console.log("No data found for position: " + position)
            }
          } else if (position == "FS") {
            const response = await fetch(`${API_URL}/api/players/random-player?position=S`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              players.push({
                position: position,
                name: result.data.full_name || result.data.first_name + " " + result.data.last_name,
                nfl_team: result.data.nfl_team
              })
            } else {
              console.log("No data found for position: " + position)
            }
          } else {
            const response = await fetch(`${API_URL}/api/players/random-player?position=${position}`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              players.push({
                position: position,
                name: result.data.full_name || result.data.first_name + " " + result.data.last_name,
                nfl_team: result.data.nfl_team
              })
            } else {
              console.log("No data found for position: " + position)
            }
          }
        }
      } else if (formData.offenseType === "3 WR 1 TE" && formData.defenseType === "3-4 Base Defense") {
         for (const position of positions) {
          if (position == "RB" || position == "OT" || position == "G" || position == "DE" || position == "CB") {
            const response = await fetch(`${API_URL}/api/players/random-players?position=${position}&count=2`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              for (const player of result.data) {
                players.push({
                  position: position,
                  name: player.full_name || player.first_name + " " + player.last_name,
                  nfl_team: player.nfl_team
                })
              }
            } else {
              console.log("No data found for position: " + position)
            }
          } else if (position == "WR") {
            const response = await fetch(`${API_URL}/api/players/random-players?position=WR&count=3`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              for (const player of result.data) {
                players.push({
                  position: position,
                  name: player.full_name || player.first_name + " " + player.last_name,
                  nfl_team: player.nfl_team
                })
              }
            } else {
              console.log("No data found for position: " + position)
            }
          } else if (position == "LB") {
            const response = await fetch(`${API_URL}/api/players/random-players?position=LB&count=4`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              for (const player of result.data) {
                players.push({
                  position: position,
                  name: player.full_name || player.first_name + " " + player.last_name,
                  nfl_team: player.nfl_team
                })
              }
            } else {
              console.log("No data found for position: " + position)
            }
          } else if (position == "Nickel" || position == "Dime") {
            const response = await fetch(`${API_URL}/api/players/one-from-many-positions?positions=CB,SS,DB,S`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              players.push({
                position: position,
                name: result.data.full_name || result.data.first_name + " " + result.data.last_name,
                nfl_team: result.data.nfl_team
              })
            } else {
              console.log("No data found for position: " + position)
            }
          } else if (position == "FS") {
            const response = await fetch(`${API_URL}/api/players/random-player?position=S`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              players.push({
                position: position,
                name: result.data.full_name || result.data.first_name + " " + result.data.last_name,
                nfl_team: result.data.nfl_team
              })
            } else {
              console.log("No data found for position: " + position)
            }
          } else {
            const response = await fetch(`${API_URL}/api/players/random-player?position=${position}`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              players.push({
                position: position,
                name: result.data.full_name || result.data.first_name + " " + result.data.last_name,
                nfl_team: result.data.nfl_team
              })
            } else {
              console.log("No data found for position: " + position)
            }
          }
        }
      } else if (formData.offenseType === "2 WR 2 TE" && formData.defenseType === "3-4 Base Defense") {
        for (const position of positions) {
          if (position == "RB" || position == "WR" || position == "TE" || position == "OT" || position == "G" || position == "DE" || position == "CB") {
            const response = await fetch(`${API_URL}/api/players/random-players?position=${position}&count=2`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              for (const player of result.data) {
                players.push({
                  position: position,
                  name: player.full_name || player.first_name + " " + player.last_name,
                  nfl_team: player.nfl_team
                })
              }
            } else {
              console.log("No data found for position: " + position)
            }
          } else if (position == "LB") {
            const response = await fetch(`${API_URL}/api/players/random-players?position=LB&count=4`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              for (const player of result.data) {
                players.push({
                  position: position,
                  name: player.full_name || player.first_name + " " + player.last_name,
                  nfl_team: player.nfl_team
                })
              }
            } else {
              console.log("No data found for position: " + position)
            }
          } else if (position == "Nickel" || position == "Dime") {
            const response = await fetch(`${API_URL}/api/players/one-from-many-positions?positions=CB,SS,DB,S`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              players.push({
                position: position,
                name: result.data.full_name || result.data.first_name + " " + result.data.last_name,
                nfl_team: result.data.nfl_team
              })
            } else {
              console.log("No data found for position: " + position)
            }
          } else if (position == "FS") {
            const response = await fetch(`${API_URL}/api/players/random-player?position=S`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              players.push({
                position: position,
                name: result.data.full_name || result.data.first_name + " " + result.data.last_name,
                nfl_team: result.data.nfl_team
              })
            } else {
              console.log("No data found for position: " + position)
            }
          } else {
            const response = await fetch(`${API_URL}/api/players/random-player?position=${position}`)
            const result = await response.json()
            if (result.status === "Success" && result.data) {
              players.push({
                position: position,
                name: result.data.full_name || result.data.first_name + " " + result.data.last_name,
                nfl_team: result.data.nfl_team
              })
            } else {
              console.log("No data found for position: " + position)
            }
          }
        }
      }
      setGenerateTeam(true);
      setPlayers(players);
      setSavedTeam(false);
      setLoading(false);
    } catch (error) {
      console.error(error);
      setLoading(false);
    }
  }


  const storePlayers = async () => {
    let deviceUuid = "test-device-uuid";
    if (Platform.OS === "android") {
      deviceUuid = Application.getAndroidId() || "test-device-uuid";
    } else if (Platform.OS === "ios") {
      deviceUuid = await Application.getIosIdForVendorAsync() || "test-device-uuid";
    }

    const teamData = {
      device_uuid: deviceUuid,
      team_name: formData.teamName,
      offense_type: formData.offenseType,
      defense_type: formData.defenseType,
      players: players,
    };

    try {
      const response = await fetch("${API_URL}/api/team", {
        method: "POST",
        headers: { "Content-Type": "application/json"},
        body: JSON.stringify({
          ...teamData,
        }),
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
              <FormControlLabelText>Type of Offense</FormControlLabelText>
            </FormControlLabel>
            <Select
              onValueChange={(value) =>
                setFormData({ ...formData, offenseType: value })
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
                    label="3 WR 1 TE"
                    value="3 WR 1 TE"
                  />
                  <SelectItem
                    label="2 WR 2 TE"
                    value="2 WR 2 TE"
                  />
                </SelectContent>
              </SelectPortal>
            </Select>
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
          style={[isFormFilled ? styles.disabledGenerateButton : themeGenerateButtonStyle]}
          disabled={isFormFilled}
          onPress={handleGenerateTeam}
        >
          <Text style={isFormFilled ? styles.lightButtonText : themeGenerateButtonTextStyle}>Generate Team</Text>
        </TouchableOpacity>
        { generateTeam && (
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
        )}
      </View>
      { generateTeam && (
        <Text style={[themeTextStyle, {marginTop: 20, textAlign: "center" }]}>Team Generated!</Text>
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
              {players.map((player, index) => (
                <TableRow key={index}>
                  <TableData>{player.position}</TableData>
                  <TableData>{player.name}</TableData>
                  <TableData>{abbToTeamNames[player.nfl_team as keyof typeof abbToTeamNames] || player.nfl_team}</TableData>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}
      {loading && (
        <Spinner size="large" color="blue" style={{ marginTop: 20 }} />
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

export default GenerateTeam;
