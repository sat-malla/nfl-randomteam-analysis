import { NFL_TEAM_COLORS, NFL_TEAM_COLORS_DARK, toTeamAbbr } from "@/utils/nflTeamColors";
import {
  ScrollView,
  StyleSheet,
  Switch,
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
  is_score?: boolean;
};

type BoxEntry = {
  name: string;
  position: string;
  nfl_team?: string;
  stats: { label: string; val: number | string }[];
};

type SimResult = {
  user_team: string;
  opponent: string;
  season: number;
  playoff_mode: boolean;
  overtime_periods: number;
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
  OT1: "#7c3aed",
  OT2: "#7c3aed",
  OT3: "#7c3aed",
  OT4: "#7c3aed",
  OT5: "#7c3aed",
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
  SAF: { bg: "#38bdf8", text: "#000000" },
  K: { bg: "#4ade80", text: "#000000" },
  P: { bg: "#2dd4bf", text: "#000000" },
  RS: { bg: "#a16207", text: "#000000" },
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
  const [error, setError] = useState<{ message: string; status: number; raw: string } | null>(null);

  const [playoffMode, setPlayoffMode] = useState(false);
  const [myTeamOpen, setMyTeamOpen] = useState(false);
  const [nflPickerOpen, setNflPickerOpen] = useState(false);
  const [seasonOpen, setSeasonOpen] = useState(false);

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
    setError(null);
    try {
      const resp = await fetch(`${API_URL}/api/simulate/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          team_id: selectedTeam.id,
          nfl_opponent: selectedOpponent,
          season: parseInt(selectedSeason, 10),
          is_home: isHome,
          playoff_mode: playoffMode,
        }),
      });
      const rawText = await resp.text();
      if (!resp.ok) {
        let message = "Simulation failed. Try again.";
        try {
          const data = JSON.parse(rawText);
          message = data.message ?? data.detail ?? message;
        } catch {}
        setError({ message, status: resp.status, raw: rawText });
      } else {
        try {
          setResult(JSON.parse(rawText));
        } catch {
          setError({ message: "Received invalid response from server.", status: resp.status, raw: rawText });
        }
      }
    } catch (e: any) {
      setError({ message: e?.message ?? "Network error. Make sure the backend is running.", status: 0, raw: "" });
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
                onPress={() => myTeams.length > 0 ? setMyTeamOpen(true) : undefined}
                borderColor={c.border}
                textColor={myTeams.length > 0 ? c.text : c.subtext}
                placeholderColor={c.subtext}
              />
              {myTeams.length === 0 && (
                <Text style={{ color: "red", fontSize: 12, fontFamily: "Montserrat_400Regular", marginTop: 4 }}>
                  Generate a team first to get started!
                </Text>
              )}
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

        <View style={[styles.playoffRow, { borderColor: c.border, backgroundColor: playoffMode ? (isDark ? "#1e1040" : "#f3f0ff") : "transparent" }]}>
          <View style={{ flex: 1 }}>
            <Text style={[styles.playoffLabel, { color: c.text }]}>Playoff Mode</Text>
            <Text style={[styles.playoffHint, { color: c.subtext }]}>
              No ties! Game goes to however many OTs it takes. Expect a tougher play by the opponent.
            </Text>
          </View>
          <Switch
            value={playoffMode}
            onValueChange={setPlayoffMode}
            trackColor={{ false: c.border, true: "#7c3aed" }}
            thumbColor="#fff"
          />
        </View>

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
        <View style={[styles.card, { backgroundColor: "#fee2e2", borderColor: "#fca5a5", boxShadow: c.shadow, gap: 8 }]}>
          <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
            <Text style={{ color: "#dc2626", fontFamily: "Montserrat_700Bold", fontSize: 15 }}>
              Simulation Error
            </Text>
            {error.status > 0 && (
              <View style={{ backgroundColor: "#dc2626", borderRadius: 6, paddingHorizontal: 8, paddingVertical: 2 }}>
                <Text style={{ color: "#fff", fontFamily: "Montserrat_700Bold", fontSize: 12 }}>
                  HTTP {error.status}
                </Text>
              </View>
            )}
          </View>
          <Text style={{ color: "#991b1b", fontFamily: "Montserrat_400Regular", fontSize: 14, lineHeight: 20 }}>
            {error.message}
          </Text>
          {!!error.raw && error.raw !== error.message && (
            <View style={{ backgroundColor: "#fecaca", borderRadius: 8, padding: 10, marginTop: 2 }}>
              <Text style={{ color: "#7f1d1d", fontFamily: "Montserrat_400Regular", fontSize: 12, lineHeight: 18 }}>
                {error.raw.length > 500 ? error.raw.slice(0, 500) + "..." : error.raw}
              </Text>
            </View>
          )}
        </View>
      )}

      {result && (
        <>
          <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
            <Text style={[styles.sectionTitle, { color: c.text }]}>Final Score</Text>
            <View style={styles.scoreboard}>
              <View style={styles.scoreTeam}>
                <Text style={[styles.scoreTeamName, { color: c.text }]} numberOfLines={2}>
                  {isHome ? `${result.season} ${result.opponent}` : result.user_team}
                </Text>
                <Text style={[styles.scoreNum, { color: winnerColor }]}>
                  {isHome ? result.final_score.opponent : result.final_score.user}
                </Text>
              </View>
              <View style={styles.scoreTeam}>
                <Text style={[styles.scoreTeamName, { color: c.text }]} numberOfLines={2}>
                  {isHome ? result.user_team : `${result.season} ${result.opponent}`}
                </Text>
                <Text style={[styles.scoreNum, { color: winnerColor }]}>
                  {isHome ? result.final_score.user : result.final_score.opponent}
                </Text>
              </View>
            </View>
            <Text style={[styles.winnerBadge, { color: winnerColor }]}>{winnerLabel}</Text>
            {result.overtime_periods > 0 && (
              <View style={[styles.otBadge, { backgroundColor: isDark ? "#1e1040" : "#f3f0ff", borderColor: "#7c3aed" }]}>
                <Text style={styles.otBadgeText}>
                  {result.overtime_periods === 1 ? "Overtime" : `${result.overtime_periods}x Overtime`}
                </Text>
              </View>
            )}
          </View>

          {result.box_score.length > 0 && (() => {
            const OFF_ORDER = ["QB", "RB", "FB", "WR", "TE"];
            const DEF_ORDER = ["DE", "DT", "NT", "DL", "LB", "OLB", "ILB", "MLB", "SLB", "WLB", "CB", "DB", "FS", "SS", "S", "SAF", "Nickel", "Dime"];
            const ST_ORDER = ["K", "P", "RS"];
            const offense = result.box_score.filter(p => OFF_ORDER.includes(p.position))
              .sort((a, b) => OFF_ORDER.indexOf(a.position) - OFF_ORDER.indexOf(b.position));
            const defense = result.box_score.filter(p => DEF_ORDER.includes(p.position))
              .sort((a, b) => DEF_ORDER.indexOf(a.position) - DEF_ORDER.indexOf(b.position));
            const specialTeams = result.box_score.filter(p => ST_ORDER.includes(p.position))
              .sort((a, b) => ST_ORDER.indexOf(a.position) - ST_ORDER.indexOf(b.position));

            const renderPlayer = (player: BoxEntry, i: number) => {
              const posColor = posColors[player.position] ?? { bg: "#334155", text: "#ffffff" };
              return (
                <View key={i} style={[styles.boxRow, { borderBottomColor: c.border }]}>
                  <View style={styles.boxLeft}>
                    <View style={[styles.posBadge, { backgroundColor: posColor.bg }]}>
                      <Text style={[styles.posText, { color: posColor.text }]}>{player.position}</Text>
                    </View>
                    <Text style={[styles.boxName, { color: c.text }]}>{player.name}</Text>
                    {player.nfl_team ? (() => { const abbr = toTeamAbbr(player.nfl_team); const tc = (isDark ? NFL_TEAM_COLORS_DARK : NFL_TEAM_COLORS)[abbr] ?? (isDark ? { bg: "#4a5568", text: "#000000" } : { bg: "#334155", text: "#ffffff" }); return (
                      <View style={[styles.posBadge, { backgroundColor: tc.bg, marginLeft: 6 }]}>
                        <Text style={[styles.posText, { color: tc.text }]}>{abbr}</Text>
                      </View>
                    ); })() : null}
                  </View>
                  <View style={styles.boxStats}>
                    {player.stats.map(({ label, val }) => (
                      <View key={label} style={styles.statChip}>
                        <Text style={[styles.statVal, { color: c.text }]}>{val}</Text>
                        <Text style={[styles.statLabel, { color: c.subtext }]}>{label}</Text>
                      </View>
                    ))}
                  </View>
                </View>
              );
            };

            const renderGroup = (title: string, players: BoxEntry[]) => players.length === 0 ? null : (
              <View key={title}>
                <Text style={[styles.boxGroupLabel, { color: c.subtext }]}>{title}</Text>
                {players.map(renderPlayer)}
              </View>
            );

            return (
              <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
                <Text style={[styles.sectionTitle, { color: c.text }]}>Your Team Box Score</Text>
                {renderGroup("Offense", offense)}
                {renderGroup("Defense", defense)}
                {renderGroup("Special Teams", specialTeams)}
              </View>
            );
          })()}

          {result.play_by_play.length > 0 && (
            <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
              <Text style={[styles.sectionTitle, { color: c.text }]}>Highlights</Text>
              {result.play_by_play.map((entry, i) => {
                const isUser = entry.team === result.user_team;
                const qColor = QUARTER_COLORS[entry.quarter] ?? (entry.quarter.startsWith("OT") ? "#7c3aed" : c.subtext);
                return (
                  <View key={i} style={[styles.playRow, { borderBottomColor: c.border }]}>
                    <View style={styles.playMeta}>
                      <View style={[styles.quarterBadge, { backgroundColor: qColor }]}>
                        <Text style={styles.quarterText}>{entry.quarter}</Text>
                      </View>
                      <Text style={[styles.playScore, { color: c.subtext }]}>{entry.score}</Text>
                      {entry.is_score && (
                        <View style={styles.scoreBadge}>
                          <Text style={styles.scoreBadgeText}>SCORE!</Text>
                        </View>
                      )}
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
  playoffRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
  },
  playoffLabel: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 14,
    marginBottom: 2,
  },
  playoffHint: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 12,
    lineHeight: 17,
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
  otBadge: {
    alignSelf: "center",
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 5,
    marginTop: 4,
  },
  otBadgeText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 12,
    color: "#7c3aed",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  seasonLabel: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 12,
    textAlign: "center",
  },
  boxGroupLabel: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 12,
    letterSpacing: 0.8,
    textTransform: "uppercase",
    paddingVertical: 8,
    paddingTop: 14,
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
    flexWrap: "wrap",
  },
  scoreBadge: {
    backgroundColor: "#004ba1",
    borderRadius: 5,
    paddingHorizontal: 7,
    paddingVertical: 2,
  },
  scoreBadgeText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 11,
    color: "#ffffff",
    letterSpacing: 0.5,
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
    flex: 1,
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
