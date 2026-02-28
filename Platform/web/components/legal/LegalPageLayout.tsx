interface LegalPageLayoutProps {
  title: string;
  lastUpdated: string;
  children: React.ReactNode;
}

export function LegalPageLayout({
  title,
  lastUpdated,
  children,
}: LegalPageLayoutProps) {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <header className="mb-10">
        <h1 className="text-2xl sm:text-3xl font-bold text-foreground">
          {title}
        </h1>
        <p className="mt-2 text-xs text-muted-foreground">
          Last updated: {lastUpdated}
        </p>
      </header>

      <div className="space-y-8 text-sm text-muted-foreground leading-relaxed [&_h2]:text-base [&_h2]:font-semibold [&_h2]:text-foreground [&_h2]:mb-3 [&_p]:mb-3 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1.5 [&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:space-y-1.5 [&_a]:text-foreground [&_a]:underline [&_a]:underline-offset-2 [&_a:hover]:opacity-80">
        {children}
      </div>
    </div>
  );
}
