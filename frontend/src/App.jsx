import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/layout/Layout';
import { AuthProvider } from './context/AuthContext';
import { CartProvider } from './context/CartContext';
import { StoreProvider } from './context/StoreContext';
import { ToastProvider } from './context/ToastContext';
import Cart from './pages/Cart';
import Catalog from './pages/Catalog';
import Checkout from './pages/Checkout';
import Home from './pages/Home';
import HowItWorks from './pages/HowItWorks';
import SellWithUs from './pages/SellWithUs';
import SellerStore from './pages/SellerStore';
import Orders from './pages/Orders';
import Product from './pages/Product';
import Profile from './pages/Profile';
import ReturnsPolicy from './pages/ReturnsPolicy';
import DeliveryTimes from './pages/DeliveryTimes';
import CompatibilityFaq from './pages/CompatibilityFaq';
import Manage from './pages/Manage';
import ResetPassword from './pages/ResetPassword';
import PainelLayout from './pages/painel/PainelLayout';
import PainelLogin from './pages/painel/PainelLogin';
import PainelDashboard from './pages/painel/PainelDashboard';
import PainelOrders from './pages/painel/PainelOrders';
import PainelConfig from './pages/painel/PainelConfig';
import PainelErrors from './pages/painel/PainelErrors';
import PainelSellers from './pages/painel/PainelSellers';
import PainelFinance from './pages/painel/PainelFinance';
import PainelPayouts from './pages/painel/PainelPayouts';
import PainelInvoices from './pages/painel/PainelInvoices';

export default function App() {
  return (
    <BrowserRouter>
      <StoreProvider>
        <AuthProvider>
          <CartProvider>
            <ToastProvider>
              <Routes>
                <Route path="painel/entrar" element={<PainelLogin />} />
                <Route path="painel" element={<PainelLayout />}>
                  <Route index element={<Navigate to="visao" replace />} />
                  <Route path="visao" element={<PainelDashboard />} />
                  <Route path="financeiro" element={<PainelFinance />} />
                  <Route path="repasses" element={<PainelPayouts />} />
                  <Route path="nfe" element={<PainelInvoices />} />
                  <Route path="pedidos" element={<PainelOrders />} />
                  <Route path="vendedores" element={<PainelSellers />} />
                  <Route path="config" element={<PainelConfig />} />
                  <Route path="erros" element={<PainelErrors />} />
                  <Route path="pagamentos" element={<Navigate to="/painel/visao" replace />} />
                  <Route path="conteudo" element={<Navigate to="/painel/vendedores" replace />} />
                  <Route path="audiencia" element={<Navigate to="/painel/visao" replace />} />
                </Route>

                <Route element={<Layout />}>
                  <Route index element={<Home />} />
                  <Route path="pecas" element={<Catalog />} />
                  <Route path="peca/:slug" element={<Product />} />
                  <Route path="carrinho" element={<Cart />} />
                  <Route path="checkout" element={<Checkout />} />
                  <Route path="pedidos" element={<Orders />} />
                  <Route path="perfil" element={<Profile />} />
                  <Route path="vender" element={<SellerHub />} />
                  <Route path="venda-conosco" element={<SellWithUs />} />
                  <Route path="loja/:slug" element={<SellerStore />} />
                  <Route path="como-funciona" element={<HowItWorks />} />
                  <Route path="trocas-devolucoes" element={<ReturnsPolicy />} />
                  <Route path="prazos-entrega" element={<DeliveryTimes />} />
                  <Route path="faq-compatibilidade" element={<CompatibilityFaq />} />
                  <Route path="gerenciar" element={<Manage />} />
                  <Route path="reset-password" element={<ResetPassword />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
              </Routes>
            </ToastProvider>
          </CartProvider>
        </AuthProvider>
      </StoreProvider>
    </BrowserRouter>
  );
}
