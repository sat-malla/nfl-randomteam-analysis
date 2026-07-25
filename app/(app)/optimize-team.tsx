import { NFL_TEAM_COLORS, NFL_TEAM_COLORS_DARK } from "@/utils/nflTeamColors";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  ActivityIndicator,
  useColorScheme,
  Modal,
} from "react-native";
import { useState } from "react";
import Ionicons from "react-native-vector-icons/Ionicons";

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

type RosterPlayer = {
  name: string;
  position: string;
  nfl_team: string;
  salary: number;
  salary_display: string;
};

type OptimizeResult = {
  superbowl_probability: number;
  offense_type: string;
  defense_type: string;
  total_salary: number;
  salary_cap: number;
  cap_space_remaining: number;
  roster_size: number;
  position_breakdown: Record<string, number>;
  fitness_history: number[];
  roster: RosterPlayer[];
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
  SAF: { bg: "#004c75", text: "#ffffff" },
  K: { bg: "#1ec95d", text: "#ffffff" },
  P: { bg: "#21ccb2", text: "#ffffff" },
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
  SAF: { bg: "#38bdf8", text: "#000000" },
  K: { bg: "#4ade80", text: "#000000" },
  P: { bg: "#2dd4bf", text: "#000000" },
  RS: { bg: "#a16207", text: "#000000" },
};

const POS_ORDER = [
  "QB", "RB", "FB", "WR", "TE",
  "OT", "G", "C",
  "DE", "DT", "NT", "DL",
  "LB", "OLB", "ILB", "MLB", "SLB", "WLB",
  "CB", "FS", "SS", "S", "SAF",
  "K", "P", "RS",
];

function formatSalary(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

function capBarColor(pct: number): string {
  if (pct >= 0.95) return "#dc2626";
  if (pct >= 0.80) return "#f59e0b";
  return "#16a34a";
}

export default function OptimizeTeam() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [error, setError] = useState("");
  const [infoVisible, setInfoVisible] = useState(false);

  const posColors = isDark ? POS_COLORS_DARK : POS_COLORS_LIGHT;

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
    accent: "#3b82f6",
    green: "#16a34a",
  };

  const handleOptimize = async () => {
    setLoading(true);
    setResult(null);
    setError("");
    try {
      const resp = await fetch(`${API_URL}/api/optimize/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await resp.json();
      if (!resp.ok) {
        setError(data.message ?? "Optimization failed. Try again.");
      } else {
        setResult(data);
      }
    } catch {
      setError("Network error. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const capUsed = result ? result.total_salary / result.salary_cap : 0;
  const capBarWidth = Math.min(capUsed, 1);

  const offense = result?.roster.filter(p => ["QB", "RB", "FB", "WR", "TE"].includes(p.position)) ?? [];
  const oline = result?.roster.filter(p => ["OT", "G", "C"].includes(p.position)) ?? [];
  const defense = result?.roster.filter(p =>
    ["DE", "DT", "NT", "DL", "LB", "OLB", "ILB", "MLB", "SLB", "WLB", "CB", "FS", "SS", "S", "SAF"].includes(p.position)
  ) ?? [];
  const special = result?.roster.filter(p => ["K", "P", "RS"].includes(p.position)) ?? [];

  const renderPlayer = (player: RosterPlayer, i: number) => {
    const posColor = posColors[player.position] ?? { bg: "#334155", text: "#ffffff" };
    const teamColor = (isDark ? NFL_TEAM_COLORS_DARK : NFL_TEAM_COLORS)[player.nfl_team] ?? (isDark ? { bg: "#4a5568", text: "#000000" } : { bg: "#334155", text: "#ffffff" });
    return (
      <View key={i} style={[styles.playerRow, { borderBottomColor: c.border }]}>
        <View style={styles.playerLeft}>
          <View style={[styles.posBadge, { backgroundColor: posColor.bg }]}>
            <Text style={[styles.posText, { color: posColor.text }]}>{player.position}</Text>
          </View>
          <View style={styles.playerInfo}>
            <Text style={[styles.playerName, { color: c.text }]}>{player.name}</Text>
            {player.nfl_team ? (
              <View style={[styles.teamBadge, { backgroundColor: teamColor.bg }]}>
                <Text style={[styles.teamText, { color: teamColor.text }]}>{player.nfl_team}</Text>
              </View>
            ) : null}
          </View>
        </View>
        <Text style={[styles.salary, { color: c.subtext }]}>{formatSalary(player.salary)}</Text>
      </View>
    );
  };

  const renderGroup = (title: string, players: RosterPlayer[]) =>
    players.length === 0 ? null : (
      <View key={title}>
        <Text style={[styles.groupLabel, { color: c.subtext }]}>{title}</Text>
        {players.map(renderPlayer)}
      </View>
    );

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: c.bg }}
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator={false}
    >
      <Text style={[styles.title, { color: c.text }]}>Optimal Team Builder</Text>
      <Text style={[styles.subtitle, { color: c.subtext }]}>
        Generate a RANDOMIZED but OPTIMAL team under a{" "}
        <Text style={{ fontFamily: "Montserrat_700Bold" }}>$200M salary cap</Text> to
        maximize Super Bowl probability!
      </Text>

      <Modal
        visible={infoVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setInfoVisible(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setInfoVisible(false)}
        >
          <View style={[styles.modalCard, { backgroundColor: c.card, borderColor: c.border }]}>
            <Text style={[styles.modalTitle, { color: c.text }]}>How It Works</Text>

            <View style={styles.modalItem}>
              <Text style={[styles.modalItemTitle, { color: c.text }]}>$200M Salary Cap</Text>
              <Text style={[styles.modalItemBody, { color: c.subtext }]}>
                The NFL uses a salary cap to stop teams from buying every superstar. We will use $200M, which roughly what real NFL teams work with so you can't just stack the roster with Patrick Mahomes, Puka Nacua, and Myles Garrett. Every player has a price tag based on their real performance, so you have to make tradeoffs.
              </Text>
            </View>

            <View style={[styles.modalDivider, { backgroundColor: c.border }]} />

            <View style={styles.modalItem}>
              <Text style={[styles.modalItemTitle, { color: c.text }]}>29-Player Roster</Text>
              <Text style={[styles.modalItemBody, { color: c.subtext }]}>
                The active NFL roster has 53 players, but most don't see the field. We will use 29: the 11 starters on offense and 11 on defense. So, every pick actually matters to the simulation.
              </Text>
            </View>

            <TouchableOpacity
              style={[styles.modalClose, { backgroundColor: c.button }]}
              onPress={() => setInfoVisible(false)}
            >
              <Text style={[styles.modalCloseText, { color: c.buttonText }]}>Got it</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>

      <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
        <View style={styles.cardHeader}>
          <Text style={[styles.sectionTitle, { color: c.text }]}>Parameters</Text>
          <TouchableOpacity onPress={() => setInfoVisible(true)} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <Ionicons name="information-circle-outline" size={24} color={c.subtext} />
          </TouchableOpacity>
        </View>

        <View style={styles.paramGrid}>
          <View style={styles.paramItem}>
            <Text style={[styles.paramValue, { color: c.accent }]}>$200M</Text>
            <Text style={[styles.paramLabel, { color: c.subtext }]}>Salary Cap</Text>
          </View>
          <View style={styles.paramItem}>
            <Text style={[styles.paramValue, { color: c.accent }]}>29</Text>
            <Text style={[styles.paramLabel, { color: c.subtext }]}>Roster Size</Text>
          </View>
        </View>

        <TouchableOpacity
          style={[styles.optimizeBtn, { backgroundColor: loading ? "#9ca3af" : c.button }]}
          disabled={loading}
          onPress={handleOptimize}
        >
          {loading ? (
            <View style={styles.loadingRow}>
              <ActivityIndicator color={c.buttonText} style={{ marginRight: 8 }} />
              <Text style={[styles.optimizeBtnText, { color: "#fff" }]}>Running GA...</Text>
            </View>
          ) : (
            <Text style={[styles.optimizeBtnText, { color: c.buttonText }]}>
              {result ? "Re-Run Optimizer" : "Build Optimal Team"}
            </Text>
          )}
        </TouchableOpacity>

        {loading && (
          <Text style={[styles.loadingHint, { color: c.subtext }]}>
            Evolving 40 rosters across 60 generations... 15-30s
          </Text>
        )}
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
            <Text style={[styles.sectionTitle, { color: c.text }]}>Optimal Roster Found</Text>
            <View style={styles.sbRow}>
              <Text style={[styles.sbProb, { color: c.green }]}>
                {result.superbowl_probability.toFixed(1)}%
              </Text>
              <Text style={[styles.sbLabel, { color: c.subtext }]}>Super Bowl Probability</Text>
              <View style={styles.formationRow}>
                <View style={[styles.formationBadge, { backgroundColor: c.accent }]}>
                  <Text style={styles.formationText}>{result.offense_type}</Text>
                </View>
                <View style={[styles.formationBadge, { backgroundColor: "#db2777" }]}>
                  <Text style={styles.formationText}>{result.defense_type}</Text>
                </View>
              </View>
            </View>
            <View style={styles.capSection}>
              <View style={styles.capHeader}>
                <Text style={[styles.capLabel, { color: c.text }]}>Salary Cap Usage</Text>
                <Text style={[styles.capNumbers, { color: c.subtext }]}>
                  {formatSalary(result.total_salary)} / {formatSalary(result.salary_cap)}
                </Text>
              </View>
              <View style={[styles.capBarBg, { backgroundColor: c.border }]}>
                <View
                  style={[
                    styles.capBarFill,
                    {
                      width: `${Math.round(capBarWidth * 100)}%` as any,
                      backgroundColor: capBarColor(capBarWidth),
                    },
                  ]}
                />
              </View>
              <Text style={[styles.capRemaining, { color: c.subtext }]}>
                {formatSalary(result.cap_space_remaining)} remaining
              </Text>
            </View>
            <Text style={[styles.breakdownTitle, { color: c.subtext }]}>Position Breakdown</Text>
            <View style={styles.breakdownGrid}>
              {POS_ORDER.filter(pos => result.position_breakdown[pos])
                .map(pos => {
                  const posColor = posColors[pos] ?? { bg: "#334155", text: "#ffffff" };
                  return (
                    <View key={pos} style={styles.breakdownItem}>
                      <View style={[styles.posBadge, { backgroundColor: posColor.bg }]}>
                        <Text style={[styles.posText, { color: posColor.text }]}>{pos}</Text>
                      </View>
                      <Text style={[styles.breakdownCount, { color: c.text }]}>
                        ×{result.position_breakdown[pos]}
                      </Text>
                    </View>
                  );
                })}
            </View>
          </View>
          <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
            <Text style={[styles.sectionTitle, { color: c.text }]}>Roster ({result.roster_size} players)</Text>
            {renderGroup("Offense", offense)}
            {renderGroup("O-Line", oline)}
            {renderGroup("Defense", defense)}
            {renderGroup("Special Teams", special)}
          </View>
          {result.fitness_history.length > 0 && (
            <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
              <Text style={[styles.sectionTitle, { color: c.text }]}>GA Convergence</Text>
              <Text style={[styles.convergenceSubtitle, { color: c.subtext }]}>
                Best Super Bowl probability per generation
              </Text>
              <View style={styles.sparklineContainer}>
                {result.fitness_history.map((val, i) => {
                  const max = Math.max(...result.fitness_history);
                  const min = Math.min(...result.fitness_history);
                  const range = max - min || 1;
                  const heightPct = ((val - min) / range) * 100;
                  return (
                    <View
                      key={i}
                      style={[
                        styles.sparkBar,
                        {
                          height: Math.max(4, (heightPct / 100) * 80),
                          backgroundColor: i === result.fitness_history.length - 1 ? c.green : c.accent,
                          opacity: 0.4 + (i / result.fitness_history.length) * 0.6,
                        },
                      ]}
                    />
                  );
                })}
              </View>
              <View style={styles.convergenceStats}>
                <View style={styles.convergenceStat}>
                  <Text style={[styles.convergenceVal, { color: c.text }]}>
                    {result.fitness_history[0].toFixed(2)}%
                  </Text>
                  <Text style={[styles.convergenceLabel, { color: c.subtext }]}>Gen 1</Text>
                </View>
                <View style={styles.convergenceStat}>
                  <Text style={[styles.convergenceVal, { color: c.green }]}>
                    {result.fitness_history[result.fitness_history.length - 1].toFixed(2)}%
                  </Text>
                  <Text style={[styles.convergenceLabel, { color: c.subtext }]}>Final</Text>
                </View>
              </View>
            </View>
          )}
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
    fontFamily: "Montserrat_700Bold",
    textAlign: "center",
  },
  subtitle: {
    fontSize: 14,
    fontFamily: "Montserrat_400Regular",
    marginTop: 8,
    textAlign: "center",
    marginBottom: 20,
    lineHeight: 20,
  },
  card: {
    width: "100%",
    borderRadius: 14,
    borderWidth: 1,
    padding: 16,
    marginBottom: 16,
    gap: 12,
  },
  sectionTitle: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 20,
    textAlign: "center",
    marginBottom: 4,
    flex: 1,
  },
  paramGrid: {
    flexDirection: "row",
    justifyContent: "space-around",
  },
  paramItem: {
    alignItems: "center",
    gap: 4,
  },
  paramValue: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 20,
  },
  paramLabel: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 11,
  },
  optimizeBtn: {
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 4,
  },
  optimizeBtnText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 16,
  },
  loadingRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  loadingHint: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 12,
    textAlign: "center",
    marginTop: -4,
  },
  sbRow: {
    alignItems: "center",
    gap: 4,
  },
  sbProb: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 48,
  },
  sbLabel: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
  },
  capSection: {
    gap: 6,
  },
  capHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  capLabel: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 13,
  },
  capNumbers: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 12,
  },
  capBarBg: {
    height: 10,
    borderRadius: 5,
    overflow: "hidden",
  },
  capBarFill: {
    height: "100%",
    borderRadius: 5,
  },
  capRemaining: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 12,
    textAlign: "right",
  },
  breakdownTitle: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 12,
    letterSpacing: 0.8,
    textTransform: "uppercase",
  },
  breakdownGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  breakdownItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  breakdownCount: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 13,
  },
  groupLabel: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 12,
    letterSpacing: 0.8,
    textTransform: "uppercase",
    paddingVertical: 8,
    paddingTop: 14,
  },
  playerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 10,
    borderBottomWidth: 0.5,
  },
  playerLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    flex: 1,
  },
  playerInfo: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    flexWrap: "wrap",
    flex: 1,
  },
  playerName: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 14,
  },
  posBadge: {
    borderRadius: 5,
    paddingHorizontal: 7,
    paddingVertical: 3,
    alignItems: "center",
    justifyContent: "center",
  },
  posText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 11,
  },
  teamBadge: {
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  teamText: {
    fontSize: 11,
    fontFamily: "Montserrat_700Bold",
  },
  salary: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 13,
    marginLeft: 8,
  },
  sparklineContainer: {
    flexDirection: "row",
    alignItems: "flex-end",
    height: 80,
    gap: 2,
    paddingVertical: 4,
  },
  sparkBar: {
    flex: 1,
    borderRadius: 2,
  },
  convergenceSubtitle: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 12,
    textAlign: "center",
    marginTop: -8,
  },
  convergenceStats: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  convergenceStat: {
    alignItems: "center",
    gap: 2,
  },
  convergenceVal: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 16,
  },
  convergenceLabel: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 11,
  },
  formationRow: {
    flexDirection: "row",
    gap: 8,
    marginTop: 6,
    justifyContent: "center",
    flexWrap: "wrap",
  },
  formationBadge: {
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  formationText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 12,
    color: "#ffffff",
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  modalCard: {
    width: "100%",
    borderRadius: 16,
    borderWidth: 1,
    padding: 20,
    gap: 16,
  },
  modalTitle: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 18,
    textAlign: "center",
  },
  modalItem: {
    gap: 6,
  },
  modalItemTitle: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 15,
  },
  modalItemBody: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 13,
    lineHeight: 20,
  },
  modalDivider: {
    height: 1,
  },
  modalClose: {
    padding: 12,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 4,
  },
  modalCloseText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 15,
  },
});
