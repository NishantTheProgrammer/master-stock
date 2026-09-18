import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import { LayoutDashboard, LineChart, BarChart3, Activity, Settings } from "lucide-react";

export const metadata: Metadata = {
  title: "Master Stock - Agentic AI",
  description: "Agentic AI Stock Market Prediction System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="app-container">
          <aside className="sidebar">
            <div className="logo">
              <Activity size={28} color="#3b82f6" />
              <span>Master Stock</span>
            </div>
            
            <nav className="nav-links">
              <Link href="/" className="nav-item">
                <LayoutDashboard size={20} />
                <span>Overview</span>
              </Link>
              <Link href="/stocks" className="nav-item">
                <LineChart size={20} />
                <span>Stocks & Scores</span>
              </Link>
              <Link href="/predictions" className="nav-item">
                <Activity size={20} />
                <span>Predictions</span>
              </Link>
              <Link href="/sandbox" className="nav-item">
                <BarChart3 size={20} />
                <span>Sandbox</span>
              </Link>
              <Link href="/system" className="nav-item">
                <Settings size={20} />
                <span>System</span>
              </Link>
            </nav>
          </aside>
          
          <main className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
