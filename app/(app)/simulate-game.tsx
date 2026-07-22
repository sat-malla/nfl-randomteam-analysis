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

type PlayEntry = {
  quarter: string;
  team: string;
  play: string;
  score: string;
};

type BoxEntry = {
  name: string;
  position: string;
  stats: Record<string, number>;
};

type SimResult = {
  user_team: string;
  opponent: string;
  season: number;
  final_score: { user: number; opponent: number };
  winner: string;
  play_by_play: PlayEntry[];
  box_score: BoxEntry[];
};

const QUARTER_COLORS: Record<string, string> = {
  Q1: "#3b82f6",
  Q2: "#f59e0b",
  Q3: "#10b981",
  Q4: "#ef4444",
};

export default function SimulateGame() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";

  const [myTeams, setMyTeams] = useState<TeamSummary[]>([]);
  const [selectedMyTeamName, setSelectedMyTeamName] = useState("");
  const [selectedOpponent, setSelectedOpponent] = useState("");
  const [selectedSeason, setSelectedSeason] = useState("");
  const [isHome, setIsHome] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimResult | null>(null);
  const [error, setError] = useState("");

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
    win: "#16a34a",
    loss: "#dc2626",
    tie: "#6b7280",
  };

  const getDeviceUuid = async () => {
    if (Platform.OS === "android") return Application.getAndroidId() || "test-device-uuid";
    if (Platform.OS === "ios") return (await Application.getIosIdForVendorAsync()) || "test-device-uuid";
    return "test-device-uuid";
  };

  useEffect(() => {
    const fetchTeams = async () => {
      const uuid = await getDeviceUuid();
      fetch(`${API_URL}/api/team/device/${uuid}`)
        .then((r) => r.json())
        .then((res) => {
          if (res.status === "Success" && res.data) {
            setMyTeams(res.data.map((t: { id: string; team_name: string }) => ({
              id: t.id,
              team_name: t.team_name,
            })));
          }
        })
        .catch(() => {});
    };
    fetchTeams();
  }, []);

  const selectedTeam = myTeams.find((t) => t.team_name === selectedMyTeamName);
  const canSimulate = !!(selectedTeam && selectedOpponent && selectedSeason && isHome !== null && !loading);

  const handleSimulate = async () => {
    if (!canSimulate || !selectedTeam) return;
    setLoading(true);
    setResult(null);
    setError("");
    try {
      const resp = await fetch(`${API_URL}/api/simulate/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          team_id: selectedTeam.id,
          nfl_opponent: selectedOpponent,
          season: parseInt(selectedSeason, 10),
          is_home: isHome,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setError(data.message ?? "Simulation failed. Try again.");
      } else {
        setResult(data);
      }
    } catch {
      setError("Network error. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const myTeamItems = myTeams.map((t) => ({ label: t.team_name, value: t.team_name }));
  const nflTeamItems = NFL_TEAMS.map((t) => ({ label: t, value: t }));
  const seasonItems = SEASONS.slice().reverse().map((s) => ({ label: s, value: s }));

  const winnerColor = result
    ? result.winner === "TIE"
      ? c.tie
      : result.winner === result.user_team
      ? c.win
      : c.loss
    : c.text;

  const winnerLabel = result
    ? result.winner === "TIE"
      ? "TIE GAME"
      : result.winner === result.user_team
      ? "YOU WIN!"
      : "YOU LOSE"
    : "";

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
            <VStack space="sm">
              <FormControlLabel>
                <FormControlLabelText style={{ color: c.text, fontFamily: "Montserrat_700Bold" }}>
                  Your Team
                </FormControlLabelText>
              </FormControlLabel>
              <PickerTrigger
                value={selectedMyTeamName}
                placeholder="Select your generated team"
                onPress={() => setMyTeamOpen(true)}
                borderColor={c.border}
                textColor={c.text}
                placeholderColor={c.subtext}
              />
            </VStack>

            <View style={styles.vsDivider}>
              <View style={[styles.vsDividerLine, { backgroundColor: c.border }]} />
              <Text style={[styles.vsText, { color: c.subtext }]}>VS</Text>
              <View style={[styles.vsDividerLine, { backgroundColor: c.border }]} />
            </View>

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

            <VStack space="sm">
              <FormControlLabel>
                <FormControlLabelText style={{ color: c.text, fontFamily: "Montserrat_700Bold" }}>
                  Season
                </FormControlLabelText>
              </FormControlLabel>
              <Text style={[styles.hint, { color: c.subtext }]}>
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

            <VStack space="sm">
              <FormControlLabel>
                <FormControlLabelText style={{ color: c.text, fontFamily: "Montserrat_700Bold" }}>
                  Game Location
                </FormControlLabelText>
              </FormControlLabel>
              <View style={styles.locationGroup}>
                {([true, false] as const).map((home) => {
                  const active = isHome === home;
                  return (
                    <TouchableOpacity
                      key={String(home)}
                      style={[
                        styles.locationBtn,
                        {
                          backgroundColor: active ? c.button : "transparent",
                          borderColor: active ? c.button : c.border,
                          flex: 1,
                        },
                      ]}
                      onPress={() => setIsHome(home)}
                    >
                      <Text style={[
                        styles.locationBtnText,
                        { color: active ? c.buttonText : c.subtext },
                      ]}>
                        {home ? "Home" : "Away"}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
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
            <Text style={[styles.simulateBtnText, { color: canSimulate ? c.buttonText : "#fff" }]}>
              Simulate Game
            </Text>
          )}
        </TouchableOpacity>
      </View>

      {!!error && (
        <View style={[styles.card, { backgroundColor: "#fee2e2", borderColor: "#fca5a5", boxShadow: c.shadow }]}>
          <Text style={{ color: "#dc2626", fontFamily: "Montserrat_400Regular", fontSize: 14 }}>
            {error}
          </Text>
        </View>
      )}

      {result && (
        <>
          <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
            <Text style={[styles.sectionTitle, { color: c.text }]}>Final Score</Text>
            <View style={styles.scoreboard}>
              <View style={styles.scoreTeam}>
                <Text style={[styles.scoreTeamName, { color: c.text }]} numberOfLines={2}>
                  {result.user_team}
                </Text>
                <Text style={[styles.scoreNum, { color: winnerColor }]}>
                  {result.final_score.user}
                </Text>
              </View>
              <View style={styles.scoreTeam}>
                <Text style={[styles.scoreTeamName, { color: c.text }]} numberOfLines={2}>
                  {result.opponent}
                </Text>
                <Text style={[styles.scoreNum, { color: winnerColor }]}>
                  {result.final_score.opponent}
                </Text>
              </View>
            </View>
            <Text style={[styles.winnerBadge, { color: winnerColor }]}>{winnerLabel}</Text>
            <Text style={[styles.seasonLabel, { color: c.subtext }]}>
              {result.opponent} · {result.season} Season
            </Text>
          </View>

          {result.box_score.length > 0 && (
            <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
              <Text style={[styles.sectionTitle, { color: c.text }]}>Your Team Box Score</Text>
              {result.box_score.map((player, i) => (
                <View key={i} style={[styles.boxRow, { borderBottomColor: c.border }]}>
                  <View style={styles.boxLeft}>
                    <Text style={[styles.boxPos, { color: c.subtext }]}>{player.position}</Text>
                    <Text style={[styles.boxName, { color: c.text }]}>{player.name}</Text>
                  </View>
                  <View style={styles.boxStats}>
                    {Object.entries(player.stats).map(([label, val]) => (
                      <View key={label} style={styles.statChip}>
                        <Text style={[styles.statVal, { color: c.text }]}>{val}</Text>
                        <Text style={[styles.statLabel, { color: c.subtext }]}>{label}</Text>
                      </View>
                    ))}
                  </View>
                </View>
              ))}
            </View>
          )}

          {result.play_by_play.length > 0 && (
            <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
              <Text style={[styles.sectionTitle, { color: c.text }]}>Play-by-Play</Text>
              {result.play_by_play.map((entry, i) => {
                const isUser = entry.team === result.user_team;
                const qColor = QUARTER_COLORS[entry.quarter] ?? c.subtext;
                return (
                  <View key={i} style={[styles.playRow, { borderBottomColor: c.border }]}>
                    <View style={styles.playMeta}>
                      <View style={[styles.quarterBadge, { backgroundColor: qColor }]}>
                        <Text style={styles.quarterText}>{entry.quarter}</Text>
                      </View>
                      <Text style={[styles.playScore, { color: c.subtext }]}>{entry.score}</Text>
                    </View>
                    <View style={[
                      styles.playContent,
                      { borderLeftColor: isUser ? c.button : c.border, borderLeftWidth: 3 }
                    ]}>
                      <Text style={[styles.playTeamLabel, { color: isUser ? c.text : c.subtext }]}>
                        {entry.team}
                      </Text>
                      <Text style={[styles.playText, { color: c.text }]}>{entry.play}</Text>
                    </View>
                  </View>
                );
              })}
            </View>
          )}
        </>
      )}

      <PickerModal
        visible={myTeamOpen}
        onClose={() => setMyTeamOpen(false)}
        title="Select Your Team"
        items={myTeamItems}
        selectedValue={selectedMyTeamName}
        onSelect={setSelectedMyTeamName}
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
    gap: 12,
  },
  vsDivider: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  vsDividerLine: { flex: 1, height: 1 },
  vsText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 13,
    letterSpacing: 2,
  },
  hint: {
    fontSize: 12,
    fontFamily: "Montserrat_400Regular",
    marginTop: -4,
  },
  locationGroup: {
    flexDirection: "row",
    gap: 10,
  },
  locationBtn: {
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: "center",
  },
  locationBtnText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 14,
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
  sectionTitle: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 20,
    marginBottom: 4,
    textAlign: "center",
  },
  scoreboard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-around",
    paddingVertical: 8,
  },
  scoreTeam: { alignItems: "center", flex: 1 },
  scoreTeamName: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 13,
    textAlign: "center",
    marginBottom: 6,
  },
  scoreNum: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 48,
  },
  scoreDash: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 28,
    marginBottom: 8,
  },
  winnerBadge: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 20,
    textAlign: "center",
    letterSpacing: 2,
  },
  seasonLabel: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 12,
    textAlign: "center",
  },
  boxRow: {
    paddingVertical: 10,
    borderBottomWidth: 0.5,
    gap: 4,
  },
  boxLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 4,
  },
  boxPos: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 11,
    opacity: 0.7,
    width: 32,
  },
  boxName: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 14,
  },
  boxStats: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    paddingLeft: 40,
  },
  statChip: { alignItems: "center", minWidth: 40 },
  statVal: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 15,
  },
  statLabel: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 10,
  },
  playRow: {
    paddingVertical: 10,
    borderBottomWidth: 0.5,
    gap: 6,
  },
  playMeta: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  quarterBadge: {
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  quarterText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 11,
    color: "#fff",
  },
  playScore: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 12,
  },
  playContent: {
    paddingLeft: 10,
    gap: 2,
  },
  playTeamLabel: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 11,
  },
  playText: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
    lineHeight: 20,
  },
});
