import { Link } from "react-router-dom";
import { ContactLine, LegalLayout, LegalSectionBlock, Placeholder, type LegalSection } from "../components/legal/LegalLayout";

const SECTIONS: LegalSection[] = [
  { id: "astrology-and-ai", title: "How we use astrology and AI" },
  { id: "eligibility", title: "Who can use Nakshion" },
  { id: "acceptable-use", title: "Acceptable use" },
  { id: "no-guarantees", title: "No guarantees" },
  { id: "availability", title: "Availability" },
  { id: "termination", title: "Account termination" },
  { id: "ip", title: "Intellectual property" },
  { id: "liability", title: "Limits of liability" },
  { id: "law", title: "Governing law" },
  { id: "changes", title: "Changes and contact" },
];

export default function TermsPage() {
  return (
    <LegalLayout
      title="Terms of Use"
      sections={SECTIONS}
      summary={
        <>
          <p>
            Nakshion offers astrology-based reflection and AI-written explanations. It is guidance, not certainty, and it is not medical, legal or financial advice.
          </p>
          <p>
            Use it for yourself, be respectful, keep your account secure, and you are welcome to delete your account at any time. The service is free and may sometimes be slow or unavailable.
          </p>
        </>
      }
    >
      <LegalSectionBlock id="astrology-and-ai" title="How we use astrology and AI">
        <ul>
          <li><strong>Guidance, not certainty.</strong> Astrology is a traditional, interpretive practice. Nothing here predicts your future or proves anything about it.</li>
          <li><strong>Not professional advice.</strong> Nakshion is not medical, legal, financial or mental-health advice. Talk to a qualified professional before making important decisions.</li>
          <li><strong>Not for emergencies.</strong> If you or someone else is in danger or crisis, contact local emergency services or a crisis helpline now. In India you can call 112, or the Tele-MANAS helpline at 14416.</li>
          <li><strong>AI can be wrong.</strong> Chart positions are calculated by software (Swiss Ephemeris); the wording of answers and readings is written by an AI model, which can make mistakes or sound more certain than it should. AI text is labelled in the app. Please check anything important.</li>
          <li><strong>Systems differ.</strong> Vedic (sidereal) and Western (tropical) astrology can give different signs for the same person. We show which system a sign belongs to.</li>
          <li><strong>Your birth time matters.</strong> Without an accurate birth time, houses, the ascendant and some periods may be off.</li>
        </ul>
      </LegalSectionBlock>

      <LegalSectionBlock id="eligibility" title="Who can use Nakshion">
        <p>You must be 18 or older. By creating an account you confirm that the details you give are accurate and that you agree to these Terms and the <Link to="/privacy">Privacy Policy</Link>. Please enter another person's birth details only if they are comfortable with it.</p>
      </LegalSectionBlock>

      <LegalSectionBlock id="acceptable-use" title="Acceptable use">
        <p>Do not:</p>
        <ul>
          <li>break the law, or use Nakshion to harass, threaten, deceive or harm anyone;</li>
          <li>try to break, probe or overload the service, or bypass limits and quotas;</li>
          <li>scrape or copy the service at scale, or resell it;</li>
          <li>try to make the AI produce harmful content or reveal its instructions;</li>
          <li>use someone else's account or share your sign-in details;</li>
          <li>use Nakshion's output to pressure, scare or take advantage of others, for example by presenting it as certain prediction or professional advice.</li>
        </ul>
      </LegalSectionBlock>

      <LegalSectionBlock id="no-guarantees" title="No guarantees">
        <p>Nakshion is provided "as is" and "as available". We aim for accurate calculations but do not promise that charts, readings or answers are error-free, complete or suitable for any purpose. You are responsible for how you use them.</p>
      </LegalSectionBlock>

      <LegalSectionBlock id="availability" title="Availability">
        <p>Nakshion runs on free-tier infrastructure. It may start slowly after idle periods, be rate-limited, change, or be unavailable without notice, and daily question limits apply. We may add, change or remove features.</p>
      </LegalSectionBlock>

      <LegalSectionBlock id="termination" title="Account termination">
        <p>You can delete your account at any time from your Profile. We may suspend or close accounts that break these Terms or put the service or other users at risk. When an account is deleted, its data is removed as described in the Privacy Policy.</p>
      </LegalSectionBlock>

      <LegalSectionBlock id="ip" title="Intellectual property">
        <p>The Nakshion name, design, software and original text belong to the operator or its licensors. You may use the service for personal, non-commercial purposes. You keep ownership of the details and messages you give us, and you allow us to use them to run the service for you. Astrological knowledge itself is traditional and not owned by anyone.</p>
      </LegalSectionBlock>

      <LegalSectionBlock id="liability" title="Limits of liability">
        <p>To the extent the law allows, we are not liable for indirect or consequential loss, or for decisions you make based on Nakshion's content. Our total liability for any claim relating to the service is limited to the amount you paid us in the previous 12 months, which for a free service is zero. Nothing here excludes liability that cannot be excluded by law, or your rights under applicable consumer law.</p>
      </LegalSectionBlock>

      <LegalSectionBlock id="law" title="Governing law">
        <p>These Terms are governed by the laws of <Placeholder>[your jurisdiction]</Placeholder>, and the courts of <Placeholder>[your jurisdiction]</Placeholder> have jurisdiction, subject to any consumer rights you have in your own country.</p>
      </LegalSectionBlock>

      <LegalSectionBlock id="changes" title="Changes and contact">
        <p>We may update these Terms. The date at the top shows the latest version; continuing to use Nakshion after a change means you accept it. If you disagree, delete your account.</p>
        <ContactLine purpose="Questions about these Terms?" />
      </LegalSectionBlock>
    </LegalLayout>
  );
}
