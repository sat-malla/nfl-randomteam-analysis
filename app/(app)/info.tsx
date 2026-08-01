import {
  ScrollView,
  StyleSheet,
  Text,
  View,
  useColorScheme,
  TouchableOpacity,
  Linking,
} from "react-native";
import Ionicons from "react-native-vector-icons/Ionicons";

type LinkItem = {
  label: string;
  icon: React.ComponentProps<typeof Ionicons>["name"];
  url: string;
};
type ContentBlock =
  | { type: "body"; text: string }
  | { type: "label"; text: string }
  | { type: "links"; links: LinkItem[] };

type Section = {
  id: string;
  icon: React.ComponentProps<typeof Ionicons>["name"];
  title: string;
  content: ContentBlock[];
};

const SECTIONS: Section[] = [
  {
    id: "about",
    icon: "american-football-outline" as const,
    title: "About the App",
    content: [
      {
        type: "body",
        text: "Pro Football Random Team Generator & Analysis (RTGA) is a passion project built for any passionate NFL fans who have wondered how a randomly generated team would do in an NFL season, analyzing stats, or making predictions. Or, optimizing a team to win a Super Bowl? We've seen those Madden NFL simulations, but only amongst actual NFL teams.",
      },
      {
        type: "body",
        text: "You build a fictional team out of real NFL players with a custom name of your choice, then put them through a machine learning-powered simulation engine that models real game outcomes. How cool is that?",
      },
    ],
  },
  {
    id: "how",
    icon: "hardware-chip-outline" as const,
    title: "How It All Works",
    content: [
      {
        type: "label",
        text: "Generate a Team",
      },
      {
        type: "body",
        text: "Pick a head coach, offensive formation (3WR/1TE or 2WR/2TE), and defensive scheme (4-3 or 3-4). The app pulls real NFL players (up-to-date data) and builds your roster.",
      },
      {
        type: "label",
        text: "Analyze a Season",
      },
      {
        type: "body",
        text: "Your team gets run through hundreds of Monte Carlo simulations of a full 17-game season. Each game samples player performance from historical stat distributions, applies a coach multiplier, home/away adjustments, and opponent strength. The result: projected wins, playoff odds, and Super Bowl probability. Now you're really digging deep into a team you just randomly generated!",
      },
      {
        type: "label",
        text: "Simulate a Game",
      },
      {
        type: "body",
        text: "Play-by-play simulation powered by two neural networks: one predicts whether the offense's play call: run, pass, punt, or kick a field goal on any given down at any time. The other predicts the outcome: yards gained, turnover probability, and touchdown chance. The result is a full box score and a highlights narrative.",
      },
      {
        type: "label",
        text: "Optimal Team Builder",
      },
      {
        type: "body",
        text: "A Genetic Algorithm searches thousands of roster combinations under a $301.2M salary cap (updated to 2026) for a 29-person roster team (all starters no backups) to find the team with the highest projected Super Bowl probability. Players are assigned synthetic salaries based on their real historical performance, so you actually have to make tradeoffs.",
      },
    ],
  },
  {
    id: "creator",
    icon: "person-outline" as const,
    title: "About the Creator",
    content: [
      {
        type: "body",
        text: "Hey there! I'm Sathvik Malla, and I am currently studying CS + Math at UC Berkeley. I built this app because I wanted a project that actually combined my love for the NFL with ML Ops and predictions in a way that felt real and fun.",
      },
      {
        type: "body",
        text: "This project uses a full ML stack: neural networks trained on NFL play-by-play data, a generative model for synthetic stat priors, a Monte Carlo simulation engine, and a Genetic Algorithm optimizer... all served through a Go API backend and React Native + Expo frontend.",
      },
      {
        type: "body",
        text: "If you want to connect, check out my work! Or, just talk football and ML for fun:",
      },
      {
        type: "links",
        links: [
          { label: "GitHub", icon: "logo-github" as const, url: "https://github.com/sat-malla" },
          { label: "LinkedIn", icon: "logo-linkedin" as const, url: "https://www.linkedin.com/in/sathvik-malla-41b7aa284" },
          { label: "Portfolio", icon: "globe-outline" as const, url: "https://sathvik-malla.netlify.app/" },
        ],
      },
    ],
  },
];

export default function Info() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";

  const c = {
    bg: isDark ? "#132130" : "#edf5ff",
    card: isDark ? "#02080f" : "#ffffff",
    text: isDark ? "#edf5ff" : "#02080f",
    subtext: isDark ? "#a0b4c8" : "#4a5568",
    border: isDark ? "#1e3a52" : "#bfdbfe",
    shadow: isDark
      ? "rgba(250,250,250,0.8) 0px 3px 8px"
      : "rgba(0,0,0,0.24) 0px 3px 8px",
    accent: "#3b82f6",
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: c.bg }}
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator={false}
    >
      {SECTIONS.map((section) => (
        <View
          key={section.id}
          style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}
        >
          <View style={styles.sectionHeader}>
            <Ionicons name={section.icon} size={22} color={c.accent} />
            <Text style={[styles.sectionTitle, { color: c.text }]}>{section.title}</Text>
          </View>
          {section.content.map((block, i) => {
            if (block.type === "label") {
              return (
                <Text key={i} style={[styles.label, { color: c.accent }]}>
                  {block.text}
                </Text>
              );
            }
            if (block.type === "body") {
              return (
                <Text key={i} style={[styles.body, { color: c.subtext }]}>
                  {block.text}
                </Text>
              );
            }
            if (block.type === "links" && block.links) {
              return (
                <View key={i} style={styles.linksRow}>
                  {block.links.map((link) => (
                    <TouchableOpacity
                      key={link.label}
                      style={[styles.linkBtn, { borderColor: c.border }]}
                      onPress={() => Linking.openURL(link.url)}
                    >
                      <Ionicons name={link.icon} size={18} color={c.accent} />
                      <Text style={[styles.linkLabel, { color: c.accent }]}>{link.label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              );
            }
            return null;
          })}
        </View>
      ))}

      <Text style={[styles.footer, { color: c.subtext }]}>
        © {new Date().getFullYear()} Pro Football RTGA. All rights reserved.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 24,
    paddingBottom: 60,
    gap: 16,
  },
  card: {
    borderRadius: 14,
    borderWidth: 1,
    padding: 18,
    gap: 12,
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginBottom: 2,
  },
  sectionTitle: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 18,
  },
  label: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 13,
    marginTop: 4,
  },
  body: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
    lineHeight: 22,
  },
  linksRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    marginTop: 4,
  },
  linkBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  linkLabel: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 13,
  },
  footer: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 11,
    textAlign: "center",
    opacity: 0.5,
    marginTop: 8,
  },
});
