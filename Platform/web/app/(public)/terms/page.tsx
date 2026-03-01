import { Metadata } from "next";
import { LegalPageLayout } from "@/components/legal/LegalPageLayout";

export const metadata: Metadata = {
  title: "Terms of Service — Apter Financial",
};

export default function TermsPage() {
  return (
    <LegalPageLayout title="Terms of Service" lastUpdated="February 24, 2026">
      <section>
        <h2>1. Acceptance of Terms</h2>
        <p>
          By accessing or using the Apter Financial platform (&quot;Service&quot;),
          you agree to be bound by these Terms of Service. If you do not agree to
          these terms, do not use the Service.
        </p>
      </section>

      <section>
        <h2>2. Description of Service</h2>
        <p>
          Apter Financial provides analytical tools and informational trading
          signals. The Service is designed to support structured decision-making
          and does not execute trades, manage portfolios, or provide personalized
          investment advice on your behalf.
        </p>
      </section>

      <section>
        <h2>3. Eligibility</h2>
        <p>
          You must be at least 18 years old and legally able to enter into
          contracts in your jurisdiction to use the Service. By using the Service,
          you represent that you meet these requirements.
        </p>
      </section>

      <section>
        <h2>4. User Accounts</h2>
        <p>
          You are responsible for maintaining the confidentiality of your account
          credentials and for all activity that occurs under your account. Notify
          us immediately at{" "}
          <a href="mailto:support@apterfinancial.com">
            support@apterfinancial.com
          </a>{" "}
          if you suspect unauthorized access.
        </p>
      </section>

      <section>
        <h2>5. Acceptable Use</h2>
        <p>You agree not to:</p>
        <ul>
          <li>
            Use the Service for any unlawful purpose or in violation of any
            applicable regulations.
          </li>
          <li>
            Attempt to reverse-engineer, scrape, or extract data from the Service
            beyond normal use.
          </li>
          <li>
            Redistribute, resell, or publicly share any proprietary signals,
            analytics, or content from the Service without written permission.
          </li>
          <li>
            Interfere with or disrupt the integrity or performance of the Service.
          </li>
        </ul>
      </section>

      <section>
        <h2>6. Intellectual Property</h2>
        <p>
          All content, data, algorithms, and design elements of the Service are
          the property of Apter Financial and are protected by applicable
          intellectual property laws. Your use of the Service does not grant you
          ownership of any content or materials you access.
        </p>
      </section>

      <section>
        <h2>7. Disclaimer of Warranties</h2>
        <p>
          The Service is provided on an &quot;as-is&quot; and
          &quot;as-available&quot; basis without warranties of any kind, whether
          express or implied. Apter Financial does not warrant that the Service
          will be uninterrupted, error-free, or that any signals or analytics will
          produce specific financial outcomes.
        </p>
      </section>

      <section>
        <h2>8. Limitation of Liability</h2>
        <p>
          To the fullest extent permitted by law, Apter Financial shall not be
          liable for any indirect, incidental, special, consequential, or punitive
          damages, or any loss of profits or revenues, whether incurred directly
          or indirectly, arising from your use of the Service. In no event shall
          our total liability exceed the amount you paid to Apter Financial in the
          twelve months preceding the claim.
        </p>
      </section>

      <section>
        <h2>9. Termination</h2>
        <p>
          We may suspend or terminate your access to the Service at any time, with
          or without cause, with or without notice. Upon termination, your right
          to use the Service ceases immediately. Sections relating to intellectual
          property, disclaimers, and limitation of liability survive termination.
        </p>
      </section>

      <section>
        <h2>10. Changes to Terms</h2>
        <p>
          We may update these Terms from time to time. Material changes will be
          communicated via the Service or by email. Continued use of the Service
          after changes take effect constitutes acceptance of the updated Terms.
        </p>
      </section>

      <section>
        <h2>11. Governing Law</h2>
        <p>
          These Terms are governed by the laws of the jurisdiction in which Apter
          Financial operates, without regard to conflict-of-law principles.
        </p>
      </section>

      <section>
        <h2>12. Contact</h2>
        <p>
          Questions about these Terms? Contact us at{" "}
          <a href="mailto:support@apterfinancial.com">
            support@apterfinancial.com
          </a>
          .
        </p>
      </section>
    </LegalPageLayout>
  );
}
