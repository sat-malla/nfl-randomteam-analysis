import { assignLbLabels } from "@/utils/defense-rendering";
import {
  Text,
  ScrollView,
  TouchableOpacity,
  View,
  Platform,
  ActivityIndicator,
  Animated,
  Modal,
  KeyboardAvoidingView,
  TextInput,
  FlatList,
} from "react-native";
import { useColorScheme } from "react-native";
import { StyleSheet } from "react-native";
import PickerModal, { PickerTrigger } from "@/components/PickerModal";
import {
  FormControl,
  FormControlLabel,
  FormControlLabelText,
} from "@/components/ui/form-control";
import Svg, { Path } from "react-native-svg";
import { VStack } from "@/components/ui/vstack";
import { useState, useEffect, useRef } from "react";
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
  team?: string;
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
  points_for?: number;
  points_against?: number;
  points_per_game?: number;
};

type Team = {
  id: string;
  team_name: string;
  defense_type: string;
};

const STAT_LABELS: Record<string, string> = {
  passing_yards: "Pass Yds",
  passing_tds: "Pass TDs",
  passing_interceptions: "INTs",
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
  def_pass_defended: "Passes Defended",
  fg_made: "FG Made",
  fg_att: "FG Att",
  fg_pct: "FG%",
  punt_attempts_season: "Punts",
  punt_yards_season: "Punt Yds",
  punt_return_yards: "PR Yds",
  kickoff_return_yards: "KR Yds",
  kickoff_returns: "KR",
  punt_returns: "PR",
};

const POS_COLORS_LIGHT: Record<string, { bg: string; text: string }> = {
  QB: { bg: "#dc2626", text: "#ffffff" },
  RB: { bg: "#1f55ed", text: "#ffffff" },
  WR: { bg: "#059669", text: "#ffffff" },
  TE: { bg: "#d97706", text: "#ffffff" },
  DE: { bg: "#ea580c", text: "#ffffff" },
  DT: { bg: "#ea580c", text: "#ffffff" },
  NT: { bg: "#ea580c", text: "#ffffff" },
  DL: { bg: "#ea580c", text: "#ffffff" },
  LB: { bg: "#db2777", text: "#ffffff" },
  ILB: { bg: "#db2777", text: "#ffffff" },
  OLB: { bg: "#db2777", text: "#ffffff" },
  MLB: { bg: "#db2777", text: "#ffffff" },
  SLB: { bg: "#db2777", text: "#ffffff" },
  WLB: { bg: "#db2777", text: "#ffffff" },
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
  RS: { bg: "#4d2325", text: "#ffffff" },
};

const POS_COLORS_DARK: Record<string, { bg: string; text: string }> = {
  QB: { bg: "#f87171", text: "#000000" },
  RB: { bg: "#6b8ef5", text: "#000000" },
  WR: { bg: "#34d399", text: "#000000" },
  TE: { bg: "#fbbf24", text: "#000000" },
  DE: { bg: "#fb923c", text: "#000000" },
  DT: { bg: "#fb923c", text: "#000000" },
  NT: { bg: "#fb923c", text: "#000000" },
  DL: { bg: "#fb923c", text: "#000000" },
  LB: { bg: "#f472b6", text: "#000000" },
  ILB: { bg: "#f472b6", text: "#000000" },
  OLB: { bg: "#f472b6", text: "#000000" },
  MLB: { bg: "#f472b6", text: "#000000" },
  SLB: { bg: "#f472b6", text: "#000000" },
  WLB: { bg: "#f472b6", text: "#000000" },
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
  RS: { bg: "#f87171", text: "#000000" },
};

const OFF_POSITIONS = new Set(["QB", "RB", "FB", "WR", "TE"]);
const DEF_POSITIONS = new Set(["DE", "DT", "NT", "DL", "LB", "OLB", "ILB", "MLB", "SLB", "WLB", "CB", "FS", "SS", "S", "SAF", "DB", "Nickel", "Dime"]);

function aggregateTeamStats(projections: PlayerProjection[]) {
  let scrimmageYards = 0;
  let offTDs = 0;
  let sacks = 0;
  let defINTs = 0;

  for (const p of projections) {
    const s = p.stats;
    if (OFF_POSITIONS.has(p.position)) {
      scrimmageYards += (s.rushing_yards?.projected_total ?? 0) + (s.receiving_yards?.projected_total ?? 0);
      offTDs += (s.rushing_tds?.projected_total ?? 0) + (s.receiving_tds?.projected_total ?? 0) + (s.passing_tds?.projected_total ?? 0);
    }
    if (DEF_POSITIONS.has(p.position)) {
      sacks += s.def_sacks?.projected_total ?? 0;
      defINTs += s.def_interceptions?.projected_total ?? 0;
    }
  }

  return { scrimmageYards: Math.round(scrimmageYards), offTDs: Math.round(offTDs), sacks: Math.round(sacks), defINTs: Math.round(defINTs) };
}

type TeamStatsGridProps = {
  analysis: AnalysisResult;
  c: Record<string, string>;
  isDark: boolean;
};

type LeaderCategory = {
  label: string;
  stat: string;
  excludePos?: Set<string>;
  includePos?: Set<string>;
  unit?: string;
};

const LEADER_CATEGORIES: LeaderCategory[] = [
  { label: "Total TD Leader", stat: "total_tds", excludePos: new Set(["QB"]), unit: "TDs" },
  { label: "Rushing TD Leader", stat: "rushing_tds", unit: "TDs" },
  { label: "Receiving TD Leader", stat: "receiving_tds", unit: "TDs" },
  { label: "Scrimmage Yds Leader", stat: "scrimmage_yards", unit: "Yards" },
  { label: "Rushing Yds Leader", stat: "rushing_yards", unit: "Yards" },
  { label: "Receiving Yds Leader", stat: "receiving_yards", unit: "Yards" },
  { label: "Tackles Leader", stat: "def_tackles_solo", includePos: DEF_POSITIONS, unit: "Tackles" },
  { label: "Sacks Leader", stat: "def_sacks", includePos: DEF_POSITIONS, unit: "Sacks" },
  { label: "Passes Def. Leader", stat: "def_pass_defended", includePos: DEF_POSITIONS, unit: "PD" },
  { label: "Interceptions Leader", stat: "def_interceptions", includePos: DEF_POSITIONS, unit: "INTs" },
];

function getPlayerStatValue(p: PlayerProjection, stat: string): number {
  if (stat === "total_tds") {
    return (p.stats.rushing_tds?.projected_total ?? 0) + (p.stats.receiving_tds?.projected_total ?? 0);
  }
  if (stat === "scrimmage_yards") {
    return (p.stats.rushing_yards?.projected_total ?? 0) + (p.stats.receiving_yards?.projected_total ?? 0);
  }
  return p.stats[stat]?.projected_total ?? 0;
}

function findLeader(projections: PlayerProjection[], cat: LeaderCategory): { name: string; value: number; position: string; nfl_team: string } | null {
  let best: { name: string; value: number; position: string; nfl_team: string } | null = null;
  for (const p of projections) {
    if (cat.excludePos && cat.excludePos.has(p.position)) continue;
    if (cat.includePos && !cat.includePos.has(p.position)) continue;
    const val = getPlayerStatValue(p, cat.stat);
    if (val > 0 && (best === null || val > best.value)) {
      best = { name: p.name, value: val, position: p.position, nfl_team: p.nfl_team };
    }
  }
  return best;
}

function shortName(full: string): string {
  const parts = full.trim().split(" ");
  if (parts.length < 2) return full;
  return `${parts[0][0]}. ${parts.slice(1).join(" ")}`;
}

type TeamLeadersGridProps = {
  analysis: AnalysisResult;
  c: Record<string, string>;
  isDark: boolean;
};

function TeamLeadersGrid({ analysis, c, isDark }: TeamLeadersGridProps) {
  const projections = Array.isArray(analysis.player_projections)
    ? analysis.player_projections
    : Object.entries(analysis.player_projections as Record<string, PlayerProjection>).map(([name, p]) => ({ ...p, name }));

  const POS_COLORS = isDark ? POS_COLORS_DARK : POS_COLORS_LIGHT;
  const { bg, text } = isDark ? TILE_DARK : TILE_LIGHT;

  return (
    <View style={[{ width: "100%", borderRadius: 14, borderWidth: 1, padding: 16, marginBottom: 20, gap: 12 }, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
      <Text style={{ fontSize: 18, fontFamily: "Montserrat_700Bold", marginBottom: 4, color: c.text }}>Team Leaders</Text>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
        {LEADER_CATEGORIES.map((cat) => {
          const leader = findLeader(projections, cat);
          const posBadge = leader ? POS_COLORS[leader.position] : null;
          return (
            <View
              key={cat.label}
              style={{
                width: "47%",
                flexGrow: 1,
                backgroundColor: bg,
                borderRadius: 10,
                padding: 12,
              }}
            >
              <Text style={{ fontSize: 11, fontFamily: "Montserrat_700Bold", color: text, marginBottom: 6, opacity: 0.8 }}>
                {cat.label}
              </Text>
              {leader ? (
                <>
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 3 }}>
                    {posBadge && (
                      <View style={{ backgroundColor: posBadge.bg, borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2, borderWidth: 1, borderColor: text }}>
                        <Text style={{ fontSize: 10, fontFamily: "Montserrat_700Bold", color: posBadge.text }}>{leader.position}</Text>
                      </View>
                    )}
                    <Text style={{ fontSize: 16, fontFamily: "Montserrat_700Bold", color: text, flexShrink: 1 }} numberOfLines={1}>
                      {shortName(leader.name)}
                    </Text>
                  </View>
                  <Text style={{ fontSize: 13, fontFamily: "Montserrat_700Bold", color: text, opacity: 0.85 }}>
                    {leader.value} {cat.unit}
                  </Text>
                  {leader.nfl_team ? (
                    <Text style={{ fontSize: 10, color: text, opacity: 0.8, marginTop: 4 }} numberOfLines={1}>
                      {leader.nfl_team}
                    </Text>
                  ) : null}
                </>
              ) : (
                <Text style={{ fontSize: 13, color: text, opacity: 0.6 }}>—</Text>
              )}
            </View>
          );
        })}
      </View>
    </View>
  );
}

const TILE_LIGHT = { bg: "#1d4ed8", text: "#ffffff" };
const TILE_DARK = { bg: "#60a5fa", text: "#000000" };

function TeamStatsGrid({ analysis, c, isDark }: TeamStatsGridProps) {
  const projections = Array.isArray(analysis.player_projections)
    ? analysis.player_projections
    : Object.entries(analysis.player_projections as Record<string, PlayerProjection>).map(([name, p]) => ({ ...p, name }));

  const { scrimmageYards, offTDs, sacks, defINTs } = aggregateTeamStats(projections);

  const cells = [
    { label: "Points For", value: analysis.points_for != null ? String(analysis.points_for) : "—", sub: "season total" },
    { label: "Points Against", value: analysis.points_against != null ? String(analysis.points_against) : "—", sub: "season total" },
    { label: "Points / Game", value: analysis.points_per_game != null ? String(analysis.points_per_game) : "—", sub: "avg per game" },
    { label: "Scrimmage Yds", value: String(scrimmageYards), sub: "season total" },
    { label: "Offensive TDs", value: String(offTDs), sub: "season total" },
    { label: "Team Sacks", value: String(sacks), sub: "season total" },
    { label: "Interceptions", value: String(defINTs), sub: "season total" },
  ];

  const { bg, text } = isDark ? TILE_DARK : TILE_LIGHT;

  return (
    <View style={[{ width: "100%", borderRadius: 14, borderWidth: 1, padding: 16, marginBottom: 20, gap: 12 }, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
      <Text style={{ fontSize: 18, fontFamily: "Montserrat_700Bold", marginBottom: 4, color: c.text }}>Team Statistics</Text>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
        {cells.map((cell) => (
          <View
            key={cell.label}
            style={{
              width: "30%",
              flexGrow: 1,
              backgroundColor: bg,
              borderRadius: 10,
              padding: 12,
              alignItems: "center",
            }}
          >
            <Text style={{ fontSize: 26, fontFamily: "Montserrat_700Bold", color: text, lineHeight: 30 }}>{cell.value}</Text>
            <Text style={{ fontSize: 11, fontFamily: "Montserrat_700Bold", color: text, marginTop: 4, textAlign: "center", opacity: 0.9 }}>{cell.label}</Text>
            <Text style={{ fontSize: 10, fontFamily: "Montserrat_400Regular", color: text, marginTop: 1, opacity: 0.65 }}>{cell.sub}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

type ChatMessage = {
  id: string;
  role: "ai" | "user";
  text: string;
};

type AIChatPanelProps = {
  visible: boolean;
  onClose: () => void;
  teamId: string;
  analysis: AnalysisResult;
  c: Record<string, string>;
  isDark: boolean;
};

function AIChatPanel({ visible, onClose, teamId, analysis, c, isDark }: AIChatPanelProps) {
  const INITIAL_MSG: ChatMessage = {
    id: "init",
    role: "ai",
    text: "Press Summarize to get an AI breakdown of your team's analysis, and ask questions about your team and its analysis.",
  };

  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MSG]);
  const [input, setInput] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const flatRef = useRef<FlatList>(null);

  useEffect(() => {
    if (visible) {
      setMessages([INITIAL_MSG]);
      setInput("");
    }
  }, [visible, teamId]);

  const sendToAI = async (userText: string) => {
    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: "user", text: userText };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setAiLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/analysis/summarize/${teamId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText, analysis }),
      });
      const data = await res.json();
      const reply = data.summary ?? data.message ?? "No response from AI.";
      setMessages((prev) => [...prev, { id: `a-${Date.now()}`, role: "ai", text: reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: `a-err-${Date.now()}`, role: "ai", text: "Couldn't reach the AI backend. Make sure it's running." },
      ]);
    } finally {
      setAiLoading(false);
      setTimeout(() => flatRef.current?.scrollToEnd({ animated: true }), 100);
    }
  };

  const panelBg = isDark ? "#0d1f2d" : "#ffffff";
  const inputBg = isDark ? "#132130" : "#f1f5f9";
  const aiBubble = isDark ? "#1e3a52" : "#dbeafe";
  const aiBubbleText = isDark ? "#edf5ff" : "#02080f";
  const userBubble = isDark ? "#1d4ed8" : "#1d4ed8";

  return (
    <Modal visible={visible} transparent animationType="none" onRequestClose={onClose}>
      <View style={aiStyles.overlay} pointerEvents="box-none">
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          style={aiStyles.kvWrapper}
          pointerEvents="box-none"
        >
          <View style={[aiStyles.panel, { backgroundColor: panelBg, borderColor: c.border, shadowColor: isDark ? "#000" : "#003" }]}>
            <View style={[aiStyles.panelHeader, { borderBottomColor: c.border }]}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                <View style={aiStyles.aiDot} />
                <Text style={{ fontSize: 15, fontFamily: "Montserrat_700Bold", color: c.text }}>AI Analysis</Text>
              </View>
              <TouchableOpacity onPress={onClose} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>
                <Text style={{ fontSize: 20, color: c.subtext, lineHeight: 24 }}>×</Text>
              </TouchableOpacity>
            </View>

            <FlatList
              ref={flatRef}
              data={messages}
              keyExtractor={(m) => m.id}
              style={{ flex: 1 }}
              contentContainerStyle={{ padding: 12, gap: 8 }}
              onContentSizeChange={() => flatRef.current?.scrollToEnd({ animated: false })}
              renderItem={({ item }) => (
                <View
                  style={[
                    aiStyles.bubble,
                    item.role === "ai"
                      ? { alignSelf: "flex-start", backgroundColor: aiBubble }
                      : { alignSelf: "flex-end", backgroundColor: userBubble },
                  ]}
                >
                  <Text style={{ fontSize: 13, fontFamily: "Montserrat_400Regular", color: item.role === "ai" ? aiBubbleText : "#ffffff", lineHeight: 18 }}>
                    {item.text}
                  </Text>
                </View>
              )}
              ListFooterComponent={
                aiLoading ? (
                  <View style={[aiStyles.bubble, { alignSelf: "flex-start", backgroundColor: aiBubble }]}>
                    <ActivityIndicator size="small" color={c.subtext} />
                  </View>
                ) : null
              }
            />

            {messages.length === 1 && !aiLoading && (
              <View style={{ paddingHorizontal: 12, paddingBottom: 8 }}>
                <TouchableOpacity
                  style={[aiStyles.summarizeBtn, { backgroundColor: isDark ? "#1d4ed8" : "#1d4ed8" }]}
                  onPress={() => sendToAI("Summarize this team's analysis")}
                >
                  <Text style={{ color: "#ffffff", fontFamily: "Montserrat_700Bold", fontSize: 14 }}>✦ Summarize</Text>
                </TouchableOpacity>
              </View>
            )}

            <View style={[aiStyles.inputRow, { borderTopColor: c.border, backgroundColor: panelBg }]}>
              <TextInput
                style={[aiStyles.textInput, { backgroundColor: inputBg, color: c.text }]}
                placeholder="Ask about your team..."
                placeholderTextColor={c.subtext}
                value={input}
                onChangeText={setInput}
                returnKeyType="send"
                onSubmitEditing={() => { if (input.trim()) sendToAI(input.trim()); }}
                editable={!aiLoading}
              />
              <TouchableOpacity
                style={[aiStyles.sendBtn, { backgroundColor: input.trim() && !aiLoading ? "#1d4ed8" : "#9ca3af" }]}
                onPress={() => { if (input.trim() && !aiLoading) sendToAI(input.trim()); }}
                disabled={!input.trim() || aiLoading}
              >
                <Svg width={18} height={18} viewBox="0 0 24 24" fill="none">
                  <Path d="M12 19V5" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  <Path d="M5 12L12 5L19 12" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                </Svg>
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </View>
    </Modal>
  );
}

const AnalyzeTeam = () => {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";
  const POS_COLORS = isDark ? POS_COLORS_DARK : POS_COLORS_LIGHT;

  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<string>("");
  const [selectedTeamDefenseType, setSelectedTeamDefenseType] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [hasSaved, setHasSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [teamPickerOpen, setTeamPickerOpen] = useState(false);
  const fabOpacity = useRef(new Animated.Value(0)).current;

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
    if (hasSaved && analysis) {
      Animated.timing(fabOpacity, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }).start();
    } else {
      fabOpacity.setValue(0);
    }
  }, [hasSaved, analysis]);

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
              (team: { id: string; team_name: string; defense_type: string }) => ({
                id: team.id,
                team_name: team.team_name,
                defense_type: team.defense_type,
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
    setSelectedTeamDefenseType(team.defense_type ?? "");
    setAnalysis(null);
    setHasSaved(false);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/api/analysis/${team.id}`);
      const result = await res.json();
      if (res.ok && result.status === "Success") {
        const data = result.data as AnalysisResult;
        const projs = Array.isArray(data.player_projections) ? data.player_projections : Object.entries(data.player_projections as Record<string, PlayerProjection>).map(([name, p]) => ({ ...p, name }));
        setAnalysis({ ...data, player_projections: assignLbLabels(projs, team.defense_type) });
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
        const data = result as AnalysisResult;
        const projs = Array.isArray(data.player_projections) ? data.player_projections : Object.entries(data.player_projections as Record<string, PlayerProjection>).map(([name, p]) => ({ ...p, name }));
        setAnalysis({ ...data, player_projections: assignLbLabels(projs, selectedTeamDefenseType) });
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
    shadow: isDark ? "rgba(250,250,250,0.8) 0px 3px 8px" : "rgba(0,0,0,0.24) 0px 3px 8px",
  };

  const winColor =
    analysis && analysis.projected_wins >= 9
      ? c.green
      : analysis && analysis.projected_wins >= 6
        ? c.amber
        : c.red;

  return (
    <View style={{ flex: 1, backgroundColor: c.bg }}>
    <ScrollView
      style={{ flex: 1 }}
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
          { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow },
        ]}
      >
        <FormControl size="lg">
          <VStack space="md">
            <FormControlLabel>
              <FormControlLabelText style={{ color: c.text, fontFamily: "Montserrat_700Bold" }}>
                Choose Team
              </FormControlLabelText>
            </FormControlLabel>
            <PickerTrigger value={teams.find(t => t.id === selectedTeamId)?.team_name ?? ""} placeholder="Select a team" onPress={() => setTeamPickerOpen(true)} borderColor={c.border} textColor={c.text} placeholderColor={c.subtext} />
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
              { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow },
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
                    backgroundColor: isDark ? "#4ade80" : "#16a34a",
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
                    backgroundColor: isDark ? "#f87171" : "#dc2626",
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

          <TeamStatsGrid analysis={analysis} c={c} isDark={isDark} />
          <TeamLeadersGrid analysis={analysis} c={c} isDark={isDark} />

          {analysis.coach_analysis && analysis.coach_analysis.coach && (
            <View
              style={[
                styles.card,
                { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow },
              ]}
            >
              <Text style={[styles.cardTitle, { color: c.text }]}>
                Coach Impact
              </Text>
              <Text style={[styles.coachName, { color: c.text }]}>
                {analysis.coach_analysis.coach}
                {analysis.coach_analysis.team ? (
                  <Text style={[styles.coachMeta, { color: c.subtext }]}>{` (${analysis.coach_analysis.team})`}</Text>
                ) : null}
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
              { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow },
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

          <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
            <Text style={[styles.cardTitle, { color: c.text }]}>Position Legend</Text>
            {[
              { label: "Offense", entries: [
                ["QB", "Quarterback"], ["RB", "Running Back"],
                ["WR", "Wide Receiver"], ["TE", "Tight End"],
              ]},
              { label: "Defensive Line", entries: [
                ["DE", "Defensive End"], ["DT", "Defensive Tackle"], ["NT", "Nose Tackle"],
              ]},
              { label: "Linebackers", entries: [
                ["SLB", "Strong-side LB"], ["MLB", "Middle Linebacker"],
                ["WLB", "Weak-side LB"], ["OLB", "Outside Linebacker"],
                ["ILB", "Inside Linebacker"],
              ]},
              { label: "Defensive Backs", entries: [
                ["CB", "Cornerback"], ["FS", "Free Safety"],
                ["SS", "Strong Safety"], ["S", "Safety"],
              ]},
              { label: "Special Teams", entries: [
                ["K", "Kicker"], ["P", "Punter"],
                ["RS", "Return Specialist"],
              ]},
            ].map((group) => (
              <View key={group.label} style={{ marginBottom: 10 }}>
                <Text style={{ fontSize: 13, fontFamily: "Montserrat_700Bold", color: c.subtext, marginBottom: 6 }}>
                  {group.label}
                </Text>
                <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
                  {group.entries.map(([abbr, name]) => (
                    <View key={abbr} style={{ flexDirection: "row", alignItems: "center", width: "47%" }}>
                      <View style={{ backgroundColor: POS_COLORS[abbr]?.bg ?? c.accentLight, borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2, marginRight: 6, minWidth: 34, alignItems: "center" }}>
                        <Text style={{ fontSize: 11, fontFamily: "Montserrat_700Bold", color: POS_COLORS[abbr]?.text ?? c.accent }}>{abbr}</Text>
                      </View>
                      <Text style={{ fontSize: 12, fontFamily: "Montserrat_400Regular", color: c.subtext, flexShrink: 1 }}>{name}</Text>
                    </View>
                  ))}
                </View>
              </View>
            ))}
          </View>
        </>
      )}
    </ScrollView>

    <Animated.View style={[aiStyles.fab, { opacity: fabOpacity }]} pointerEvents={hasSaved && analysis ? "auto" : "none"}>
      <TouchableOpacity
        style={[aiStyles.fabBtn, { backgroundColor: isDark ? "#1d4ed8" : "#1d4ed8", shadowColor: isDark ? "#000" : "#003" }]}
        onPress={() => setAiPanelOpen(true)}
        activeOpacity={0.85}
      >
        <Text style={{ fontSize: 20 }}>✦</Text>
        <Text style={{ color: "#ffffff", fontFamily: "Montserrat_700Bold", fontSize: 12, marginTop: 1 }}>AI</Text>
      </TouchableOpacity>
    </Animated.View>

    {analysis && (
      <AIChatPanel
        visible={aiPanelOpen}
        onClose={() => setAiPanelOpen(false)}
        teamId={selectedTeamId}
        analysis={analysis}
        c={c}
        isDark={isDark}
      />
    )}
    <PickerModal visible={teamPickerOpen} onClose={() => setTeamPickerOpen(false)} title="Choose Team" items={teams.map(t => ({ label: t.team_name, value: t.team_name }))} selectedValue={teams.find(t => t.id === selectedTeamId)?.team_name ?? ""} onSelect={handleSelectTeam} />
    </View>
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
    fontFamily: "Montserrat_700Bold",
    textAlign: "center",
  },
  subtitle: {
    fontSize: 15,
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
    marginBottom: 20,
    gap: 12,
  },
  cardTitle: {
    fontSize: 18,
    fontFamily: "Montserrat_700Bold",
    marginBottom: 4,
  },
  button: {
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 4,
  },
  buttonText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 16,
  },
  loadingNote: {
    fontSize: 13,
    fontFamily: "Montserrat_400Regular",
    textAlign: "center",
    marginTop: -4,
  },
  error: {
    fontSize: 14,
    fontFamily: "Montserrat_400Regular",
    textAlign: "center",
  },
  winsRow: {
    alignItems: "center",
    marginVertical: 4,
  },
  winsNumber: {
    fontSize: 64,
    fontFamily: "Montserrat_700Bold",
    lineHeight: 70,
  },
  winsLabel: {
    fontSize: 16,
    fontFamily: "Montserrat_400Regular",
    marginTop: 2,
  },
  winsRange: {
    textAlign: "center",
    fontFamily: "Montserrat_400Regular",
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
    fontFamily: "Montserrat_700Bold",
  },
  probLabel: {
    fontSize: 12,
    fontFamily: "Montserrat_400Regular",
    marginTop: 2,
    textAlign: "center",
  },
  coachName: {
    fontSize: 20,
    fontFamily: "Montserrat_700Bold",
  },
  coachMeta: {
    fontSize: 13,
    fontFamily: "Montserrat_400Regular",
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
    fontFamily: "Montserrat_700Bold",
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
    fontFamily: "Montserrat_700Bold",
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
    fontFamily: "Montserrat_700Bold",
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
    fontFamily: "Montserrat_700Bold",
    flex: 1,
  },
  posBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  posText: {
    fontSize: 12,
    fontFamily: "Montserrat_700Bold",
  },
  statRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  statLabel: {
    fontSize: 13,
    fontFamily: "Montserrat_400Regular",
    width: 80,
  },
  statValue: {
    fontSize: 13,
    fontFamily: "Montserrat_700Bold",
    width: 50,
    textAlign: "right",
  },
  statRange: {
    fontSize: 12,
    fontFamily: "Montserrat_400Regular",
    marginLeft: 8,
  },
});

const aiStyles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    alignItems: "flex-end",
  },
  kvWrapper: {
    width: "100%",
    alignItems: "flex-end",
    justifyContent: "flex-end",
  },
  panel: {
    width: "92%",
    maxWidth: 380,
    height: 420,
    borderRadius: 18,
    borderWidth: 1,
    marginBottom: 100,
    marginRight: 16,
    overflow: "hidden",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.25,
    shadowRadius: 16,
    elevation: 12,
  },
  panelHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  aiDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#22c55e",
  },
  bubble: {
    maxWidth: "82%",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 14,
    marginBottom: 4,
  },
  summarizeBtn: {
    paddingVertical: 10,
    paddingHorizontal: 18,
    borderRadius: 10,
    alignItems: "center",
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 10,
    borderTopWidth: 1,
    gap: 8,
  },
  textInput: {
    flex: 1,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 11,
    fontSize: 15,
    fontFamily: "Montserrat_400Regular",
  },
  sendBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 3,
  },
  fab: {
    position: "absolute",
    bottom: 28,
    right: 20,
  },
  fabBtn: {
    width: 58,
    height: 58,
    borderRadius: 29,
    alignItems: "center",
    justifyContent: "center",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
});

export default AnalyzeTeam;
