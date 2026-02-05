export function SystemAssessmentPanel({ lines }: { lines: string[] }) {
  return (
    <section className="bt-panel p-4">
      <div className="bt-panel-title">SYSTEM ASSESSMENT</div>
      <div className="mt-3 space-y-2 text-sm">
        {lines.slice(0, 6).map((t, i) => (
          <p key={i} className="text-muted-foreground leading-relaxed">
            {t}
          </p>
        ))}
      </div>
    </section>
  );
}
