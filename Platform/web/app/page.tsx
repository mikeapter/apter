import StickyNav from "@/components/landing/StickyNav";
import Hero from "@/components/landing/Hero";
import SocialProof from "@/components/landing/SocialProof";
import HowItWorks from "@/components/landing/HowItWorks";
import FeatureGrid from "@/components/landing/FeatureGrid";
import PricingTeaser from "@/components/landing/PricingTeaser";
import Footer from "@/components/landing/Footer";

export default function LandingPage() {
  return (
    <>
      <StickyNav />
      <main>
        <Hero />
        <SocialProof />
        <HowItWorks />
        <FeatureGrid />
        <PricingTeaser />
      </main>
      <Footer />
    </>
  );
}
