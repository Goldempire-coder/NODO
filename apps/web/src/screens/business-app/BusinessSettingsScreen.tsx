import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { humanizePurchaseStatus } from "../../hooks/business-mini-app/helpers";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";

export function BusinessSettingsScreen({ model }: { model: BusinessMiniAppModel }) {
  const { business, lockBusinessPinSession, loadReferrals, paymentMethods, setBusinessAvailability, setView, updatingAvailability } = model;
  const canOperate = business?.verification_status === "approved" && paymentMethods.length > 0;
  const isAcceptingOrders = business?.is_accepting_orders !== false;
  const pinConfigured = Boolean(business?.access_link?.pin_configured);
  const pinUnlocked = Boolean(business?.access_link?.pin_unlocked);
  return (
    <div className="business-card">
      <Text className="business-card__label">Perfil</Text>
      <Title level="3" className="business-shell__title">{business?.business_name || "Perfil negocio"}</Title>
      <div className="business-status-panel">
        <div>
          <span className={canOperate ? "status-dot" : "status-dot status-dot--muted"} aria-hidden="true" />
          <div>
            <strong>{canOperate ? "Operativo" : "No operativo"}</strong>
          </div>
        </div>
      </div>
      <div className="business-grid">
        <Text>Estado: {business?.verification_status ? humanizePurchaseStatus(business.verification_status) : "sin negocio"}</Text>
        <Text>Riesgo: {business?.risk_level || "n/a"}</Text>
        <Text>Pais: {business?.country || "VE"}</Text>
        <Text>Metodos guardados: {paymentMethods.length}</Text>
      </div>
      <Text className="auth-entry__session-meta">Puedes guardar Zelle y USDT TRC20, y elegir cual usar en cada anuncio.</Text>
      <Button
        mode={isAcceptingOrders ? "outline" : "filled"}
        size="s"
        disabled={!canOperate || updatingAvailability}
        onClick={() => void setBusinessAvailability(!isAcceptingOrders)}
      >
        {updatingAvailability ? "Guardando..." : isAcceptingOrders ? "Poner offline" : "Poner online"}
      </Button>
      <div className="business-shell__tabs">
        <Button mode="outline" size="s" onClick={() => setView("payment-methods")}>Metodos</Button>
        <Button mode="outline" size="s" onClick={() => void loadReferrals()}>Referidos</Button>
        <Button mode="outline" size="s" onClick={() => setView("business-rules")}>Reglas</Button>
      </div>
      <Button mode="outline" size="s" onClick={() => setView("business-pin")}>{pinConfigured ? "Desbloquear PIN" : "Crear PIN"}</Button>
      {pinConfigured && pinUnlocked ? (
        <Button mode="outline" size="s" onClick={() => void lockBusinessPinSession()}>Bloquear acciones sensibles</Button>
      ) : null}
      <Button mode="outline" size="s" onClick={() => setView("business-support")}>Soporte NODO</Button>
    </div>
  );
}

const BUSINESS_RULES = [
  {
    title: "Bot y Mini App",
    body: "El bot solo avisa y abre NODO. La Mini App muestra y opera. El backend valida y manda."
  },
  {
    title: "Online / offline",
    body: "Offline oculta tus anuncios activos y bloquea nuevas ordenes. Las ordenes ya abiertas siguen visibles para resolverlas."
  },
  {
    title: "Anuncios",
    body: "Cada anuncio es una oportunidad. Si un cliente lo toma, queda ocupado. Para operar varios clientes, publica varios anuncios."
  },
  {
    title: "Creditos",
    body: "Publicar asigna un credito. Abrir una operacion lo reserva. Completar o evadir consume. Cancelacion legitima puede devolver."
  },
  {
    title: "Pagos P2P",
    body: "NODO no custodia ni libera el dinero del cambio. Cliente y negocio pagan directamente entre ellos."
  },
  {
    title: "Comprobantes",
    body: "Un comprobante no confirma que el dinero llego. Verifica en tu banco o billetera antes de pagar al cliente."
  },
  {
    title: "USDC Base",
    body: "Pegar un hash no acredita por si solo. El backend valida red, token, destino, monto, exito y que el hash no se haya usado."
  },
  {
    title: "Notificaciones",
    body: "El aviso automatico de nueva orden queda pendiente de conectar. Por ahora revisa Ordenes dentro de la Mini App."
  }
];

export function BusinessRulesScreen() {
  return (
    <div className="business-card">
      <Text className="business-card__label">Perfil</Text>
      <Title level="3" className="business-shell__title">Reglas y terminos</Title>
      <div className="business-list">
        {BUSINESS_RULES.map((rule) => (
          <div className="business-rule-item" key={rule.title}>
            <strong>{rule.title}</strong>
            <Text>{rule.body}</Text>
          </div>
        ))}
      </div>
    </div>
  );
}
