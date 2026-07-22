import { assignLbLabels } from "@/utils/defense-rendering";
import { Box } from "@/components/ui/box";
import {
  FormControl,
  FormControlLabel,
  FormControlLabelText,
} from "@/components/ui/form-control";
import { Heading } from "@/components/ui/heading";
import { Input, InputField } from "@/components/ui/input";
import PickerModal, { PickerTrigger } from "@/components/PickerModal";
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
  const [offensePickerOpen, setOffensePickerOpen] = useState(false);
  const [defensePickerOpen, setDefensePickerOpen] = useState(false);
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
  const [headCoach, setHeadCoach] = useState("");
  const [headCoachTeam, setHeadCoachTeam] = useState("");

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
  
  // Randomly pick `n` items from an array without replacement
  const pickRandom = <T,>(arr: T[], n: number): T[] => {
    const copy = [...arr];
    const result: T[] = [];
    for (let i = 0; i < n && copy.length > 0; i++) {
      const idx = Math.floor(Math.random() * copy.length);
      result.push(copy.splice(idx, 1)[0]);
    }
    return result;
  };

  const handleGenerateTeam = async () => {
    setLoading(true);
    setGenerateTeam(false);
    const players = [];

    const positions = ["QB", "RB", "WR", "TE", "OT", "G", "C", "DE", "DT", "LB", "CB", "FS", "SS", "Nickel", "Dime", "K", "P", "RS", "LS"]

    // Pick 2 random offensive and 2 random defensive positions to guarantee slot=1 (true starters)
    const offPositions = ["QB", "WR", "TE", "OT", "G", "C"];
    const defPositions = ["DE", "DT", "LB", "CB", "FS", "SS"];
    const slot1OffPositions = new Set(pickRandom(offPositions, 2));
    const slot1DefPositions = new Set(pickRandom(defPositions, 2));

    const fetchSlot = (position: string): string => {
      if (slot1OffPositions.has(position) || slot1DefPositions.has(position)) return "&slot=1";
      return "";
    };

    try {
      if (formData.offenseType === "3 WR 1 TE" && formData.defenseType === "4-3 Base Defense") {
        for (const position of positions) {
          if (position == "RB") {
            // RB1 from starters (depth 1), RB2 from backups (depth 2+)
            for (const slot of [1, 2]) {
              const response = await fetch(`${API_URL}/api/players/random-players?position=RB&count=1&slot=${slot}`)
              const result = await response.json()
              if (result.status === "Success" && result.data) {
                const player = result.data[0]
                players.push({ position: "RB", name: player.full_name || player.first_name + " " + player.last_name, nfl_team: player.nfl_team })
              }
            }
          } else if (position == "OT" || position == "G" || position == "DE" || position == "DT" || position == "CB") {
            const response = await fetch(`${API_URL}/api/players/random-players?position=${position}&count=2${fetchSlot(position)}`)
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
            const response = await fetch(`${API_URL}/api/players/random-players?position=${position}&count=3${fetchSlot(position)}`)
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
            const slotParam = fetchSlot(position);
            const response = await fetch(`${API_URL}/api/players/random-player?position=${position}${slotParam}`)
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
          if (position == "RB") {
            for (const slot of [1, 2]) {
              const response = await fetch(`${API_URL}/api/players/random-players?position=RB&count=1&slot=${slot}`)
              const result = await response.json()
              if (result.status === "Success" && result.data) {
                const player = result.data[0]
                players.push({ position: "RB", name: player.full_name || player.first_name + " " + player.last_name, nfl_team: player.nfl_team })
              }
            }
          } else if (position == "WR" || position == "TE" || position == "OT" || position == "G" || position == "DE" || position == "DT" || position == "CB") {
            const response = await fetch(`${API_URL}/api/players/random-players?position=${position}&count=2${fetchSlot(position)}`)
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
            const response = await fetch(`${API_URL}/api/players/random-players?position=${position}&count=3${fetchSlot(position)}`)
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
            const slotParam = fetchSlot(position);
            const response = await fetch(`${API_URL}/api/players/random-player?position=${position}${slotParam}`)
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
          if (position == "RB") {
            for (const slot of [1, 2]) {
              const response = await fetch(`${API_URL}/api/players/random-players?position=RB&count=1&slot=${slot}`)
              const result = await response.json()
              if (result.status === "Success" && result.data) {
                const player = result.data[0]
                players.push({ position: "RB", name: player.full_name || player.first_name + " " + player.last_name, nfl_team: player.nfl_team })
              }
            }
          } else if (position == "OT" || position == "G" || position == "DE" || position == "CB") {
            const response = await fetch(`${API_URL}/api/players/random-players?position=${position}&count=2${fetchSlot(position)}`)
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
            const response = await fetch(`${API_URL}/api/players/random-players?position=WR&count=3${fetchSlot(position)}`)
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
            const response = await fetch(`${API_URL}/api/players/random-players?position=LB&count=4${fetchSlot(position)}`)
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
            const slotParam = fetchSlot(position);
            const response = await fetch(`${API_URL}/api/players/random-player?position=${position}${slotParam}`)
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
          if (position == "RB") {
            for (const slot of [1, 2]) {
              const response = await fetch(`${API_URL}/api/players/random-players?position=RB&count=1&slot=${slot}`)
              const result = await response.json()
              if (result.status === "Success" && result.data) {
                const player = result.data[0]
                players.push({ position: "RB", name: player.full_name || player.first_name + " " + player.last_name, nfl_team: player.nfl_team })
              }
            }
          } else if (position == "WR" || position == "TE" || position == "OT" || position == "G" || position == "DE" || position == "CB") {
            const response = await fetch(`${API_URL}/api/players/random-players?position=${position}&count=2${fetchSlot(position)}`)
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
            const response = await fetch(`${API_URL}/api/players/random-players?position=LB&count=4${fetchSlot(position)}`)
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
            const slotParam = fetchSlot(position);
            const response = await fetch(`${API_URL}/api/players/random-player?position=${position}${slotParam}`)
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
      try {
        const coachRes = await fetch(`${API_URL}/api/coaches/random`);
        const coachResult = await coachRes.json();
        if (coachResult.status === "Success" && coachResult.data) {
          setHeadCoach(coachResult.data.head_coach);
          const teamAbbrev = coachResult.data.team ?? "";
          setHeadCoachTeam(abbToTeamNames[teamAbbrev as keyof typeof abbToTeamNames] ?? teamAbbrev);
        }
      } catch (e) {
        setHeadCoach("");
      }

      setGenerateTeam(true);
      setPlayers(assignLbLabels(players, formData.defenseType));
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
      head_coach: headCoach,
      players: players,
    };

    try {
      const response = await fetch(`${API_URL}/api/team`, {
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
      <Text style={[styles.text, themeTextStyle]}>Generate a New Random NFL Team</Text>
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
              <FormControlLabelText style={{ fontFamily: "Montserrat_400Regular" }}>Team Name</FormControlLabelText>
            </FormControlLabel>
            <Input size="lg">
              <InputField
                type="text"
                placeholder="Team Name"
                value={formData.teamName}
                style={[themeInputTextStyle, { fontFamily: "Montserrat_400Regular" }]}
                onChangeText={(text) =>
                  setFormData({ ...formData, teamName: text })
                }
              />
            </Input>
            <FormControlLabel style={{ marginTop: 15 }}>
              <FormControlLabelText style={{ fontFamily: "Montserrat_400Regular" }}>Type of Offense</FormControlLabelText>
            </FormControlLabel>
            <PickerTrigger
              value={formData.offenseType}
              placeholder="Select option"
              onPress={() => setOffensePickerOpen(true)}
              borderColor={colorScheme === "dark" ? "#1e3a52" : "#bfdbfe"}
              textColor={colorScheme === "dark" ? "#edf5ff" : "#02080f"}
              placeholderColor={colorScheme === "dark" ? "#a0b4c8" : "#4a5568"}
            />
            <FormControlLabel style={{ marginTop: 15 }}>
              <FormControlLabelText style={{ fontFamily: "Montserrat_400Regular" }}>Type of Defense</FormControlLabelText>
            </FormControlLabel>
            <PickerTrigger
              value={formData.defenseType}
              placeholder="Select option"
              onPress={() => setDefensePickerOpen(true)}
              borderColor={colorScheme === "dark" ? "#1e3a52" : "#bfdbfe"}
              textColor={colorScheme === "dark" ? "#edf5ff" : "#02080f"}
              placeholderColor={colorScheme === "dark" ? "#a0b4c8" : "#4a5568"}
            />
          </VStack>
        </FormControl>
        <TouchableOpacity
          style={[isFormFilled ? styles.disabledGenerateButton : themeGenerateButtonStyle]}
          disabled={isFormFilled}
          onPress={handleGenerateTeam}
        >
          <Text style={themeGenerateButtonTextStyle}>Generate Team</Text>
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
        <Text style={[themeTextStyle, {marginTop: 8, marginBottom: 18, textAlign: "center" }]}>Team Generated!</Text>
      )}
      {generateTeam && (
        <Box style={themeTableStyle}>
          {headCoach ? (
            <Text style={[themeTextStyle, { fontSize: 18, fontFamily: "Montserrat_700Bold", textAlign: "center", paddingVertical: 12, paddingHorizontal: 8 }]}>
              Head Coach: {headCoach}{headCoachTeam ? ` (${headCoachTeam})` : ""}
            </Text>
          ) : null}
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
                  <TableData style={{ flexWrap: "wrap", flex: 1 }}>{abbToTeamNames[player.nfl_team as keyof typeof abbToTeamNames] || player.nfl_team}</TableData>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}
      {loading && (
        <Spinner size="large" color="blue" style={{ marginTop: 20 }} />
      )}
      <PickerModal
        visible={offensePickerOpen}
        onClose={() => setOffensePickerOpen(false)}
        title="Type of Offense"
        items={[
          { label: "3 WR 1 TE", value: "3 WR 1 TE" },
          { label: "2 WR 2 TE", value: "2 WR 2 TE" },
        ]}
        selectedValue={formData.offenseType}
        onSelect={(value) => setFormData({ ...formData, offenseType: value })}
      />
      <PickerModal
        visible={defensePickerOpen}
        onClose={() => setDefensePickerOpen(false)}
        title="Type of Defense"
        items={[
          { label: "4-3 Base Defense", value: "4-3 Base Defense" },
          { label: "3-4 Base Defense", value: "3-4 Base Defense" },
        ]}
        selectedValue={formData.defenseType}
        onSelect={(value) => setFormData({ ...formData, defenseType: value })}
      />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    alignItems: "center",
    paddingHorizontal: 16,
    paddingBottom: 60,
  },
  text: {
    fontSize: 29,
    fontFamily: "Montserrat_700Bold",
    marginTop: 40,
    textAlign: "center",
  },
  subText: {
    fontSize: 16,
    fontFamily: "Montserrat_400Regular",
    marginTop: 10,
    textAlign: "center",
  },
  formContainer: {
    flexDirection: "column",
    marginTop: 20,
    gap: 12,
    padding: 16,
    marginBottom: 20,
    width: "100%",
    borderRadius: 14,
    borderWidth: 1,
  },
  lightForm: {
    backgroundColor: "#ffffff",
    borderColor: "#bfdbfe",
    boxShadow: "rgba(0, 0, 0, 0.24) 0px 3px 8px",
  },
  darkForm: {
    backgroundColor: "#02080f",
    borderColor: "#1e3a52",
    boxShadow: "rgba(250, 250, 250, 0.8) 0px 3px 8px",
  },
  lightTable: {
    width: "100%",
    marginBottom: 20,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#bfdbfe",
    overflow: "hidden",
    boxShadow: "rgba(0, 0, 0, 0.24) 0px 3px 8px",
  },
  darkTable: {
    width: "100%",
    marginBottom: 20,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#1e3a52",
    overflow: "hidden",
    boxShadow: "rgba(250, 250, 250, 0.8) 0px 3px 8px",
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
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  darkGenerateButton: {
    backgroundColor: "#edf5ff",
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  disabledGenerateButton: {
    backgroundColor: "#9ca3af",
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  lightSaveButton: {
    backgroundColor: "#008a33",
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  darkSaveButton: {
    backgroundColor: "#34f77c",
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  disabledSaveButton: {
    backgroundColor: "#d4d4d4",
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 10,
  },
  lightButtonText: {
    color: "#edf5ff",
    fontFamily: "Montserrat_700Bold",
    fontSize: 16,
  },
  darkButtonText: {
    color: "#02080f",
    fontFamily: "Montserrat_700Bold",
    fontSize: 16,
  },
  lightSaveButtonText: {
    color: "#ffffff",
    fontFamily: "Montserrat_700Bold",
    fontSize: 16,
  },
  darkSaveButtonText: {
    color: "#000000",
    fontFamily: "Montserrat_700Bold",
    fontSize: 16,
  },
  disabledSaveButtonText: {
    color: "#ffffff",
    fontFamily: "Montserrat_700Bold",
    fontSize: 16,
  },
});

export default GenerateTeam;
