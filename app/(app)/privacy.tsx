import {
  ScrollView,
  StyleSheet,
  Text,
  View,
  useColorScheme,
} from "react-native";
import { useRouter } from "expo-router";

export default function Privacy() {
  const isDark = useColorScheme() === "dark";
  const router = useRouter();
  const c = {
    bg: isDark ? "#132130" : "#edf5ff",
    text: isDark ? "#edf5ff" : "#02080f",
    subtext: isDark ? "#a0b4c8" : "#4a5568",
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: c.bg }}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
    >
      <Text style={[styles.heading, { color: c.text }]}>Privacy Policy</Text>

      <Text style={[styles.body, { color: c.subtext }]}>
        This privacy policy applies to the Pro Football Random Team Generator
        &amp; Analysis app for mobile devices, together with any related
        services operated by Sathvik Malla (collectively, the "Application").
        Sathvik Malla is hereby referred to as the "Service Provider".
      </Text>

      <Text style={[styles.section, { color: c.text }]}>
        Information Collection and Use
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        The Application collects information when you download and use it. This
        information may include information such as
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • Your device's Internet Protocol address
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • The pages of the Application that you visit, the time and date of your
        visit, the time spent on those pages
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • The time spent on the Application
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • Your mobile operating system you use
      </Text>

      <Text style={[styles.section, { color: c.text }]}>
        Cookies and tracking technologies
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        The Application or its third-party SDKs may use cookies, SDKs, pixels,
        and similar technologies to support functionality, analytics, or service
        delivery. Where required by applicable law, the Service Provider will
        obtain consent before using non-essential tracking technologies.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>Your Rights</Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        You may request access to, correction of, or deletion of your personal
        data held by the Service Provider. To exercise these rights, or to
        withdraw consent where processing is based on consent, contact the
        Service Provider at sathvikmalla17@gmail.com.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>
        Your California privacy rights (CCPA/CPRA)
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        If you are a California resident, you have the right to know what
        personal information is collected, the right to delete personal
        information, the right to opt out of the sale or sharing of personal
        information, and the right to non-discrimination for exercising these
        rights. To exercise your CCPA/CPRA rights, contact the Service Provider
        at sathvikmalla17@gmail.com.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>
        Artificial Intelligence
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        The Application uses Artificial Intelligence (AI) technologies to
        enhance user experience and provide certain features. The AI components
        may process user data to deliver personalized content, recommendations,
        or automated functionalities. All AI processing is performed in
        accordance with this privacy policy and applicable laws. If you have
        questions about the AI features or data processing, please contact the
        Service Provider.
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        The Service Provider may use the information you provide to send
        important information, required notices, and, where permitted by law,
        marketing communications.
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        For a better experience while using the Application, the Service
        Provider may require you to provide certain personally identifiable
        information, including but not limited to Email. The information the
        Service Provider requests will be retained and used as described in this
        privacy policy.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>
        Third Party Access
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        Only aggregated, anonymized data is periodically transmitted to external
        services to aid the Service Provider in improving the Application and
        their service. The Service Provider may share your information with
        third parties in the ways that are described in this privacy statement.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>
        International Data Transfers
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        The Service Provider or its third-party service providers may transfer
        personal data to countries outside your country of residence, including
        outside the European Economic Area (EEA). Where applicable law requires
        safeguards for international transfers, the Service Provider will use
        appropriate mechanisms.
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • Standard Contractual Clauses (SCCs) approved by the European
        Commission
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • Adequacy decisions or other legally recognized transfer mechanisms
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • Your consent, where required and legally permitted
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        Data protection laws in other countries may differ from those in your
        jurisdiction. Where required by law, the Service Provider will apply
        appropriate safeguards and obtain any consent required for the transfer.
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        Please note that the Application utilizes third-party services that have
        their own Privacy Policy about handling data. Below are the links to the
        Privacy Policy of the third-party service providers used by the
        Application:
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • Google Analytics for Firebase
        (https://firebase.google.com/support/privacy)
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • Expo (https://expo.io/privacy)
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        The Service Provider may disclose User Provided and Automatically
        Collected Information:
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • As required by law, such as to comply with a subpoena, or similar
        legal process;
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • When they believe in good faith that disclosure is necessary to
        protect their rights, protect your safety or the safety of others,
        investigate fraud, or respond to a government request;
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • With their trusted services providers who work on their behalf, do not
        have an independent use of the information the Service Provider
        discloses to them, and have agreed to adhere to the rules set forth in
        this privacy statement.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>Opt-Out Rights</Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        You can stop further collection of information from your mobile device
        by uninstalling the Application. Uninstalling will stop the Application
        from collecting data from your device, but it does not automatically
        delete information that has already been transmitted to the Service
        Provider or to third parties.
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        To request deletion of your personal data, to withdraw consent, or to
        exercise any of your rights, contact the Service Provider at
        sathvikmalla17@gmail.com.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>
        Data Retention Policy
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        The Service Provider retains personal data based on its necessity for
        the stated purposes:
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • User Provided Data: Retained for the duration of your use of the
        Application plus 12 months thereafter, unless longer retention is
        required by law
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • Automatically Collected Data: Retained for up to 24 months from
        collection, unless longer retention is required for legal compliance
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • Aggregated and Anonymized Data: Retained indefinitely as it no longer
        identifies you
      </Text>
      <Text style={[styles.bullet, { color: c.subtext }]}>
        • Data required for legal compliance: Retained as long as required by
        applicable law
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        You may request deletion of your personal data, subject to any legal
        obligation to retain it. If you want the Service Provider to delete User
        Provided Data submitted through the Application, please contact them at
        sathvikmalla17@gmail.com. Please note that some User Provided Data may
        be required for the Application to function properly.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>Data Deletion</Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        You can request deletion of your personal data or account by contacting
        the Service Provider at sathvikmalla17@gmail.com. The Service Provider
        will process your request within the timeframes required by applicable
        law.
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        Upon verification of your identity, the Service Provider will delete
        your personal data from its systems, except where retention is required
        for legal compliance or legitimate business purposes.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>Children</Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        The Application is not intended for children under 13 years of age, or
        such higher age as required by applicable law. The Service Provider does
        not knowingly solicit data from children or market the Application to
        them.
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        Where parental or guardian consent is required under applicable law, the
        Application is not intended for use without that consent. The Service
        Provider does not knowingly collect personally identifiable information
        from children under 13 years of age in violation of applicable law. In
        the event the Service Provider discovers that a child has provided
        personal information, the Service Provider will immediately delete this
        from their servers. If you are a parent or guardian and you are aware
        that your child has provided the Service Provider with personal
        information, please contact the Service Provider
        (sathvikmalla17@gmail.com) so that they will be able to take the
        necessary actions.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>Security</Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        The Service Provider is concerned about safeguarding the confidentiality
        of your information. The Service Provider provides physical, electronic,
        and procedural safeguards to protect information the Service Provider
        processes and maintains.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>
        Data Breach Notification
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        If a data breach occurs that affects your personal data, the Service
        Provider will notify you in accordance with applicable legal
        requirements, including, where required, providing information about the
        nature of the breach and the steps being taken to address it.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>Changes</Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        The Service Provider may update this Privacy Policy from time to time.
        The Service Provider will notify you of material changes by posting the
        updated Privacy Policy with an effective date. Where required by law,
        the Service Provider will seek your consent to material changes before
        they take effect.
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        Previous versions of this Privacy Policy will be maintained and made
        available upon request by contacting the Service Provider at
        sathvikmalla17@gmail.com.
      </Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        This privacy policy is effective as of 2026-08-01.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>Your Consent</Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        Where processing is based on consent, you provide that consent by
        affirmatively opting in to the relevant feature or action. You may
        withdraw consent at any time without affecting processing carried out
        before withdrawal. Processing based on other lawful bases is carried out
        as described above.
      </Text>

      <Text style={[styles.section, { color: c.text }]}>Contact Us</Text>
      <Text style={[styles.body, { color: c.subtext }]}>
        If you have any questions regarding privacy while using the Application,
        or have questions about the practices, please contact the Service
        Provider via email at sathvikmalla17@gmail.com or visit the{" "}
        <Text style={styles.link} onPress={() => router.push("/support")}>
          Support
        </Text>{" "}
        page.
      </Text>

      <View style={styles.divider} />
      <Text style={[styles.footer, { color: c.subtext }]}>
        © {new Date().getFullYear()} Pro Football RTGA. All rights reserved.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingHorizontal: 20,
    paddingTop: 24,
    paddingBottom: 60,
    gap: 10,
  },
  heading: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 30,
    marginBottom: 6,
    textAlign: "center",
  },
  section: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 15,
    marginTop: 10,
  },
  body: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
    lineHeight: 22,
  },
  link: {
    fontFamily: "Montserrat_700Bold",
    fontSize: 14,
    color: "#3b82f6",
    textDecorationLine: "underline",
  },
  bullet: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 14,
    lineHeight: 22,
    paddingLeft: 8,
  },
  divider: {
    height: 1,
    backgroundColor: "#1e3a5233",
    marginTop: 24,
    marginBottom: 12,
  },
  footer: {
    fontFamily: "Montserrat_400Regular",
    fontSize: 12,
    opacity: 0.5,
    textAlign: "center",
  },
});
