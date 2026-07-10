import { Text, Title } from "@telegram-apps/telegram-ui";
import { humanizePurchaseStatus } from "../../hooks/business-mini-app/helpers";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";

export function BusinessSettingsScreen({ model }: { model: BusinessMiniAppModel }) {
  const { business } = model;
  return (
    <div className="business-card">
      <Text className="business-card__label">Perfil</Text>
      <Title level="3" className="business-shell__title">{business?.business_name || "Perfil negocio"}</Title>
      <div className="business-grid">
        <Text>Estado: {business?.verification_status ? humanizePurchaseStatus(business.verification_status) : "sin negocio"}</Text>
        <Text>Riesgo: {business?.risk_level || "n/a"}</Text>
        <Text>Pais: {business?.country || "VE"}</Text>
      </div>
      <Text className="auth-entry__session-meta">La edicion de datos sensibles y metodos queda gobernada por NODO.</Text>
    </div>
  );
}
