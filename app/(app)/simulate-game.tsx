import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  useColorScheme,
  View,
  ActivityIndicator,
  Platform,
} from "react-native";
import {
  FormControl,
  FormControlLabel,
  FormControlLabelText,
} from "@/components/ui/form-control";
import { VStack } from "@/components/ui/vstack";
import PickerModal, { PickerTrigger } from "@/components/PickerModal";
import { useState, useEffect } from "react";
import * as Application from "expo-application";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

const NFL_TEAMS = [
  "Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens",
  "Buffalo Bills", "Carolina Panthers", "Chicago Bears",
  "Cincinnati Bengals", "Cleveland Browns", "Dallas Cowboys",
  "Denver Broncos", "Detroit Lions", "Green Bay Packers",
  "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars",
  "Kansas City Chiefs", "Las Vegas Raiders", "Los Angeles Chargers",
  "Los Angeles Rams", "Miami Dolphins", "Minnesota Vikings",
  "New England Patriots", "New Orleans Saints", "New York Giants",
  "New York Jets", "Philadelphia Eagles", "Pittsburgh Steelers",
  "San Francisco 49ers", "Seattle Seahawks", "Tampa Bay Buccaneers",
  "Tennessee Titans", "Washington Commanders",
];

const SEASONS = Array.from({ length: 11 }, (_, i) => String(2015 + i));

type TeamSummary = { id: string; team_name: string };

export default function SimulateGame() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";

  const [myTeams, setMyTeams] = useState<TeamSummary[]>([]);
  const [selectedMyTeam, setSelectedMyTeam] = useState("");
  const [selectedOpponent, setSelectedOpponent] = useState("");
  const [selectedSeason, setSelectedSeason] = useState("");
  const [loading, setLoading] = useState(false);
  const [myTeamOpen, setMyTeamOpen] = useState(false);
  const [nflPickerOpen, setNflPickerOpen] = useState(false);
  const [seasonOpen, setSeasonOpen] = useState(false);

  const c = {
    bg: isDark ? "#132130" : "#edf5ff",
    card: isDark ? "#02080f" : "#ffffff",
    text: isDark ? "#edf5ff" : "#02080f",
    subtext: isDark ? "#a0b4c8" : "#4a5568",
    border: isDark ? "#1e3a52" : "#bfdbfe",
    shadow: isDark
      ? "rgba(250,250,250,0.8) 0px 3px 8px"
      : "rgba(0,0,0,0.24) 0px 3px 8px",
    button: isDark ? "#edf5ff" : "#02080f",
    buttonText: isDark ? "#02080f" : "#edf5ff",
  };

  const getDeviceUuid = async () => {
    if (Platform.OS === "android") {
      return Application.getAndroidId() || "test-device-uuid";
    } else if (Platform.OS === "ios") {
      return (await Application.getIosIdForVendorAsync()) || "test-device-uuid";
    }
    return "test-device-uuid";
  };

  useEffect(() => {
    const fetchTeams = async () => {
      const deviceUuid = await getDeviceUuid();
      fetch(`${API_URL}/api/team/device/${deviceUuid}`)
        .then((r) => r.json())
        .then((result) => {
          if (result.status === "Success" && result.data) {
            setMyTeams(
              result.data.map((t: { id: string; team_name: string }) => ({
                id: t.id,
                team_name: t.team_name,
              }))
            );
          }
        })
        .catch(() => {});
    };
    fetchTeams();
  }, []);

  const canSimulate = !!(selectedMyTeam && selectedOpponent && selectedSeason && !loading);

  const handleSimulate = async () => {
    if (!canSimulate) return;
    setLoading(true);
    // simulation logic goes here
    setLoading(false);
  };

  const myTeamItems = myTeams.map((t) => ({ label: t.team_name, value: t.team_name }));
  const nflTeamItems = NFL_TEAMS.map((t) => ({ label: t, value: t }));
  const seasonItems = SEASONS.slice().reverse().map((s) => ({ label: s, value: s }));

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: c.bg }}
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator={false}
    >
      <Text style={[styles.title, { color: c.text }]}>Simulate a Game</Text>
      <Text style={[styles.subtitle, { color: c.subtext }]}>
        Pit your generated team against a real NFL squad and see how the game plays out.
      </Text>

      <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
        <FormControl size="lg">
          <VStack space="xl">

            {/* Your Team */}
            <VStack space="sm">
              <FormControlLabel>
                <FormControlLabelText style={{ color: c.text, fontFamily: "Montserrat_700Bold" }}>
                  Your Team
                </FormControlLabelText>
              </FormControlLabel>
              <PickerTrigger
                value={selectedMyTeam}
                placeholder="Select your generated team"
                onPress={() => setMyTeamOpen(true)}
                borderColor={c.border}
                textColor={c.text}
                placeholderColor={c.subtext}
              />
            </VStack>

            {/* VS divider */}
            <View style={styles.vsDivider}>
              <View style={[styles.vsDividerLine, { backgroundColor: c.border }]} />
              <Text style={[styles.vsText, { color: c.subtext }]}>VS</Text>
              <View style={[styles.vsDividerLine, { backgroundColor: c.border }]} />
            </View>

            {/* NFL Opponent */}
            <VStack space="sm">
              <FormControlLabel>
                <FormControlLabelText style={{ color: c.text, fontFamily: "Montserrat_700Bold" }}>
                  NFL Opponent
                </FormControlLabelText>
              </FormControlLabel>
              <PickerTrigger
                value={selectedOpponent}
                placeholder="Select an NFL team"
                onPress={() => setNflPickerOpen(true)}
                borderColor={c.border}
                textColor={c.text}
                placeholderColor={c.subtext}
              />
            </VStack>

            {/* Season */}
            <VStack space="sm">
              <FormControlLabel>
                <FormControlLabelText style={{ color: c.text, fontFamily: "Montserrat_700Bold" }}>
                  Season
                </FormControlLabelText>
              </FormControlLabel>
              <Text style={[styles.seasonHint, { color: c.subtext }]}>
                The NFL opponent's stats from this season will be used.
              </Text>
              <PickerTrigger
                value={selectedSeason}
                placeholder="Select a season"
                onPress={() => setSeasonOpen(true)}
                borderColor={c.border}
                textColor={c.text}
                placeholderColor={c.subtext}
              />
            </VStack>

          </VStack>
        </FormControl>

        <TouchableOpacity
          style={[styles.simulateBtn, { backgroundColor: canSimulate ? c.button : "#9ca3af" }]}
          disabled={!canSimulate}
          onPress={handleSimulate}
        >
          {loading ? (
            <ActivityIndicator color={c.buttonText} />
          ) : (
            <Text style={[styles.simulateBtnText, { color: c.buttonText }]}>
              Simulate Game
            </Text>
          )}
        </TouchableOpacity>
      </View>

      {!loading && selectedMyTeam && selectedOpponent && selectedSeason && (
        <View style={[styles.card, styles.resultPlaceholder, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
          <Text style={[styles.resultPlaceholderText, { color: c.subtext }]}>
            Game results will appear here after simulation.
          </Text>
        </View>
      )}

      <PickerModal
        visible={myTeamOpen}
        onClose={() => setMyTeamOpen(false)}
        title="Select Your Team"
        items={myTeamItems}
        selectedValue={selectedMyTeam}
        onSelect={setSelectedMyTeam}
      />

      <PickerModal
        visible={nflPickerOpen}
        onClose={() => setNflPickerOpen(false)}
        title="Select NFL Team"
        items={nflTeamItems}
        selectedValue={selectedOpponent}
        onSelect={setSelectedOpponent}
      />

      <PickerModal
        visible={seasonOpen}
        onClose={() => setSeasonOpen(false)}
        title="Select Season"
        items={seasonItems}
        selectedValue={selectedSeason}
        onSelect={setSelectedSeason}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    alignItems: "center",
    paddingHorizontal: 16,
    paddingBottom: 60,
    paddingTop: 30,
  },
  title: {
    fontSize: 26,
    fontFamily: "Montserrat_700Bold",
    textAlign: "center",
  },
  subtitle: {
    fontSize: 14,
    fontFamily: "Montserrat_400Regular",
    marginTop: 8,
    textAlign: "center",
    marginBottom: 20,
  },
  card: {
    width: "100%",
    borderRadius: 14,
    borderWidth: 1,
    padding: 16,
    marginBottom: 16,
    gap: 16,
  },
  vsDivider: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  vsDividerLine: {
    flex: 1,
    height: 1,
  },
  vsText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 13,
    letterSpacing: 2,
  },
  seasonHint: {
    fontSize: 12,
    fontFamily: "Montserrat_400Regular",
    marginTop: -4,
  },
  simulateBtn: {
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 4,
  },
  simulateBtnText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 16,
  },
  resultPlaceholder: {
    alignItems: "center",
    paddingVertical: 40,
  },
  resultPlaceholderText: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
    textAlign: "center",
  },
});
