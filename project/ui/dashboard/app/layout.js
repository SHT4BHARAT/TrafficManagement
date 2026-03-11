import "./globals.css";

export const metadata = {
  title: "DAITFO | City Operator Dashboard",
  description: "Dynamic AI Traffic Flow Optimizer & Emergency Grid",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
