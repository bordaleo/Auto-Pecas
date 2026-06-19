import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { useStore } from '../../context/StoreContext';
import Analytics from '../Analytics';
import AuthModal from '../AuthModal';
import CartDrawer from '../CartDrawer';
import Footer from './Footer';
import Header from './Header';
import SideNav from './SideNav';

export default function Layout() {
  const [authOpen, setAuthOpen] = useState(false);
  const [authTab, setAuthTab] = useState('login');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { whatsappUrl } = useStore();

  const openAuth = (tab = 'login') => {
    setAuthTab(tab);
    setAuthOpen(true);
  };

  return (
    <div className="app-shell">
      <Analytics />
      <div className="app-body">
        <SideNav open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <div className="app-content">
          <Header onOpenAuth={openAuth} onOpenSidebar={() => setSidebarOpen(true)} />
          <main className="app-main">
            <Outlet context={{ openAuth }} />
          </main>
          <Footer onOpenAuth={openAuth} />
        </div>
      </div>
      <CartDrawer />
      <AuthModal
        open={authOpen}
        tab={authTab}
        onClose={() => setAuthOpen(false)}
        onTabChange={setAuthTab}
      />
      <a href={whatsappUrl} className="whatsapp-fab" target="_blank" rel="noreferrer" aria-label="WhatsApp">
        💬
      </a>
    </div>
  );
}
