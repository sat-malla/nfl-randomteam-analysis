import { assignLbLabels } from "@/utils/defense-rendering";
import { NFL_TEAM_COLORS, NFL_TEAM_COLORS_DARK, toTeamAbbr } from "@/utils/nflTeamColors";
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
  Alert,
} from "react-native";
import Svg, {
  Rect,
  Line,
  Text as SvgText,
} from "react-native-svg";
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
  LS: { bg: "#a8a29e", text: "#000000" },
  RS: { bg: "#f87171", text: "#000000" },
};

const OFFENSE_POSITIONS = new Set(["QB", "RB", "FB", "WR", "TE", "OT", "G", "C", "OL", "K", "P", "LS", "RS"]);
const DEFENSE_POSITIONS = new Set(["DE", "DT", "NT", "DL", "LB", "OLB", "ILB", "MLB", "SLB", "WLB", "CB", "S", "FS", "SS", "DB", "SAF", "Nickel", "Dime"]);

const DEFENSE_ROW_ORDER = [
  ["DE", "DT", "NT", "DL"],
  ["LB", "ILB", "MLB", "SLB", "WLB", "OLB"],
  ["CB", "Nickel", "Dime", "DB", "SAF"],
  ["FS", "SS", "S"],
];


const DEFENSE_ROW_Y_FRACS = [0.88, 0.68, 0.46, 0.24];

const OFFENSE_ROW_ORDER = [
  ["OT", "G", "C", "OL"],
  ["WR", "TE"],
  ["RB", "FB"],
  ["QB"],
];

const ST_POSITIONS = new Set(["K", "P", "RS", "LS"]);
const ST_ORDER = ["K", "P", "RS", "LS"];

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
  const totalSegments = 10;
  const segH = height / totalSegments;
  const stripeColors = ["#1a6b2a", "#1e7a30"];
  const yardLabels = ["10", "20", "30", "40", "50", "40", "30", "20", "10"];
  const hashInset = width * 0.28;
  const hashLen = 7;

  return (
    <Svg width={width} height={height} style={StyleSheet.absoluteFillObject} pointerEvents="none">
      <Rect x={0} y={0} width={width} height={height} fill="#1a6b2a" />

      {Array.from({ length: totalSegments }).map((_, i) => (
        <Rect key={`s${i}`} x={0} y={i * segH} width={width} height={segH} fill={stripeColors[i % 2]} />
      ))}

      {yardLabels.map((label, i) => {
        const y = (i + 1) * segH;
        const is50 = label === "50";
        return (
          <Line key={`yl${i}`} x1={0} y1={y} x2={width} y2={y}
            stroke="#ffffff" strokeWidth={is50 ? 2.5 : 1.2} opacity={is50 ? 0.9 : 0.55} />
        );
      })}

      <Rect x={1} y={1} width={width - 2} height={height - 2} fill="none" stroke="#ffffff" strokeWidth={2} opacity={0.75} />

      
      {yardLabels.map((_, i) => {
        const y = (i + 1) * segH;
        return [hashInset, width - hashInset].map((x, j) => (
          <Line key={`h${i}-${j}`} x1={x} y1={y - hashLen / 2} x2={x} y2={y + hashLen / 2}
            stroke="#ffffff" strokeWidth={1.5} opacity={0.65} />
        ));
      })}

     
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

const DE_POSITIONS = new Set(["DE"]);
const DT_POSITIONS = new Set(["DT", "NT", "DL"]);
const OLB_POSITIONS = new Set(["OLB"]);
const INNER_LB_POSITIONS = new Set(["LB", "ILB", "MLB", "SLB", "WLB"]);
const CB_POSITIONS = new Set(["CB"]);
const NICKEL_DIME_POSITIONS = new Set(["Nickel", "Dime", "DB", "SAF"]);
const OT_POSITIONS = new Set(["OT"]);
const G_POSITIONS = new Set(["G"]);
const C_POSITIONS = new Set(["C", "OL"]);

function sortOLine(players: Player[]): Player[] {
  const ots = players.filter((p) => OT_POSITIONS.has(p.position));
  const gs = players.filter((p) => G_POSITIONS.has(p.position));
  const cs = players.filter((p) => C_POSITIONS.has(p.position));
  const other = players.filter((p) => !OT_POSITIONS.has(p.position) && !G_POSITIONS.has(p.position) && !C_POSITIONS.has(p.position));
  const leftOT = ots[0] ? [ots[0]] : [];
  const rightOT = ots[1] ? [ots[1]] : [];
  const leftG = gs[0] ? [gs[0]] : [];
  const rightG = gs[1] ? [gs[1]] : [];
  return [...leftOT, ...leftG, ...cs, ...other, ...rightG, ...rightOT];
}

function sortDLine(players: Player[]): Player[] {
  const des = players.filter((p) => DE_POSITIONS.has(p.position));
  const dts = players.filter((p) => DT_POSITIONS.has(p.position));
  const other = players.filter((p) => !DE_POSITIONS.has(p.position) && !DT_POSITIONS.has(p.position));
  if (des.length >= 2) {
    return [des[0], ...dts, ...other, ...des.slice(1)];
  }
  return [...des, ...dts, ...other];
}

// OLB on edges, inner LBs (ILB/MLB/SLB/WLB) in the middle
function sortLBRow(players: Player[]): Player[] {
  const olbs = players.filter((p) => OLB_POSITIONS.has(p.position));
  const inner = players.filter((p) => INNER_LB_POSITIONS.has(p.position));
  const other = players.filter((p) => !OLB_POSITIONS.has(p.position) && !INNER_LB_POSITIONS.has(p.position));
  const leftOLB = olbs[0] ? [olbs[0]] : [];
  const rightOLB = olbs[1] ? [olbs[1]] : [];
  return [...leftOLB, ...inner, ...other, ...rightOLB];
}

function sortSecondary(players: Player[]): Player[] {
  const cbs = players.filter((p) => CB_POSITIONS.has(p.position));
  const slots = players.filter((p) => NICKEL_DIME_POSITIONS.has(p.position));
  const other = players.filter((p) => !CB_POSITIONS.has(p.position) && !NICKEL_DIME_POSITIONS.has(p.position));
  if (cbs.length >= 2) {
    return [cbs[0], ...slots, ...other, ...cbs.slice(1)];
  }
  return [...cbs, ...slots, ...other];
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

function SpecialTeamsField({
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
  const miniHeight = 110;

  const stPlayers = ST_ORDER
    .map((pos) => team.players.find((p) => p.position === pos))
    .filter((p): p is Player => !!p);

  return (
    <View style={{ width: fieldWidth, marginTop: 12 }}>
      <View style={{ height: 1, backgroundColor: c.border, marginBottom: 12 }} />
      <Text style={{ textAlign: "center", color: c.subtext, fontFamily: "Montserrat_700Bold", fontSize: 13, marginBottom: 6 }}>
        Special Teams
      </Text>
      <View style={[styles.fieldWrapper, { width: fieldWidth, height: miniHeight }]}>
        <Svg width={fieldWidth} height={miniHeight} style={StyleSheet.absoluteFillObject} pointerEvents="none">
          <Rect x={0} y={0} width={fieldWidth} height={miniHeight} fill="#1a6b2a" />
          <Rect x={0} y={0} width={fieldWidth} height={miniHeight / 2} fill="#1e7a30" />
          <Line x1={0} y1={miniHeight / 2} x2={fieldWidth} y2={miniHeight / 2}
            stroke="#ffffff" strokeWidth={2.5} opacity={0.9} />
          <SvgText x={fieldWidth * 0.08} y={miniHeight / 2 - 4} textAnchor="middle"
            fill="#ffffff" fontSize={13} fontWeight="bold" opacity={0.85}>50</SvgText>
          <SvgText x={fieldWidth * 0.92} y={miniHeight / 2 - 4} textAnchor="middle"
            fill="#ffffff" fontSize={13} fontWeight="bold" opacity={0.85}>50</SvgText>
          <Rect x={1} y={1} width={fieldWidth - 2} height={miniHeight - 2} fill="none" stroke="#ffffff" strokeWidth={2} opacity={0.75} />
        </Svg>
        <View style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: fieldWidth,
          height: miniHeight,
          flexDirection: "row",
          justifyContent: "center",
          alignItems: "center",
          gap: 6,
          paddingHorizontal: 8,
        }}>
          {stPlayers.map((player, i) => (
            <PlayerCard key={`${player.name}-${i}`} player={player} posColors={posColors} />
          ))}
        </View>
      </View>
      <View style={{ height: 1, backgroundColor: c.border, marginTop: 12 }} />
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
    OFFENSE_POSITIONS.has(p.position) && !ST_POSITIONS.has(p.position)
  );

  const defenseRows = groupPlayersByRows(defensePlayers, DEFENSE_ROW_ORDER);
  const offenseRows = groupPlayersByRows(offensePlayers, OFFENSE_ROW_ORDER);
  const halfH = fieldHeight / 2;
  const CARD_H = 70;
  const offRowH = offenseRows.length > 0 ? (halfH - 14 * 2) / offenseRows.length : 0;

  return (
    <View style={{ width: fieldWidth, marginBottom: 4 }}>
      <Text style={{ textAlign: "center", color: c.subtext, fontFamily: "Montserrat_700Bold", fontSize: 13, marginBottom: 6 }}>
        Defense
      </Text>

      <View style={[styles.fieldWrapper, { width: fieldWidth, height: fieldHeight }]}>
        <FootballField width={fieldWidth} height={fieldHeight} />

        {defenseRows.map((row, rowIdx) => {
          const frac = DEFENSE_ROW_Y_FRACS[rowIdx] ?? (0.1 + rowIdx * 0.2);
          const y = frac * halfH - CARD_H / 2;

          const hasDLine = row.some((p) => DE_POSITIONS.has(p.position) || DT_POSITIONS.has(p.position));
          const hasSecondary = row.some((p) => CB_POSITIONS.has(p.position) || NICKEL_DIME_POSITIONS.has(p.position));
          const hasLBs = row.some((p) => OLB_POSITIONS.has(p.position) || INNER_LB_POSITIONS.has(p.position));
          const sortedRow = hasDLine ? sortDLine(row) : hasSecondary ? sortSecondary(row) : hasLBs ? sortLBRow(row) : row;

          return (
            <View
              key={`def-row-${rowIdx}`}
              style={{
                position: "absolute",
                top: y,
                left: 0,
                width: fieldWidth,
                flexDirection: "row",
                justifyContent: "center",
                alignItems: "center",
                flexWrap: "wrap",
                gap: 4,
                paddingHorizontal: 4,
              }}
            >
              {sortedRow.map((player, pi) => (
                <PlayerCard key={`${player.name}-${pi}`} player={player} posColors={posColors} />
              ))}
            </View>
          );
        })}

        {offenseRows.map((row, rowIdx) => {
          const y = halfH + 14 + rowIdx * offRowH;
          const hasOL = row.some((p) => OT_POSITIONS.has(p.position) || G_POSITIONS.has(p.position) || C_POSITIONS.has(p.position));
          const sortedOffRow = hasOL ? sortOLine(row) : row;
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
              {sortedOffRow.map((player, pi) => (
                <PlayerCard key={`${player.name}-${pi}`} player={player} posColors={posColors} />
              ))}
            </View>
          );
        })}
      </View>

      <Text style={{ textAlign: "center", color: c.subtext, fontFamily: "Montserrat_700Bold", fontSize: 13, marginTop: 6 }}>
        Offense
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
  const [teamPickerOpen, setTeamPickerOpen] = useState(false);
  const [deleteTeamName, setDeleteTeamName] = useState<string>("");
  const [deletePickerOpen, setDeletePickerOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

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

  const handleDeleteTeam = () => {
    const summary = teamSummaries.find((t) => t.team_name === deleteTeamName);
    if (!summary) return;
    Alert.alert(
      "Delete Team",
      `Are you sure you want to permanently delete "${deleteTeamName}"? This cannot be undone.`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            setDeleting(true);
            try {
              const res = await fetch(`${API_URL}/api/team/${summary.id}`, { method: "DELETE" });
              const result = await res.json();
              if (result.status === "Success") {
                setTeamSummaries((prev) => prev.filter((t) => t.id !== summary.id));
                if (selectedTeamName === deleteTeamName) {
                  setSelectedTeamName("");
                  setSelectedTeam(null);
                }
                setDeleteTeamName("");
              } else {
                Alert.alert("Error", "Failed to delete team. Please try again.");
              }
            } catch {
              Alert.alert("Error", "Could not connect to server.");
            } finally {
              setDeleting(false);
            }
          },
        },
      ]
    );
  };

  const handleViewTeam = async () => {
    const summary = teamSummaries.find((t) => t.team_name === selectedTeamName);
    if (!summary) return;
    setLoading(true);
    setSelectedTeam(null);
    setDeleteTeamName(selectedTeamName);
    try {
      const res = await fetch(`${API_URL}/api/team/${summary.id}`);
      const result = await res.json();
      if (result.status === "Success" && result.data) {
        setSelectedTeam({ ...result.data, players: assignLbLabels(result.data.players, result.data.defense_type) });
      }
    } catch (_) {}
    setLoading(false);
  };

  return (
    <>
    <ScrollView
      style={{ flex: 1, backgroundColor: c.bg }}
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator
    >
      <Text style={[styles.title, { color: c.text }]}>View & Delete Generated Teams</Text>
      <Text style={[styles.subtitle, { color: c.subtext }]}>
        Pick one of your generated teams and see the full roster.
      </Text>

      <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
        <FormControl size="lg">
          <VStack space="md">
            <FormControlLabel>
              <FormControlLabelText style={{ color: c.text, fontFamily: "Montserrat_700Bold" }}>
                Choose Team
              </FormControlLabelText>
            </FormControlLabel>
            <PickerTrigger
              value={selectedTeamName}
              placeholder="Select a team"
              onPress={() => teamSummaries.length > 0 ? setTeamPickerOpen(true) : undefined}
              borderColor={c.border}
              textColor={teamSummaries.length > 0 ? c.text : c.subtext}
              placeholderColor={c.subtext}
            />
            {teamSummaries.length === 0 && (
              <Text style={{ color: "red", fontSize: 12, fontFamily: "Montserrat_400Regular", marginTop: 4 }}>
                Generate a team first to get started!
              </Text>
            )}
          </VStack>
        </FormControl>

        <TouchableOpacity
          style={[
            styles.viewButton,
            { backgroundColor: selectedTeamName && !loading ? (isDark ? "#edf5ff" : "#02080f") : "#9ca3af" },
          ]}
          disabled={!selectedTeamName || loading || teamSummaries.length === 0}
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
                Head Coach: {selectedTeam.head_coach}
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
          <SpecialTeamsField team={selectedTeam} posColors={posColors} c={c} />

          <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow, marginTop: 16 }]}>
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
                {player.nfl_team ? (() => { const abbr = toTeamAbbr(player.nfl_team); const tc = (isDark ? NFL_TEAM_COLORS_DARK : NFL_TEAM_COLORS)[abbr] ?? (isDark ? { bg: "#4a5568", text: "#000000" } : { bg: "#334155", text: "#ffffff" }); return (
                  <View style={[styles.posBadge, { backgroundColor: tc.bg, marginLeft: "auto" }]}>
                    <Text style={[styles.posText, { color: tc.text }]}>{abbr}</Text>
                  </View>
                ); })() : null}
              </View>
            ))}
          </View>

        </>
      )}

      <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
        <FormControl size="lg">
          <VStack space="md">
            <FormControlLabel>
              <FormControlLabelText style={{ color: c.text, fontFamily: "Montserrat_700Bold" }}>
                Delete Team
              </FormControlLabelText>
            </FormControlLabel>
            <PickerTrigger
              value={deleteTeamName}
              placeholder="Select a team to delete"
              onPress={() => teamSummaries.length > 0 ? setDeletePickerOpen(true) : undefined}
              borderColor={deleteTeamName ? "#ef4444" : c.border}
              textColor={teamSummaries.length > 0 ? c.text : c.subtext}
              placeholderColor={c.subtext}
            />
            {teamSummaries.length === 0 && (
              <Text style={{ color: "red", fontSize: 12, fontFamily: "Montserrat_400Regular", marginTop: 4 }}>
                You must have at least one team generated to delete one! You can't delete nothing!
              </Text>
            )}
          </VStack>
        </FormControl>
        <TouchableOpacity
          style={[
            styles.viewButton,
            { backgroundColor: deleteTeamName && !deleting ? "#ef4444" : "#9ca3af" },
          ]}
          disabled={!deleteTeamName || deleting}
          onPress={handleDeleteTeam}
        >
          {deleting ? (
            <ActivityIndicator color="#ffffff" />
          ) : (
            <Text style={[styles.viewButtonText, { color: "#ffffff" }]}>
              Delete Team
            </Text>
          )}
        </TouchableOpacity>
      </View>
    </ScrollView>
    <PickerModal
      visible={teamPickerOpen}
      onClose={() => setTeamPickerOpen(false)}
      title="Choose Team"
      items={teamSummaries.map((t) => ({ label: t.team_name, value: t.team_name }))}
      selectedValue={selectedTeamName}
      onSelect={handleSelectTeam}
    />
    <PickerModal
      visible={deletePickerOpen}
      onClose={() => setDeletePickerOpen(false)}
      title="Select Team to Delete"
      items={teamSummaries.map((t) => ({ label: t.team_name, value: t.team_name }))}
      selectedValue={deleteTeamName}
      onSelect={(val) => setDeleteTeamName(val)}
    />
    </>
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
    gap: 8,
  },
  teamName: {
    fontSize: 22,
    fontFamily: "Montserrat_700Bold",
    textAlign: "center",
  },
  teamMeta: {
    fontSize: 14,
    fontFamily: "Montserrat_400Regular",
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
    fontFamily: "Montserrat_700Bold",
  },
  sectionTitle: {
    fontSize: 17,
    fontFamily: "Montserrat_700Bold",
    marginBottom: 4,
  },
  fieldWrapper: {
    overflow: "hidden",
    position: "relative",
    marginTop: 4,
    marginBottom: 4,
  },
  playerCard: {
    backgroundColor: "rgba(0,0,0,0.72)",
    borderRadius: 7,
    paddingHorizontal: 3,
    paddingVertical: 4,
    alignItems: "center",
    width: 67,
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
    fontFamily: "Montserrat_700Bold",
  },
  playerName: {
    fontSize: 10,
    fontFamily: "Montserrat_700Bold",
    color: "#ffffff",
    textAlign: "center",
  },
  playerTeam: {
    fontSize: 9,
    fontFamily: "Montserrat_400Regular",
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
    fontFamily: "Montserrat_700Bold",
  },
  rosterName: {
    flex: 1,
    fontSize: 14,
    fontFamily: "Montserrat_700Bold",
  },
  rosterTeam: {
    fontSize: 12,
    fontFamily: "Montserrat_400Regular",
  },
  viewButton: {
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 4,
  },
  viewButtonText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 16,
  },
});
