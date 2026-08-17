export const metadata = {
  title: "SECOND UNIT — Delivery Assurance for the Render Farm",
  description: "Green metrics, broken art: an agent crew that watches the picture, not just the dashboard.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: "#0b0d10", color: "#e7e9ec", fontFamily: "system-ui, sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
