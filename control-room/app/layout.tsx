import "./globals.css";

export const metadata = {
  metadataBase: new URL("https://second-unit-control-room-1026707323109.us-central1.run.app"),
  title: "SECOND UNIT — Delivery Assurance for the Render Farm",
  description: "Green metrics, broken art: an agent crew that watches the picture, not just the dashboard.",
  icons: {
    icon: "/favicon.svg",
  },
  openGraph: {
    title: "SECOND UNIT",
    description: "Green metrics. Broken art. Only one of those two things is checking the picture.",
    images: ["/og.png"],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
