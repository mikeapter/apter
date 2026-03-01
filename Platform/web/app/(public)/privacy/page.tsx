import { Metadata } from "next";
import { LegalPageLayout } from "@/components/legal/LegalPageLayout";

export const metadata: Metadata = {
  title: "Privacy Policy — Apter Financial",
};

export default function PrivacyPage() {
  return (
    <LegalPageLayout title="Privacy Policy" lastUpdated="February 24, 2026">
      <section>
        <h2>1. Information We Collect</h2>
        <p>We collect the following categories of information:</p>
        <ul>
          <li>
            <strong>Account information:</strong> Email address and display name
            provided during registration.
          </li>
          <li>
            <strong>Authentication logs:</strong> Login timestamps, IP addresses,
            and device identifiers used for security and fraud prevention.
          </li>
          <li>
            <strong>Usage analytics:</strong> Pages visited, features used, and
            interaction patterns that help us improve the Service.
          </li>
          <li>
            <strong>Payment information:</strong> Billing details processed
            through our payment provider. We do not store full card numbers on our
            servers.
          </li>
        </ul>
      </section>

      <section>
        <h2>2. How We Use Your Information</h2>
        <p>We use collected information to:</p>
        <ul>
          <li>Provide and maintain the Service.</li>
          <li>Authenticate your identity and secure your account.</li>
          <li>Process payments and manage subscriptions.</li>
          <li>Send transactional communications (e.g., password resets, billing receipts).</li>
          <li>Analyze usage patterns to improve product quality.</li>
        </ul>
      </section>

      <section>
        <h2>3. Cookies and Tracking</h2>
        <p>
          We use essential cookies to maintain your session and authentication
          state. We may use analytics cookies to understand how the Service is
          used. You can manage cookie preferences through your browser settings.
        </p>
      </section>

      <section>
        <h2>4. Third-Party Services</h2>
        <p>We share data with the following categories of third parties:</p>
        <ul>
          <li>
            <strong>Payment processing:</strong> Stripe handles payment
            transactions. Their use of your data is governed by the{" "}
            <a
              href="https://stripe.com/privacy"
              target="_blank"
              rel="noopener noreferrer"
            >
              Stripe Privacy Policy
            </a>
            .
          </li>
          <li>
            <strong>Authentication:</strong> We use industry-standard
            authentication services to secure your account.
          </li>
          <li>
            <strong>Analytics:</strong> Aggregated, non-identifying usage data may
            be processed by analytics providers.
          </li>
        </ul>
      </section>

      <section>
        <h2>5. Data Retention</h2>
        <p>
          We retain your account information for as long as your account is
          active. If you delete your account, we will remove your personal data
          within 30 days, except where retention is required by law or for
          legitimate business purposes (e.g., fraud prevention, legal
          obligations).
        </p>
      </section>

      <section>
        <h2>6. Data Security</h2>
        <p>
          We implement industry-standard security measures including encryption in
          transit and at rest, access controls, and regular security reviews. No
          system is perfectly secure, and we cannot guarantee absolute security of
          your data.
        </p>
      </section>

      <section>
        <h2>7. Your Rights</h2>
        <p>Depending on your jurisdiction, you may have the right to:</p>
        <ul>
          <li>Access the personal data we hold about you.</li>
          <li>Request correction of inaccurate data.</li>
          <li>Request deletion of your data.</li>
          <li>Object to or restrict certain processing activities.</li>
          <li>Export your data in a portable format.</li>
        </ul>
        <p>
          To exercise any of these rights, contact us at{" "}
          <a href="mailto:support@apterfinancial.com">
            support@apterfinancial.com
          </a>
          .
        </p>
      </section>

      <section>
        <h2>8. Children&apos;s Privacy</h2>
        <p>
          The Service is not intended for users under 18 years of age. We do not
          knowingly collect personal information from minors.
        </p>
      </section>

      <section>
        <h2>9. Changes to This Policy</h2>
        <p>
          We may update this Privacy Policy periodically. We will notify you of
          material changes via the Service or by email. The &quot;Last
          updated&quot; date at the top of this page reflects the most recent
          revision.
        </p>
      </section>

      <section>
        <h2>10. Contact</h2>
        <p>
          For privacy-related inquiries, contact us at{" "}
          <a href="mailto:support@apterfinancial.com">
            support@apterfinancial.com
          </a>
          .
        </p>
      </section>
    </LegalPageLayout>
  );
}
