import {
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  useColorScheme,
  KeyboardAvoidingView,
  Platform,
  Linking,
  Alert,
  ActivityIndicator,
} from "react-native";
import { useState } from "react";
import Ionicons from "react-native-vector-icons/Ionicons";

const SUPPORT_EMAIL = "sathvikmalla17@gmail.com";
const SUBJECTS = ["Bug Report", "Feature Request", "General Question", "Other"];

const FORMSPREE_ID = process.env.EXPO_PUBLIC_FORMSPREE_ID ?? "";
const BREVO_API_KEY = process.env.EXPO_PUBLIC_BREVO_API_KEY ?? "";
const BREVO_TEMPLATE_ID = Number(process.env.EXPO_PUBLIC_BREVO_TEMPLATE_ID ?? "1");

export default function Support() {
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const c = {
    bg: isDark ? "#132130" : "#edf5ff",
    card: isDark ? "#02080f" : "#ffffff",
    text: isDark ? "#edf5ff" : "#02080f",
    subtext: isDark ? "#a0b4c8" : "#4a5568",
    border: isDark ? "#1e3a52" : "#bfdbfe",
    inputBg: isDark ? "#0d1f2d" : "#f0f7ff",
    shadow: isDark
      ? "rgba(250,250,250,0.8) 0px 3px 8px"
      : "rgba(0,0,0,0.24) 0px 3px 8px",
    button: isDark ? "#edf5ff" : "#02080f",
    buttonText: isDark ? "#02080f" : "#edf5ff",
    accent: "#3b82f6",
    green: "#16a34a",
  };

  const canSend = name.trim() && email.trim() && subject.trim() && message.trim() && !sending;

  const handleSend = async () => {
    setSending(true);
    try {
      const formspreeRes = await fetch(`https://formspree.io/f/${FORMSPREE_ID}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ name: name.trim(), email: email.trim(), subject, message: message.trim() }),
      });
      if (!formspreeRes.ok) {
        const text = await formspreeRes.text();
        throw new Error(`Formspree ${formspreeRes.status}: ${text}`);
      }

      const brevoRes = await fetch("https://api.brevo.com/v3/smtp/email", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "api-key": BREVO_API_KEY,
        },
        body: JSON.stringify({
          to: [{ email: email.trim(), name: name.trim() }],
          templateId: BREVO_TEMPLATE_ID,
          params: { name: name.trim(), subject, message: message.trim() },
        }),
      });
      if (!brevoRes.ok) {
        const text = await brevoRes.text();
        throw new Error(`Brevo ${brevoRes.status}: ${text}`);
      }

      setSent(true);
      setName("");
      setEmail("");
      setSubject("");
      setMessage("");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error("Support send error:", msg);
      Alert.alert("Failed to send", msg);
    } finally {
      setSending(false);
    }
  };

  const inputStyle = [styles.input, { backgroundColor: c.inputBg, borderColor: c.border, color: c.text }];
  const labelStyle = [styles.label, { color: c.subtext }];

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: c.bg }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
          <View style={styles.cardHeader}>
            <Text style={[styles.cardTitle, { color: c.text }]}>Send a Message</Text>
          </View>

          {sent && (
            <View style={[styles.successBanner, { backgroundColor: c.green }]}>
              <Text style={[styles.successText, { color: "#fff" }]}>
                Message sent! Check your inbox for a confirmation. I'll get back to you soon.
              </Text>
            </View>
          )}

          <Text style={labelStyle}>Name</Text>
          <View style={styles.inputWrapper}>
            <TextInput
              style={[inputStyle, styles.inputFlex]}
              placeholder="Your name"
              placeholderTextColor={c.subtext}
              value={name}
              onChangeText={setName}
              autoCapitalize="words"
            />
            {name.length > 0 && (
              <TouchableOpacity style={styles.clearBtn} onPress={() => setName("")}>
                <Ionicons name="close-circle" size={18} color={c.subtext} />
              </TouchableOpacity>
            )}
          </View>

          <Text style={labelStyle}>Email</Text>
          <View style={styles.inputWrapper}>
            <TextInput
              style={[inputStyle, styles.inputFlex]}
              placeholder="your@email.com"
              placeholderTextColor={c.subtext}
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
            />
            {email.length > 0 && (
              <TouchableOpacity style={styles.clearBtn} onPress={() => setEmail("")}>
                <Ionicons name="close-circle" size={18} color={c.subtext} />
              </TouchableOpacity>
            )}
          </View>

          <Text style={labelStyle}>Subject</Text>
          <View style={styles.subjectRow}>
            {SUBJECTS.map((s) => (
              <TouchableOpacity
                key={s}
                style={[
                  styles.subjectChip,
                  {
                    backgroundColor: subject === s ? c.accent : c.inputBg,
                    borderColor: subject === s ? c.accent : c.border,
                  },
                ]}
                onPress={() => setSubject(s)}
              >
                <Text style={[styles.subjectChipText, { color: subject === s ? "#fff" : c.subtext }]}>
                  {s}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={labelStyle}>Message</Text>
          <View style={styles.inputWrapper}>
            <TextInput
              style={[inputStyle, styles.inputFlex, styles.messageInput]}
              placeholder="Describe your issue or feedback..."
              placeholderTextColor={c.subtext}
              value={message}
              onChangeText={setMessage}
              multiline
              numberOfLines={5}
              textAlignVertical="top"
            />
            {message.length > 0 && (
              <TouchableOpacity style={[styles.clearBtn, styles.clearBtnTop]} onPress={() => setMessage("")}>
                <Ionicons name="close-circle" size={18} color={c.subtext} />
              </TouchableOpacity>
            )}
          </View>

          <TouchableOpacity
            style={[styles.sendBtn, { backgroundColor: canSend ? c.button : "#9ca3af" }]}
            disabled={!canSend}
            onPress={handleSend}
          >
            {sending ? (
              <ActivityIndicator color={c.buttonText} />
            ) : (
              <Text style={[styles.sendBtnText, { color: canSend ? c.buttonText : "#fff" }]}>
                Send Message
              </Text>
            )}
          </TouchableOpacity>
        </View>

        <View style={[styles.card, { backgroundColor: c.card, borderColor: c.border, boxShadow: c.shadow }]}>
          <View style={styles.cardHeader}>
            <Text style={[styles.cardTitle, { color: c.text }]}>Reach Out Directly</Text>
          </View>
          <Text style={[styles.directBody, { color: c.subtext }]}>
            Prefer to email directly? You can always reach me at:
          </Text>
          <TouchableOpacity
            style={[styles.emailRow, { backgroundColor: c.inputBg, borderColor: c.border }]}
            onPress={() => Linking.openURL(`mailto:${SUPPORT_EMAIL}`)}
            disabled={true}
          >
            <Ionicons name="mail" size={18} color={c.accent} />
            <Text style={[styles.emailText, { color: c.accent }]}>{SUPPORT_EMAIL}</Text>
          </TouchableOpacity>
          <Text style={[styles.directBody, { color: c.subtext }]}>
            I try to respond within a few days. Whether it's a bug, a suggestion, or just want to talk football and ML!
          </Text>
        </View>

        <Text style={[styles.footer, { color: c.subtext }]}>
          © {new Date().getFullYear()} Pro Football RTGA. All rights reserved.
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
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
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginBottom: 2,
  },
  cardTitle: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 18,
  },
  successBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderRadius: 8,
    padding: 10,
  },
  successText: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 13,
    flex: 1,
  },
  label: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 12,
    marginBottom: -4,
  },
  input: {
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingRight: 36,
    paddingVertical: 10,
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
  },
  inputWrapper: {
    flexDirection: "row",
    alignItems: "center",
  },
  inputFlex: {
    flex: 1,
  },
  clearBtn: {
    position: "absolute",
    right: 10,
    alignSelf: "center",
  },
  clearBtnTop: {
    alignSelf: "flex-start",
    top: 10,
  },
  messageInput: {
    minHeight: 110,
    paddingTop: 10,
    paddingRight: 32,
  },
  subjectRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  subjectChip: {
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  subjectChipText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 12,
  },
  sendBtn: {
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 4,
  },
  sendBtnText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 16,
  },
  directBody: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
    lineHeight: 21,
  },
  emailRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  emailText: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 14,
  },
  footer: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 11,
    textAlign: "center",
    opacity: 0.5,
    marginTop: 4,
  },
});
