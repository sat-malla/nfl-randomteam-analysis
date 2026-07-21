import {
  Text,
  ScrollView,
  TouchableOpacity,
  View,
  Platform,
  useColorScheme,
  StyleSheet,
  Dimensions,
  ActivityIndicator,
} from "react-native";
import Svg, {
  Rect,
  Line,
  Text as SvgText,
} from "react-native-svg";
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

type Player = {
  name: string;
  position: string;
  nfl_team: string;
};

type Team = {
  id: string;
  team_name: string;
  head_coach: string;
  offense_type: string;
  defense_type: string;
  players: Player[];
};

type TeamSummary = {
  id: string;
  team_name: string;
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

const OFFENSE_POSITIONS = new Set(["QB", "RB", "FB", "WR", "TE", "OT", "G", "C", "OL", "K", "P", "LS", "RS"]);
const DEFENSE_POSITIONS = new Set(["DE", "DT", "NT", "DL", "LB", "OLB", "ILB", "MLB", "CB", "S", "FS", "SS", "DB", "SAF", "Nickel", "Dime"]);

const DEFENSE_ROW_ORDER = [
  ["DE", "DT", "NT", "DL", "OLB"],
  ["LB", "ILB", "MLB"],
  ["CB", "Nickel", "Dime", "S", "FS", "SS", "DB", "SAF"],
];

const OFFENSE_ROW_ORDER = [
  ["OT", "G", "C", "OL"],
  ["QB", "RB", "FB", "TE"],
  ["WR"],
  ["K", "P", "LS", "RS"],
];

function groupPlayersByRows(
  players: Player[],
  rowOrder: string[][]
): Player[][] {
  const rows: Player[][] = [];
  const used = new Set<string>();

  for (const posGroup of rowOrder) {
    const row = players.filter(
      (p) => posGroup.includes(p.position) && !used.has(p.name)
    );
    row.forEach((p) => used.add(p.name));
    if (row.length > 0) rows.push(row);
  }

  const leftover = players.filter((p) => !used.has(p.name));
  if (leftover.length > 0) rows.push(leftover);

  return rows;
}

function FootballField({ width, height }: { width: number; height: number }) {
  // Pure playing field — no endzones, just 10 yards segments (defense goal line to offense goal line)
  const totalSegments = 10;
  const segH = height / totalSegments;
  const stripeColors = ["#1a6b2a", "#1e7a30"];

  // 9 yard lines at segment boundaries (10, 20, 30, 40, 50, 40, 30, 20, 10)
  const yardLabels = ["10", "20", "30", "40", "50", "40", "30", "20", "10"];
  const hashInset = width * 0.28;
  const hashLen = 7;

  return (
    <Svg width={width} height={height} style={StyleSheet.absoluteFillObject} pointerEvents="none">
      {/* Base */}
      <Rect x={0} y={0} width={width} height={height} fill="#1a6b2a" />

      {/* Alternating stripes */}
      {Array.from({ length: totalSegments }).map((_, i) => (
        <Rect key={`s${i}`} x={0} y={i * segH} width={width} height={segH} fill={stripeColors[i % 2]} />
      ))}

      {/* Yard lines */}
      {yardLabels.map((label, i) => {
        const y = (i + 1) * segH;
        const is50 = label === "50";
        return (
          <Line key={`yl${i}`} x1={0} y1={y} x2={width} y2={y}
            stroke="#ffffff" strokeWidth={is50 ? 2.5 : 1.2} opacity={is50 ? 0.9 : 0.55} />
        );
      })}

      {/* Outer boundary */}
      <Rect x={1} y={1} width={width - 2} height={height - 2} fill="none" stroke="#ffffff" strokeWidth={2} opacity={0.75} />

      {/* Hash marks */}
      {yardLabels.map((_, i) => {
        const y = (i + 1) * segH;
        return [hashInset, width - hashInset].map((x, j) => (
          <Line key={`h${i}-${j}`} x1={x} y1={y - hashLen / 2} x2={x} y2={y + hashLen / 2}
            stroke="#ffffff" strokeWidth={1.5} opacity={0.65} />
        ));
      })}

      {/* Yard number labels — left and right sides */}
      {yardLabels.map((label, i) => {
        const y = (i + 1) * segH - 4;
        const is50 = label === "50";
        return [width * 0.08, width * 0.92].map((x, j) => (
          <SvgText key={`lbl${i}-${j}`} x={x} y={y} textAnchor="middle"
            fill="#ffffff" fontSize={is50 ? 13 : 11} fontWeight="bold" opacity={is50 ? 0.85 : 0.55}>
            {label}
          </SvgText>
        ));
      })}
    </Svg>
  );
}

function PlayerCard({
  player,
  posColors,
}: {
  player: Player;
  posColors: Record<string, { bg: string; text: string }>;
}) {
  const color = posColors[player.position] ?? { bg: "#334155", text: "#ffffff" };
  const shortTeam = player.nfl_team
    .split(" ")
    .slice(-1)[0]
    .slice(0, 10);
  const nameParts = player.name.trim().split(" ");
  const displayName =
    nameParts.length >= 2
      ? `${nameParts[0][0]}. ${nameParts.slice(1).join(" ")}`
      : player.name;

  return (
    <View style={styles.playerCard}>
      <View style={[styles.posBadge, { backgroundColor: color.bg }]}>
        <Text style={[styles.posText, { color: color.text }]}>
          {player.position}
        </Text>
      </View>
      <Text style={styles.playerName} numberOfLines={1}>
        {displayName}
      </Text>
      <Text style={styles.playerTeam} numberOfLines={1}>
        {shortTeam}
      </Text>
    </View>
  );
}

function FieldView({
  team,
  posColors,
  c,
}: {
  team: Team;
  posColors: Record<string, { bg: string; text: string }>;
  c: Record<string, string>;
}) {
  const { width: screenWidth } = Dimensions.get("window");
  const fieldWidth = screenWidth - 32;
  const fieldHeight = fieldWidth * 1.9;

  const defensePlayers = team.players.filter((p) =>
    DEFENSE_POSITIONS.has(p.position)
  );
  const offensePlayers = team.players.filter((p) =>
    OFFENSE_POSITIONS.has(p.position)
  );

  const defenseRows = groupPlayersByRows(defensePlayers, DEFENSE_ROW_ORDER);
  const offenseRows = groupPlayersByRows(offensePlayers, OFFENSE_ROW_ORDER);
  const halfH = fieldHeight / 2;
  const PADDING = 14;
  const defRowH = defenseRows.length > 0 ? (halfH - PADDING * 2) / defenseRows.length : 0;
  const offRowH = offenseRows.length > 0 ? (halfH - PADDING * 2) / offenseRows.length : 0;

  return (
    <View style={{ width: fieldWidth, marginBottom: 4 }}>
      <Text style={{ textAlign: "center", color: c.subtext, fontWeight: "800", fontSize: 13, letterSpacing: 3, marginBottom: 6 }}>
        DEFENSE
      </Text>

      <View style={[styles.fieldWrapper, { width: fieldWidth, height: fieldHeight }]}>
        <FootballField width={fieldWidth} height={fieldHeight} />

        {defenseRows.map((row, rowIdx) => {
          const y = PADDING + rowIdx * defRowH;
          return (
            <View
              key={`def-row-${rowIdx}`}
              style={{
                position: "absolute",
                top: y,
                left: 0,
                width: fieldWidth,
                height: defRowH,
                flexDirection: "row",
                justifyContent: "center",
                alignItems: "center",
                gap: 4,
              }}
            >
              {row.map((player) => (
                <PlayerCard key={player.name} player={player} posColors={posColors} />
              ))}
            </View>
          );
        })}

        {offenseRows.map((row, rowIdx) => {
          const y = halfH + PADDING + rowIdx * offRowH;
          return (
            <View
              key={`off-row-${rowIdx}`}
              style={{
                position: "absolute",
                top: y,
                left: 0,
                width: fieldWidth,
                height: offRowH,
                flexDirection: "row",
                justifyContent: "center",
                alignItems: "center",
                gap: 4,
              }}
            >
              {row.map((player) => (
                <PlayerCard key={player.name} player={player} posColors={posColors} />
              ))}
            </View>
          );
        })}
      </View>

      <Text style={{ textAlign: "center", color: c.subtext, fontWeight: "800", fontSize: 13, letterSpacing: 3, marginTop: 6 }}>
        OFFENSE
      </Text>
    </View>
  );
}

export default function ViewTeams() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";
  const posColors = isDark ? POS_COLORS_DARK : POS_COLORS_LIGHT;

  const [teamSummaries, setTeamSummaries] = useState<TeamSummary[]>([]);
  const [selectedTeamName, setSelectedTeamName] = useState<string>("");
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [loading, setLoading] = useState(false);

  const c = {
    bg: isDark ? "#132130" : "#edf5ff",
    card: isDark ? "#02080f" : "#ffffff",
    text: isDark ? "#edf5ff" : "#02080f",
    subtext: isDark ? "#a0b4c8" : "#4a5568",
    border: isDark ? "#1e3a52" : "#bfdbfe",
    shadow: isDark ? "rgba(250,250,250,0.8) 0px 3px 8px" : "rgba(0,0,0,0.24) 0px 3px 8px",
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
            setTeamSummaries(
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

  const handleSelectTeam = (teamName: string) => {
    setSelectedTeamName(teamName);
    setSelectedTeam(null);
  };

  const handleViewTeam = async () => {
    const summary = teamSummaries.find((t) => t.team_name === selectedTeamName);
    if (!summary) return;
    setLoading(true);
    setSelectedTeam(null);
    try {
      const res = await fetch(`${API_URL}/api/team/${summary.id}`);
      const result = await res.json();
      if (result.status === "Success" && result.data) {
        setSelectedTeam(result.data);
      }
    } catch (_) {}
    setLoading(false);
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: c.bg }}
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator
    >
      <Text style={[styles.title, { color: c.text }]}>View Generated Teams</Text>
      <Text style={[styles.subtitle, { color: c.subtext }]}>
        Pick one of your generated teams and see the full roster.
      </Text>

      <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
        <FormControl size="lg">
          <VStack space="md">
            <FormControlLabel>
              <FormControlLabelText style={{ color: c.text }}>
                Choose Team
              </FormControlLabelText>
            </FormControlLabel>
            <Select onValueChange={handleSelectTeam} selectedValue={selectedTeamName}>
              <SelectTrigger
                variant="outline"
                size="lg"
                style={{ flexDirection: "row", justifyContent: "space-between" }}
              >
                <SelectInput
                  placeholder="Select a team"
                  style={{ flex: 1, color: c.text }}
                />
                <SelectIcon as={ChevronDownIcon} style={{ color: c.text, marginRight: 8 }} />
              </SelectTrigger>
              <SelectPortal>
                <SelectBackdrop />
                <SelectContent>
                  <SelectDragIndicatorWrapper>
                    <SelectDragIndicator />
                  </SelectDragIndicatorWrapper>
                  {teamSummaries.map((t) => (
                    <SelectItem key={t.id} label={t.team_name} value={t.team_name} />
                  ))}
                </SelectContent>
              </SelectPortal>
            </Select>
          </VStack>
        </FormControl>

        <TouchableOpacity
          style={[
            styles.viewButton,
            { backgroundColor: selectedTeamName && !loading ? (isDark ? "#edf5ff" : "#02080f") : "#9ca3af" },
          ]}
          disabled={!selectedTeamName || loading}
          onPress={handleViewTeam}
        >
          {loading ? (
            <ActivityIndicator color={isDark ? "#02080f" : "#edf5ff"} />
          ) : (
            <Text style={[styles.viewButtonText, { color: isDark ? "#02080f" : "#edf5ff" }]}>
              View Team
            </Text>
          )}
        </TouchableOpacity>
      </View>

      {selectedTeam && !loading && (
        <>
          <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
            <Text style={[styles.teamName, { color: c.text }]}>
              {selectedTeam.team_name}
            </Text>
            {selectedTeam.head_coach ? (
              <Text style={[styles.teamMeta, { color: c.subtext }]}>
                HC: {selectedTeam.head_coach}
              </Text>
            ) : null}
            <View style={styles.schemeRow}>
              {selectedTeam.offense_type ? (
                <View style={[styles.schemeBadge, { backgroundColor: c.border }]}>
                  <Text style={[styles.schemeText, { color: c.text }]}>
                    {selectedTeam.offense_type}
                  </Text>
                </View>
              ) : null}
              {selectedTeam.defense_type ? (
                <View style={[styles.schemeBadge, { backgroundColor: c.border }]}>
                  <Text style={[styles.schemeText, { color: c.text }]}>
                    {selectedTeam.defense_type}
                  </Text>
                </View>
              ) : null}
            </View>
          </View>

          <FieldView team={selectedTeam} posColors={posColors} c={c} />

          <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, marginTop: 16 }]}>
            <Text style={[styles.sectionTitle, { color: c.text }]}>Full Roster</Text>
            {selectedTeam.players.map((player, idx) => (
              <View
                key={`${player.name}-${idx}`}
                style={[styles.rosterRow, { borderColor: c.border }]}
              >
                <View style={[styles.rosterBadge, { backgroundColor: posColors[player.position]?.bg ?? "#334155" }]}>
                  <Text style={[styles.rosterPos, { color: posColors[player.position]?.text ?? "#ffffff" }]}>
                    {player.position}
                  </Text>
                </View>
                <Text style={[styles.rosterName, { color: c.text }]} numberOfLines={1}>
                  {player.name}
                </Text>
                <Text style={[styles.rosterTeam, { color: c.subtext }]} numberOfLines={1}>
                  {player.nfl_team}
                </Text>
              </View>
            ))}
          </View>
        </>
      )}
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
    fontWeight: "bold",
    textAlign: "center",
  },
  subtitle: {
    fontSize: 14,
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
    gap: 8,
  },
  teamName: {
    fontSize: 22,
    fontWeight: "800",
    textAlign: "center",
  },
  teamMeta: {
    fontSize: 14,
    textAlign: "center",
  },
  schemeRow: {
    flexDirection: "row",
    justifyContent: "center",
    gap: 8,
    marginTop: 4,
  },
  schemeBadge: {
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  schemeText: {
    fontSize: 12,
    fontWeight: "600",
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: "700",
    marginBottom: 4,
  },
  fieldWrapper: {
    borderRadius: 12,
    overflow: "hidden",
    position: "relative",
    marginBottom: 4,
  },
  playerCard: {
    backgroundColor: "rgba(0,0,0,0.72)",
    borderRadius: 7,
    paddingHorizontal: 5,
    paddingVertical: 4,
    alignItems: "center",
    width: 72,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.15)",
  },
  posBadge: {
    borderRadius: 4,
    paddingHorizontal: 5,
    paddingVertical: 1,
    marginBottom: 2,
    minWidth: 28,
    alignItems: "center",
  },
  posText: {
    fontSize: 10,
    fontWeight: "800",
  },
  playerName: {
    fontSize: 10,
    fontWeight: "600",
    color: "#ffffff",
    textAlign: "center",
  },
  playerTeam: {
    fontSize: 9,
    color: "rgba(255,255,255,0.6)",
    textAlign: "center",
  },
  rosterRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingVertical: 7,
    borderBottomWidth: 0.5,
  },
  rosterBadge: {
    borderRadius: 5,
    paddingHorizontal: 7,
    paddingVertical: 2,
    minWidth: 38,
    alignItems: "center",
  },
  rosterPos: {
    fontSize: 11,
    fontWeight: "700",
  },
  rosterName: {
    flex: 1,
    fontSize: 14,
    fontWeight: "600",
  },
  rosterTeam: {
    fontSize: 12,
  },
  viewButton: {
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 4,
  },
  viewButtonText: {
    fontWeight: "700",
    fontSize: 16,
  },
});
