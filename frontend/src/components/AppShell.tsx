import { BookOpen, FileSearch, LayoutDashboard, Library, Settings } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { LEGAL_NOTE } from "../lib/utils";

const links = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/app/library", label: "Library", icon: Library, end: false },
  { to: "/app/research", label: "Research", icon: FileSearch, end: false },
  { to: "/app/settings", label: "Settings", icon: Settings, end: false },
];

export function AppShell() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="lg:grid lg:grid-cols-[240px_1fr]">
        <aside className="bg-navy text-white lg:min-h-screen">
          <div className="flex items-center gap-2 px-4 py-4">
            <BookOpen className="h-5 w-5" aria-hidden="true" />
            <div>
              <p className="font-serif text-lg leading-none">CiteWise</p>
              <p className="mt-1 text-xs text-white/70">Local research desk</p>
            </div>
          </div>
          <nav aria-label="Workspace" className="flex gap-1 overflow-x-auto px-2 pb-3 lg:block lg:px-3">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-md px-3 py-2 text-sm whitespace-nowrap ${isActive ? "bg-white/15" : "text-white/80 hover:bg-white/10"}`
                }
              >
                <link.icon className="h-4 w-4" aria-hidden="true" />
                {link.label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <div className="min-w-0">
          <main id="main" className="mx-auto max-w-6xl px-4 py-6 lg:px-8">
            <Outlet />
          </main>
          <footer className="border-t border-line px-4 py-4 text-xs text-muted lg:px-8">{LEGAL_NOTE}</footer>
        </div>
      </div>
    </div>
  );
}
