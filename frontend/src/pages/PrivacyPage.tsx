import { Link } from "react-router-dom";
import { ContactLine, LegalLayout, LegalSectionBlock, Placeholder, type LegalSection } from "../components/legal/LegalLayout";

const SECTIONS: LegalSection[] = [
  { id: "who", title: "Who we are" },
  { id: "collect", title: "What we collect" },
  { id: "why", title: "Why we use it, and our basis" },
  { id: "processors", title: "Who processes your data" },
  { id: "sale", title: "We do not sell your data" },
  { id: "retention", title: "How long we keep it" },
  { id: "rights", title: "Your rights and choices" },
  { id: "children", title: "Children" },
  { id: "cookies", title: "Cookies and browser storage" },
  { id: "security", title: "How we protect it" },
  { id: "transfers", title: "Transfers outside India" },
  { id: "grievance", title: "Contact and grievances" },
  { id: "changes", title: "Changes to this policy" },
];

const PROCESSORS: Array<[string, string, string]> = [
  ["Vercel", "Hosts the website you see", "Requests to the site (IP address, browser type)"],
  ["Render", "Hosts our API (the server that does the work)", "Everything you send to the API, in transit"],
  ["Neon", "Managed PostgreSQL database", "Account, birth details, charts, chats, reports, usage records"],
  ["Upstash", "Redis cache and rate limiting", "Short-lived cache entries, request counters, reset codes"],
  ["Google Gemini API", "Generates AI text (answers, readings)", "Your chat messages and computed chart facts"],
  ["Anthropic Claude API (optional fallback)", "Generates AI text if the primary provider is unavailable", "Your chat messages and computed chart facts"],
  ["Brevo", "Sends transactional email (verification, password reset)", "Your name, email address and the message content"],
  ["LocationIQ and Geoapify", "Place search and coordinates for your birth place", "The place text you type"],
  ["Google sign-in", "Optional sign-in with a Google account", "Your Google name, email and profile identifier"],
];

export default function PrivacyPage() {
  return (
    <LegalLayout
      title="Privacy Policy"
      sections={SECTIONS}
      summary={
        <>
          <p>
            Nakshion needs your birth details to calculate your chart, and your messages to answer your questions. We keep that data to run your account, we do not sell it, and we do not show ads.
          </p>
          <p>
            You can see and correct your details in your Profile, and you can delete your account and everything linked to it at any time. Nakshion is for people aged 18 and over.
          </p>
        </>
      }
    >
      <LegalSectionBlock id="who" title="Who we are">
        <p>
          Nakshion ("we", "us") is a Vedic astrology web app that calculates birth charts and offers AI-assisted guidance. For the purposes of the Digital Personal Data Protection Act, 2023 (India) we act as the data fiduciary, and under the GDPR as the controller, for the personal data described here. This policy applies to the website at nakshion.vercel.app and its API.
        </p>
        <p>
          Operator name and registered address: <Placeholder>[to be completed by the owner before launch]</Placeholder>.
        </p>
      </LegalSectionBlock>

      <LegalSectionBlock id="collect" title="What we collect">
        <ul>
          <li><strong>Account data:</strong> your name, email address, and a password hash (we never store your password itself). If you sign in with Google, we receive your name, email and Google account identifier.</li>
          <li><strong>Birth details:</strong> date, time (if you know it), place, and the latitude, longitude and time zone worked out from that place. You choose whether to enter them.</li>
          <li><strong>Saved partner and family charts:</strong> birth details of other people that you enter. Please add them only if the person is comfortable with it.</li>
          <li><strong>Chat messages:</strong> what you write to Nakshion and the answers you receive, along with bookmarks and feedback you give.</li>
          <li><strong>Charts, readings and compatibility reports</strong> generated from the above.</li>
          <li><strong>Usage and security logs:</strong> request times, IP address, browser type, daily question counts, and sign-in, verification and password-reset events. These help us prevent abuse and keep the service running.</li>
        </ul>
        <p>We do not ask for payment details, government identifiers, precise device location, contacts, or photos.</p>
      </LegalSectionBlock>

      <LegalSectionBlock id="why" title="Why we use it, and our basis">
        <ul>
          <li>To create your account, keep you signed in and send verification and password-reset emails: needed to provide the service you asked for.</li>
          <li>To calculate charts and generate readings, answers and compatibility reports: needed to provide the service, based on the birth details you choose to give.</li>
          <li>To protect the service (rate limits, abuse prevention, debugging): our legitimate interest in running a safe service.</li>
          <li>To meet legal obligations, if any apply.</li>
        </ul>
        <p>
          <strong>Consent.</strong> When you create an account you tick a box to confirm you agree to the Terms and this Privacy Policy, and you give us your birth details voluntarily for the purposes above. Under the DPDP Act, you may withdraw consent at any time by deleting your account; withdrawal does not affect processing done before it. We use your data only for these purposes, and only as much as is needed.
        </p>
      </LegalSectionBlock>

      <LegalSectionBlock id="processors" title="Who processes your data">
        <p>We use these service providers to run Nakshion. They process data on our behalf under their own terms and privacy policies.</p>
        <div className="overflow-x-auto rounded-control border border-border" tabIndex={0} role="region" aria-label="Service providers table">
          <table className="w-full min-w-[34rem] border-collapse text-left text-body-sm">
            <caption className="sr-only">Service providers, their purpose, and the data they handle</caption>
            <thead className="bg-elevated text-fg">
              <tr>
                <th scope="col" className="p-2.5 font-semibold">Provider</th>
                <th scope="col" className="p-2.5 font-semibold">Purpose</th>
                <th scope="col" className="p-2.5 font-semibold">Data involved</th>
              </tr>
            </thead>
            <tbody>
              {PROCESSORS.map(([name, purpose, data]) => (
                <tr key={name} className="border-t border-border align-top">
                  <th scope="row" className="p-2.5 font-medium text-fg">{name}</th>
                  <td className="p-2.5">{purpose}</td>
                  <td className="p-2.5">{data}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>
          <strong>AI providers.</strong> To answer you, we send the AI provider your message and the computed chart facts it needs (for example planet signs and periods). We do not intentionally send your name, email, or exact birth date and place. If you type such details into a chat message, they will be sent too, so please avoid entering sensitive information in chat. The provider's own terms govern how it handles that content.
        </p>
        <p>We may also disclose data if the law requires it, for example to answer a valid order from a court or authority.</p>
      </LegalSectionBlock>

      <LegalSectionBlock id="sale" title="We do not sell your data">
        <p>We do not sell or rent your personal data, and we do not use it for advertising or to build advertising profiles. There are no ad trackers on Nakshion.</p>
      </LegalSectionBlock>

      <LegalSectionBlock id="retention" title="How long we keep it">
        <ul>
          <li><strong>Account data, charts, chats and reports:</strong> until you delete them or your account.</li>
          <li><strong>Usage and security logs:</strong> no longer than 180 days.</li>
          <li><strong>Password-reset and verification codes:</strong> short-lived; they expire within minutes to hours and are then discarded.</li>
          <li><strong>Backups:</strong> deleted data may remain in provider backups for a short period before it is overwritten.</li>
        </ul>
      </LegalSectionBlock>

      <LegalSectionBlock id="rights" title="Your rights and choices">
        <p>Under the DPDP Act, and the GDPR where it applies to you, you can:</p>
        <ul>
          <li><strong>Access</strong> your data: your charts, chats and details are visible in the app.</li>
          <li><strong>Correct</strong> it: edit your name and birth details from your Profile and charts.</li>
          <li><strong>Erase</strong> it: use <Link to="/profile#danger">Delete account</Link> in your Profile. This removes your charts, chats, reports and usage records.</li>
          <li><strong>Withdraw consent</strong> at any time, by deleting your account.</li>
          <li><strong>Ask us</strong> for a copy of your data, to restrict or object to processing, or to nominate someone to act for you, using the contact below.</li>
          <li><strong>Complain:</strong> to us first, and then to the Data Protection Board of India, or to your local data protection authority if you are in the EU/UK.</li>
        </ul>
        <ContactLine purpose="To make a request that the app does not handle yourself." />
      </LegalSectionBlock>

      <LegalSectionBlock id="children" title="Children">
        <p>Nakshion is for people aged 18 and over. We do not knowingly collect personal data from anyone under 18. If you believe a child has given us data, contact us and we will delete it.</p>
      </LegalSectionBlock>

      <LegalSectionBlock id="cookies" title="Cookies and browser storage">
        <p>
          We do not use advertising or analytics cookies. To keep you signed in, your sign-in token (a JWT) is stored in your browser's storage on your device, along with small preferences such as theme and chat language. You can clear it at any time by signing out or clearing site data. Our providers (for example Vercel) may process technical request data, such as your IP address, to deliver the site.
        </p>
      </LegalSectionBlock>

      <LegalSectionBlock id="security" title="How we protect it">
        <ul>
          <li>Everything travels over HTTPS.</li>
          <li>Passwords are stored only as salted one-way hashes.</li>
          <li>You can only see your own charts, chats and reports; the server checks ownership on every request.</li>
          <li>Rate limits and short-lived reset codes reduce abuse and guessing.</li>
          <li>Our database and cache are managed services with access limited to the app.</li>
        </ul>
        <p>No system is perfectly secure. If a breach affects your personal data, we will notify you and the authorities as the law requires.</p>
      </LegalSectionBlock>

      <LegalSectionBlock id="transfers" title="Transfers outside India">
        <p>
          Our servers are in Singapore and the United States, and our AI providers process requests abroad. By using Nakshion you understand that your data is transferred to and processed in those countries, which may have different data protection rules from your own. We rely on the providers' contractual safeguards and send only what each provider needs.
        </p>
      </LegalSectionBlock>

      <LegalSectionBlock id="grievance" title="Contact and grievances">
        <ContactLine purpose="For questions, requests or complaints about your personal data, contact our grievance contact." />
        <p>Grievance officer: <Placeholder>[name and designation, to be completed by the owner]</Placeholder>. We aim to acknowledge requests within 7 days and resolve them within 30 days.</p>
      </LegalSectionBlock>

      <LegalSectionBlock id="changes" title="Changes to this policy">
        <p>
          We may update this policy as the service or the law changes. The date at the top shows the latest version. For material changes we will tell you in the app or by email before they take effect. Read how we use astrology and AI in the <Link to="/terms#astrology-and-ai">Terms of Use</Link>.
        </p>
      </LegalSectionBlock>
    </LegalLayout>
  );
}
