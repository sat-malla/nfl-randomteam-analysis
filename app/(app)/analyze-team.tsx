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
  name: string;
  position: string;
  nfl_team: string;
  stats: Record<string, StatProjection>;
};

type CoachAnalysis = {
  coach: string;
  seasons_coached: number;
  record: string;
  win_rate: number;
  coach_multiplier: number;
  qb_familiarity: boolean;
  note?: string;
};

type AnalysisResult = {
  projected_wins: number;
  win_floor: number;
  win_ceiling: number;
  playoff_probability: number;
  superbowl_probability: number;
  player_projections: PlayerProjection[];
  coach_analysis?: CoachAnalysis;
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

const POS_COLORS_LIGHT: Record<string, { bg: string; text: string }> = {
  QB: { bg: "#dc2626", text: "#ffffff" },
  RB: { bg: "#1f55ed", text: "#ffffff" },
  FB: { bg: "#1d4ed8", text: "#ffffff" },
  WR: { bg: "#059669", text: "#ffffff" },
  TE: { bg: "#d97706", text: "#ffffff" },
  OT: { bg: "#7c3aed", text: "#ffffff" },
  G: { bg: "#7c3aed", text: "#ffffff" },
  C: { bg: "#7c3aed", text: "#ffffff" },
  OL: { bg: "#7c3aed", text: "#ffffff" },
  DE: { bg: "#ea580c", text: "#ffffff" },
  DT: { bg: "#ea580c", text: "#ffffff" },
  NT: { bg: "#ea580c", text: "#ffffff" },
  DL: { bg: "#ea580c", text: "#ffffff" },
  LB: { bg: "#db2777", text: "#ffffff" },
  ILB: { bg: "#db2777", text: "#ffffff" },
  OLB: { bg: "#db2777", text: "#ffffff" },
  MLB: { bg: "#db2777", text: "#ffffff" },
  CB: { bg: "#0891b2", text: "#ffffff" },
  S: { bg: "#004c75", text: "#ffffff" },
  FS: { bg: "#004c75", text: "#ffffff" },
  SS: { bg: "#004c75", text: "#ffffff" },
  DB: { bg: "#004c75", text: "#ffffff" },
  SAF: { bg: "#004c75", text: "#ffffff" },
  Nickel: { bg: "#0891b2", text: "#ffffff" },
  Dime: { bg: "#0891b2", text: "#ffffff" },
  K: { bg: "#1ec95d", text: "#ffffff" },
  P: { bg: "#21ccb2", text: "#ffffff" },
  LS: { bg: "#57534e", text: "#ffffff" },
  RS: { bg: "#4d2325", text: "#ffffff" },
};

const POS_COLORS_DARK: Record<string, { bg: string; text: string }> = {
  QB: { bg: "#f87171", text: "#000000" },
  RB: { bg: "#6b8ef5", text: "#000000" },
  FB: { bg: "#60a5fa", text: "#000000" },
  WR: { bg: "#34d399", text: "#000000" },
  TE: { bg: "#fbbf24", text: "#000000" },
  OT: { bg: "#a78bfa", text: "#000000" },
  G: { bg: "#a78bfa", text: "#000000" },
  C: { bg: "#a78bfa", text: "#000000" },
  OL: { bg: "#a78bfa", text: "#000000" },
  DE: { bg: "#fb923c", text: "#000000" },
  DT: { bg: "#fb923c", text: "#000000" },
  NT: { bg: "#fb923c", text: "#000000" },
  DL: { bg: "#fb923c", text: "#000000" },
  LB: { bg: "#f472b6", text: "#000000" },
  ILB: { bg: "#f472b6", text: "#000000" },
  OLB: { bg: "#f472b6", text: "#000000" },
  MLB: { bg: "#f472b6", text: "#000000" },
  CB: { bg: "#22d3ee", text: "#000000" },
  S: { bg: "#38bdf8", text: "#000000" },
  FS: { bg: "#38bdf8", text: "#000000" },
  SS: { bg: "#38bdf8", text: "#000000" },
  DB: { bg: "#38bdf8", text: "#000000" },
  SAF: { bg: "#38bdf8", text: "#000000" },
  Nickel: { bg: "#22d3ee", text: "#000000" },
  Dime: { bg: "#22d3ee", text: "#000000" },
  K: { bg: "#4ade80", text: "#000000" },
  P: { bg: "#2dd4bf", text: "#000000" },
  LS: { bg: "#a8a29e", text: "#000000" },
  RS: { bg: "#f87171", text: "#000000" },
};

const AnalyzeTeam = () => {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";
  const POS_COLORS = isDark ? POS_COLORS_DARK : POS_COLORS_LIGHT;

  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [hasSaved, setHasSaved] = useState(false);
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
              }),
            );
            setTeams(mapped);
          }
        })
        .catch((err) => console.log(err));
    };
    fetchTeams();
  }, []);

  const handleSelectTeam = async (teamName: string) => {
    const team = teams.find((t) => t.team_name === teamName);
    if (!team) return;
    setSelectedTeamId(team.id);
    setAnalysis(null);
    setHasSaved(false);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/analysis/${team.id}`);
      const result = await res.json();
      if (res.ok && result.status === "Success") {
        setAnalysis(result.data);
        setHasSaved(true);
      }
    } catch (_) {
      // no saved analysis
    }
  };

  const handleAnalyze = async () => {
    if (!selectedTeamId) return;
    setLoading(true);
    setAnalysis(null);
    setError(null);

    try {
      const response = await fetch(
        `${API_URL}/api/team/analyze/${selectedTeamId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        },
      );
      const result = await response.json();
      if (!response.ok) {
        setError(result.detail ?? "Analysis failed");
      } else {
        setAnalysis(result);
        setHasSaved(true);
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

      <View
        style={[
          styles.card,
          { backgroundColor: c.card, borderColor: c.border },
        ]}
      >
        <FormControl size="lg">
          <VStack space="md">
            <FormControlLabel>
              <FormControlLabelText style={{ color: c.text }}>
                Choose Team
              </FormControlLabelText>
            </FormControlLabel>
            <Select onValueChange={handleSelectTeam}>
              <SelectTrigger
                variant="outline"
                size="lg"
                style={{
                  flexDirection: "row",
                  justifyContent: "space-between",
                }}
              >
                <SelectInput
                  placeholder="Select a team"
                  style={{ flex: 1, color: c.text }}
                />
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
            {
              backgroundColor:
                selectedTeamId && !loading && !hasSaved ? c.button : "#9ca3af",
            },
          ]}
          disabled={!selectedTeamId || loading || hasSaved}
          onPress={handleAnalyze}
        >
          {loading ? (
            <ActivityIndicator color={c.buttonText} />
          ) : (
            <Text
              style={[
                styles.buttonText,
                { color: hasSaved ? "#ffffff" : c.buttonText },
              ]}
            >
              {hasSaved ? "Analyzed" : "Analyze Team"}
            </Text>
          )}
        </TouchableOpacity>

        {hasSaved && !loading && (
          <TouchableOpacity
            style={[styles.button, { backgroundColor: c.amber }]}
            onPress={() => {
              setHasSaved(false);
              handleAnalyze();
            }}
          >
            <Text style={[styles.buttonText, { color: "#ffffff" }]}>
              Re-analyze
            </Text>
          </TouchableOpacity>
        )}

        {loading && (
          <Text style={[styles.loadingNote, { color: c.subtext }]}>
            Running season simulations... ~10 seconds.
          </Text>
        )}

        {error && <Text style={[styles.error, { color: c.red }]}>{error}</Text>}
      </View>

      {analysis && (
        <>
          <View
            style={[
              styles.card,
              { backgroundColor: c.card, borderColor: c.border },
            ]}
          >
            <Text style={[styles.cardTitle, { color: c.text }]}>
              Season Projection
            </Text>

            <View style={styles.winsRow}>
              <Text style={[styles.winsNumber, { color: winColor }]}>
                {analysis.projected_wins}
              </Text>
              <Text style={[styles.winsLabel, { color: c.subtext }]}>
                Projected Wins
              </Text>
            </View>

            <Text style={[styles.winsRange, { color: c.subtext }]}>
              Floor: {analysis.win_floor}W — Ceiling: {analysis.win_ceiling}W
            </Text>

            <View style={styles.probRow}>
              <View
                style={[
                  styles.probCard,
                  {
                    backgroundColor: isDark ? "#60a5fa" : "#1d4ed8",
                    borderWidth: 0,
                  },
                ]}
              >
                <Text
                  style={[
                    styles.probPct,
                    { color: isDark ? "#000000" : "#ffffff" },
                  ]}
                >
                  {analysis.playoff_probability}%
                </Text>
                <Text
                  style={[
                    styles.probLabel,
                    { color: isDark ? "#00000099" : "#ffffff99" },
                  ]}
                >
                  Playoff Chance
                </Text>
              </View>
              <View
                style={[
                  styles.probCard,
                  {
                    backgroundColor: isDark ? "#a78bfa" : "#7c3aed",
                    borderWidth: 0,
                  },
                ]}
              >
                <Text
                  style={[
                    styles.probPct,
                    { color: isDark ? "#000000" : "#ffffff" },
                  ]}
                >
                  {analysis.superbowl_probability}%
                </Text>
                <Text
                  style={[
                    styles.probLabel,
                    { color: isDark ? "#00000099" : "#ffffff99" },
                  ]}
                >
                  Super Bowl Chance
                </Text>
              </View>
            </View>
          </View>

          {analysis.coach_analysis && analysis.coach_analysis.coach && (
            <View
              style={[
                styles.card,
                { backgroundColor: c.card, borderColor: c.border },
              ]}
            >
              <Text style={[styles.cardTitle, { color: c.text }]}>
                Coach Impact
              </Text>
              <Text style={[styles.coachName, { color: c.text }]}>
                {analysis.coach_analysis.coach}
              </Text>
              {analysis.coach_analysis.note ? (
                <Text style={[styles.coachMeta, { color: c.subtext }]}>
                  {analysis.coach_analysis.note}
                </Text>
              ) : (
                <>
                  <Text style={[styles.coachMeta, { color: c.subtext }]}>
                    Since 2015:
                  </Text>
                  <Text style={[styles.coachMeta, { color: c.subtext }]}>
                    {analysis.coach_analysis.seasons_coached} season
                    {analysis.coach_analysis.seasons_coached !== 1
                      ? "s"
                      : ""}{" "}
                    coached · Record: {analysis.coach_analysis.record} · Win
                    rate: {(analysis.coach_analysis.win_rate * 100).toFixed(1)}%
                  </Text>
                  <View style={styles.coachRow}>
                    <View
                      style={[
                        styles.coachBadge,
                        {
                          backgroundColor:
                            analysis.coach_analysis.coach_multiplier >= 1
                              ? isDark
                                ? "#4ade80"
                                : "#16a34a"
                              : isDark
                                ? "#f87171"
                                : "#dc2626",
                        },
                      ]}
                    >
                      <Text
                        style={[
                          styles.coachBadgeText,
                          { color: isDark ? "#000000" : "#ffffff" },
                        ]}
                      >
                        {analysis.coach_analysis.coach_multiplier >= 1
                          ? "+"
                          : ""}
                        {(
                          (analysis.coach_analysis.coach_multiplier - 1) *
                          100
                        ).toFixed(1)}
                        % performance boost
                      </Text>
                    </View>
                    {analysis.coach_analysis.qb_familiarity && (
                      <View
                        style={[
                          styles.coachBadge,
                          { backgroundColor: isDark ? "#fbbf24" : "#d97706" },
                        ]}
                      >
                        <Text
                          style={[
                            styles.coachBadgeText,
                            { color: isDark ? "#000000" : "#ffffff" },
                          ]}
                        >
                          Coached QB before
                        </Text>
                      </View>
                    )}
                  </View>
                </>
              )}
            </View>
          )}

          <View
            style={[
              styles.card,
              { backgroundColor: c.card, borderColor: c.border },
            ]}
          >
            <Text style={[styles.cardTitle, { color: c.text }]}>
              Player Projections
            </Text>
            <View
              style={[
                styles.playerCard,
                { borderColor: c.border, marginBottom: 4 },
              ]}
            >
              <View style={styles.playerHeader}>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.cardTitle, { color: c.text }]}>
                    Legend
                  </Text>
                  <Text
                    style={[
                      styles.playerName,
                      { color: c.subtext, fontStyle: "italic" },
                    ]}
                  >
                    Player Name - NFL Team
                  </Text>
                </View>
                <View
                  style={[
                    styles.posBadge,
                    {
                      backgroundColor: isDark ? "#60a5fa" : "#1d4ed8",
                      marginTop: 25,
                    },
                  ]}
                >
                  <Text
                    style={[
                      styles.posText,
                      { color: isDark ? "#000000" : "#ffffff" },
                    ]}
                  >
                    POS
                  </Text>
                </View>
              </View>
              <View style={styles.statRow}>
                <Text
                  style={[
                    styles.statLabel,
                    { color: c.subtext, fontStyle: "italic" },
                  ]}
                >
                  Stat
                </Text>
                <Text
                  style={[
                    styles.statValue,
                    { color: c.subtext, fontStyle: "italic" },
                  ]}
                >
                  1260
                </Text>
                <Text
                  style={[
                    styles.statRange,
                    { color: c.subtext, fontStyle: "italic" },
                  ]}
                >
                  1072-1446
                </Text>
              </View>
              <View style={{ flexDirection: "row", marginTop: 2 }}>
                <View style={{ width: 80 }} />
                <Text
                  style={{
                    width: 50,
                    fontSize: 10,
                    color: c.subtext,
                    fontStyle: "italic",
                    textAlign: "right",
                  }}
                >
                  ↑ avg
                </Text>
                <Text
                  style={{
                    fontSize: 10,
                    color: c.subtext,
                    fontStyle: "italic",
                    marginLeft: 8,
                  }}
                >
                  ↑ P10-P90 (80% of seasons)
                </Text>
              </View>
            </View>
            {(Array.isArray(analysis.player_projections)
              ? analysis.player_projections
              : Object.entries(analysis.player_projections as Record<string, PlayerProjection>).map(([name, p]) => ({ ...p, name }))
            ).map((proj) => (
              <View
                key={proj.name}
                style={[styles.playerCard, { borderColor: c.border }]}
              >
                <View style={styles.playerHeader}>
                  <Text style={[styles.playerName, { color: c.text }]}>
                    {proj.name}
                    {proj.nfl_team ? ` - ${proj.nfl_team}` : ""}
                  </Text>
                  <View
                    style={[
                      styles.posBadge,
                      {
                        backgroundColor:
                          POS_COLORS[proj.position]?.bg ?? c.accentLight,
                      },
                    ]}
                  >
                    <Text
                      style={[
                        styles.posText,
                        { color: POS_COLORS[proj.position]?.text ?? c.accent },
                      ]}
                    >
                      {proj.position}
                    </Text>
                  </View>
                </View>
                {Object.entries(proj.stats).map(([stat, vals]) => {
                  const isPct = stat === "fg_pct";
                  const fmt = (v: number) => isPct ? `${v.toFixed(1)}%` : String(v);
                  return (
                    <View key={stat} style={styles.statRow}>
                      <Text style={[styles.statLabel, { color: c.subtext }]}>
                        {STAT_LABELS[stat] ?? stat}
                      </Text>
                      <Text style={[styles.statValue, { color: c.text }]}>
                        {fmt(vals.projected_total)}
                      </Text>
                      <Text style={[styles.statRange, { color: c.subtext }]}>
                        {fmt(vals.floor)}-{fmt(vals.ceiling)}
                      </Text>
                    </View>
                  );
                })}
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
  coachName: {
    fontSize: 20,
    fontWeight: "700",
  },
  coachMeta: {
    fontSize: 13,
    lineHeight: 18,
  },
  coachRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 4,
  },
  coachBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  coachBadgeText: {
    fontSize: 13,
    fontWeight: "600",
  },
  legend: {
    borderRadius: 8,
    borderWidth: 1,
    padding: 10,
    gap: 4,
    marginBottom: 4,
  },
  legendTitle: {
    fontSize: 12,
    fontWeight: "700",
    marginBottom: 2,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  legendRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  legendBold: {
    fontSize: 13,
    fontWeight: "700",
    width: 40,
    textAlign: "right",
  },
  legendRange: {
    fontSize: 12,
    width: 80,
    textAlign: "right",
  },
  legendDesc: {
    fontSize: 12,
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
