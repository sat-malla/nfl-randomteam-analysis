import {
  Text,
  ScrollView,
  TouchableOpacity,
  View,
  Platform,
  ActivityIndicator,
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
import { VStack } from "@/components/ui/vstack";
import { useState, useEffect } from "react";
import * as Application from "expo-application";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

type StatProjection = {
  projected_total: number;
  floor: number;
  ceiling: number;
};

type PlayerProjection = {
  position: string;
  stats: Record<string, StatProjection>;
};

type AnalysisResult = {
  projected_wins: number;
  win_floor: number;
  win_ceiling: number;
  playoff_probability: number;
  superbowl_probability: number;
  player_projections: Record<string, PlayerProjection>;
};

type Team = {
  id: string;
  team_name: string;
};

const STAT_LABELS: Record<string, string> = {
  passing_yards: "Pass Yds",
  passing_tds: "Pass TDs",
  interceptions: "INTs",
  rushing_yards: "Rush Yds",
  carries: "Carries",
  rushing_tds: "Rush TDs",
  receptions: "Rec",
  targets: "Tgts",
  receiving_yards: "Rec Yds",
  receiving_tds: "Rec TDs",
  def_tackles_solo: "Tackles",
  def_sacks: "Sacks",
  def_interceptions: "INTs",
  def_passes_defended: "PD",
  def_fumbles_forced: "FF",
  fg_made: "FG Made",
  fg_att: "FG Att",
  fg_pct: "FG%",
  punt_return_yards: "PR Yds",
  kickoff_return_yards: "KR Yds",
  kickoff_returns: "KR",
  punt_returns: "PR",
};

const AnalyzeTeam = () => {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";

  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

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
            const mapped = result.data.map(
              (team: { id: string; team_name: string }) => ({
                id: team.id,
                team_name: team.team_name,
              })
            );
            setTeams(mapped);
          }
        })
        .catch((err) => console.log(err));
    };
    fetchTeams();
  }, []);

  const handleAnalyze = async () => {
    if (!selectedTeamId) return;
    setLoading(true);
    setAnalysis(null);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/team/analyze/${selectedTeamId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const result = await response.json();
      if (!response.ok) {
        setError(result.detail ?? "Analysis failed");
      } else {
        setAnalysis(result);
      }
    } catch (e) {
      setError("Could not reach server. Make sure both backends are running.");
    } finally {
      setLoading(false);
    }
  };

  const c = {
    bg: isDark ? "#132130" : "#edf5ff",
    card: isDark ? "#02080f" : "#ffffff",
    text: isDark ? "#edf5ff" : "#02080f",
    subtext: isDark ? "#a0b4c8" : "#4a5568",
    accent: "#004ba1",
    accentLight: isDark ? "#1a3a6b" : "#dbeafe",
    border: isDark ? "#1e3a52" : "#bfdbfe",
    button: isDark ? "#edf5ff" : "#02080f",
    buttonText: isDark ? "#02080f" : "#edf5ff",
    green: isDark ? "#34f77c" : "#008a33",
    amber: isDark ? "#fbbf24" : "#d97706",
    red: isDark ? "#f87171" : "#dc2626",
  };

  const winColor =
    analysis && analysis.projected_wins >= 9
      ? c.green
      : analysis && analysis.projected_wins >= 6
      ? c.amber
      : c.red;

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: c.bg }}
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator={true}
      keyboardShouldPersistTaps="handled"
    >
      <Text style={[styles.title, { color: c.text }]}>Analyze Your Team</Text>
      <Text style={[styles.subtitle, { color: c.subtext }]}>
        Select a saved team to run a full season simulation.
      </Text>

      <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border }]}>
        <FormControl size="lg">
          <VStack space="md">
            <FormControlLabel>
              <FormControlLabelText style={{ color: c.text }}>Choose Team</FormControlLabelText>
            </FormControlLabel>
            <Select
              onValueChange={(value) => {
                const team = teams.find((t) => t.team_name === value);
                if (team) setSelectedTeamId(team.id);
              }}
            >
              <SelectTrigger
                variant="outline"
                size="lg"
                style={{ flexDirection: "row", justifyContent: "space-between" }}
              >
                <SelectInput placeholder="Select a team" style={{ flex: 1, color: c.text }} />
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
          style={[
            styles.button,
            { backgroundColor: selectedTeamId && !loading ? c.button : "#9ca3af" },
          ]}
          disabled={!selectedTeamId || loading}
          onPress={handleAnalyze}
        >
          {loading ? (
            <ActivityIndicator color={c.buttonText} />
          ) : (
            <Text style={[styles.buttonText, { color: c.buttonText }]}>Analyze Team</Text>
          )}
        </TouchableOpacity>

        {loading && (
          <Text style={[styles.loadingNote, { color: c.subtext }]}>
            Running 1,000 season simulations… this takes ~30 seconds.
          </Text>
        )}

        {error && (
          <Text style={[styles.error, { color: c.red }]}>{error}</Text>
        )}
      </View>

      {analysis && (
        <>
          {/* Season Projection */}
          <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border }]}>
            <Text style={[styles.cardTitle, { color: c.text }]}>Season Projection</Text>

            <View style={styles.winsRow}>
              <Text style={[styles.winsNumber, { color: winColor }]}>
                {analysis.projected_wins}
              </Text>
              <Text style={[styles.winsLabel, { color: c.subtext }]}>Projected Wins</Text>
            </View>

            <Text style={[styles.winsRange, { color: c.subtext }]}>
              Floor: {analysis.win_floor}W — Ceiling: {analysis.win_ceiling}W
            </Text>

            <View style={styles.probRow}>
              <View style={[styles.probCard, { backgroundColor: c.accentLight, borderColor: c.border }]}>
                <Text style={[styles.probPct, { color: c.accent }]}>
                  {analysis.playoff_probability}%
                </Text>
                <Text style={[styles.probLabel, { color: c.subtext }]}>Playoff Chance</Text>
              </View>
              <View style={[styles.probCard, { backgroundColor: c.accentLight, borderColor: c.border }]}>
                <Text style={[styles.probPct, { color: c.accent }]}>
                  {analysis.superbowl_probability}%
                </Text>
                <Text style={[styles.probLabel, { color: c.subtext }]}>Super Bowl Chance</Text>
              </View>
            </View>
          </View>

          {/* Player Projections */}
          <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border }]}>
            <Text style={[styles.cardTitle, { color: c.text }]}>Player Projections</Text>
            {Object.entries(analysis.player_projections).map(([name, proj]) => (
              <View key={name} style={[styles.playerCard, { borderColor: c.border }]}>
                <View style={styles.playerHeader}>
                  <Text style={[styles.playerName, { color: c.text }]}>{name}</Text>
                  <View style={[styles.posBadge, { backgroundColor: c.accentLight }]}>
                    <Text style={[styles.posText, { color: c.accent }]}>{proj.position}</Text>
                  </View>
                </View>
                {Object.entries(proj.stats).map(([stat, vals]) => (
                  <View key={stat} style={styles.statRow}>
                    <Text style={[styles.statLabel, { color: c.subtext }]}>
                      {STAT_LABELS[stat] ?? stat}
                    </Text>
                    <Text style={[styles.statValue, { color: c.text }]}>
                      {vals.projected_total}
                    </Text>
                    <Text style={[styles.statRange, { color: c.subtext }]}>
                      {vals.floor}–{vals.ceiling}
                    </Text>
                  </View>
                ))}
              </View>
            ))}
          </View>
        </>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  scrollContent: {
    alignItems: "center",
    paddingHorizontal: 16,
    paddingBottom: 60,
    paddingTop: 30,
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
    textAlign: "center",
  },
  subtitle: {
    fontSize: 15,
    marginTop: 8,
    textAlign: "center",
    marginBottom: 20,
  },
  card: {
    width: "100%",
    borderRadius: 14,
    borderWidth: 1,
    padding: 16,
    marginBottom: 20,
    gap: 12,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 4,
  },
  button: {
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 4,
  },
  buttonText: {
    fontWeight: "700",
    fontSize: 16,
  },
  loadingNote: {
    fontSize: 13,
    textAlign: "center",
    marginTop: -4,
  },
  error: {
    fontSize: 14,
    textAlign: "center",
  },
  winsRow: {
    alignItems: "center",
    marginVertical: 4,
  },
  winsNumber: {
    fontSize: 64,
    fontWeight: "800",
    lineHeight: 70,
  },
  winsLabel: {
    fontSize: 16,
    marginTop: 2,
  },
  winsRange: {
    textAlign: "center",
    fontSize: 14,
  },
  probRow: {
    flexDirection: "row",
    gap: 12,
    marginTop: 4,
  },
  probCard: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    padding: 12,
    alignItems: "center",
  },
  probPct: {
    fontSize: 24,
    fontWeight: "700",
  },
  probLabel: {
    fontSize: 12,
    marginTop: 2,
    textAlign: "center",
  },
  playerCard: {
    borderTopWidth: 1,
    paddingTop: 12,
    marginTop: 4,
    gap: 6,
  },
  playerHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
  playerName: {
    fontSize: 15,
    fontWeight: "700",
    flex: 1,
  },
  posBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  posText: {
    fontSize: 12,
    fontWeight: "600",
  },
  statRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  statLabel: {
    fontSize: 13,
    width: 80,
  },
  statValue: {
    fontSize: 13,
    fontWeight: "600",
    width: 50,
    textAlign: "right",
  },
  statRange: {
    fontSize: 12,
    marginLeft: 8,
  },
});

export default AnalyzeTeam;
