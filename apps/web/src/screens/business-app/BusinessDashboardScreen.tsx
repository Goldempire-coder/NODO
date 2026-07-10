import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";

export function BusinessDashboardScreen({ model }: { model: BusinessMiniAppModel }) {
  const { business, loadBusinessOrders, loadCreditDashboard, loadMyAds, setView } = model;
  return (
    <div className="business-card">
      <Text className="business-card__label">Resumen</Text>
      <Title level="3" className="business-shell__title">
        {business?.business_name || "NODO Negocio"}
      </Title>
      <Text className="auth-entry__session-meta">
        Gestiona anuncios, ordenes y creditos desde tu espacio de negocio.
      </Text>
      <div className="business-grid">
        <Button mode="filled" size="s" onClick={() => setView("create-ad")}>
          Crear anuncio
        </Button>
        <Button mode="outline" size="s" onClick={() => void loadMyAds()}>
          Mis anuncios
        </Button>
        <Button mode="outline" size="s" onClick={() => void loadBusinessOrders("payment_reported")}>
          Ordenes por revisar
        </Button>
        <Button mode="outline" size="s" onClick={() => void loadCreditDashboard()}>
          Creditos
        </Button>
      </div>
      <div className="trusted-empty">
        <span className="status-dot" aria-hidden="true" />
        <Text>Confirma pago solo cuando realmente lo recibiste. Esa accion consume los creditos del anuncio.</Text>
      </div>
    </div>
  );
}
