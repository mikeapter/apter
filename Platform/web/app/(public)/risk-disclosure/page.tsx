import { Metadata } from "next";
import { LegalPageLayout } from "@/components/legal/LegalPageLayout";

export const metadata: Metadata = {
  title: "Risk Disclosure — Apter Financial",
};

export default function RiskDisclosurePage() {
  return (
    <LegalPageLayout
      title="Risk Disclosure"
      lastUpdated="February 24, 2026"
    >
      <section>
        <h2>Not Investment Advice</h2>
        <p>
          Apter Financial provides analytical tools and informational signals
          only. Nothing on this platform constitutes investment advice, a
          solicitation, or a recommendation to buy, sell, or hold any security,
          financial product, or instrument. The content and signals provided
          should not be relied upon as the sole basis for any investment
          decision.
        </p>
      </section>

      <section>
        <h2>No Fiduciary Relationship</h2>
        <p>
          Apter Financial is not a registered investment adviser, broker-dealer,
          or financial planner. Use of the Service does not create a fiduciary,
          advisory, or professional relationship between you and Apter Financial.
        </p>
      </section>

      <section>
        <h2>Trading Risk</h2>
        <p>
          Trading and investing in financial markets involves substantial risk of
          loss. You may lose some or all of your invested capital. The degree of
          risk varies by asset class, strategy, and market conditions. You should
          only trade with capital you can afford to lose.
        </p>
      </section>

      <section>
        <h2>Past Performance</h2>
        <p>
          Past performance of any signal, strategy, or analytical output is not
          indicative of future results. Historical data and backtested results
          have inherent limitations and do not account for all factors that affect
          real-world trading, including slippage, liquidity, and execution timing.
        </p>
      </section>

      <section>
        <h2>User Responsibility</h2>
        <p>
          All trading decisions are made independently by the user. You are solely
          responsible for evaluating the merits and risks of each trade or
          investment decision. We strongly recommend consulting with a qualified
          financial advisor before making any trading or investment decisions.
        </p>
      </section>

      <section>
        <h2>Data Accuracy</h2>
        <p>
          While we strive to provide accurate and timely information, Apter
          Financial does not guarantee the accuracy, completeness, or timeliness
          of any data, signals, or analytics provided through the Service. Market
          data may be delayed or subject to errors. Always verify information
          independently before acting on it.
        </p>
      </section>

      <section>
        <h2>Regulatory Considerations</h2>
        <p>
          Financial regulations vary by jurisdiction. It is your responsibility to
          ensure that your use of the Service and any related trading activities
          comply with the laws and regulations applicable in your jurisdiction.
        </p>
      </section>

      <section>
        <h2>Questions</h2>
        <p>
          If you have any questions about the risks associated with using the
          Service, contact us at{" "}
          <a href="mailto:support@apterfinancial.com">
            support@apterfinancial.com
          </a>
          .
        </p>
      </section>
    </LegalPageLayout>
  );
}
