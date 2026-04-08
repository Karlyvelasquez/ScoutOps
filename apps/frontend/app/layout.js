export const metadata = {
  title: "ScoutOps",
  description: "SRE Incident Triage Agent"
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "sans-serif", margin: 0, padding: 24 }}>{children}</body>
    </html>
  );
}
