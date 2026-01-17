import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Home, LogIn, Download, FileText, Map, Settings } from 'lucide-react';

interface LayoutProps {
  children: ReactNode;
}

const navItems = [
  { path: '/', label: 'Dashboard', icon: Home },
  { path: '/auth', label: 'Autenticação', icon: LogIn },
  { path: '/consulta', label: 'Consulta WFS', icon: Map },
  { path: '/download', label: 'Downloads', icon: Download },
  { path: '/batch', label: 'Lote', icon: FileText },
];

export function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-govbr-primary text-white">
        <div className="p-6">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Settings className="w-6 h-6" />
            Gov.br Auth
          </h1>
          <p className="text-blue-200 text-sm mt-1">Painel de Testes</p>
        </div>

        <nav className="mt-6">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-6 py-3 transition-colors ${
                  isActive
                    ? 'bg-govbr-secondary border-r-4 border-white'
                    : 'hover:bg-govbr-secondary/50'
                }`}
              >
                <Icon className="w-5 h-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-auto">
        {children}
      </main>
    </div>
  );
}
