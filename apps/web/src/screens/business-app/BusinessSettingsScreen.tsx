import { useState } from "react";
import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { humanizePurchaseStatus } from "../../hooks/business-mini-app/helpers";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";
import { actionStartedAt, recordActionCompleted, recordActionFailed, recordActionStarted } from "../../hooks/actionTelemetry";

async function copyText(value: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  let copied = false;
  try {
    copied = document.execCommand("copy");
  } finally {
    document.body.removeChild(textarea);
  }
  if (!copied) {
    throw new Error("CLIPBOARD_COPY_FAILED");
  }
}

function shortBusinessId(value: string | null | undefined) {
  if (!value) {
    return "No disponible";
  }
  if (value.length <= 18) {
    return value;
  }
  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}

export function BusinessSettingsScreen({ model }: { model: BusinessMiniAppModel }) {
  const { business, lockBusinessPinSession, loadReferrals, paymentMethods, setBusinessAvailability, setView, updatingAvailability } = model;
  const [businessIdCopied, setBusinessIdCopied] = useState(false);
  const [businessIdCopyError, setBusinessIdCopyError] = useState(false);
  const canOperate = business?.verification_status === "approved";
  const isAcceptingOrders = business?.is_accepting_orders !== false;
  const pinConfigured = Boolean(business?.access_link?.pin_configured);
  const pinUnlocked = Boolean(business?.access_link?.pin_unlocked);
  const businessId = business?.id || "";
  const copyBusinessId = async () => {
    if (!businessId) {
      return;
    }
    const startedAt = actionStartedAt();
    recordActionStarted("business_id_copy", "business-settings");
    setBusinessIdCopyError(false);
    try {
      await copyText(businessId);
      setBusinessIdCopied(true);
      recordActionCompleted("business_id_copy", "business-settings", startedAt);
      window.setTimeout(() => setBusinessIdCopied(false), 1600);
    } catch {
      setBusinessIdCopied(false);
      setBusinessIdCopyError(true);
      recordActionFailed("business_id_copy", "business-settings", startedAt, "CLIPBOARD_COPY_FAILED");
    }
  };
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
        <Text>Pais: {business?.country || "VE"}</Text>
        <Text>Metodos guardados: {paymentMethods.length}</Text>
      </div>
      <div className={businessIdCopied ? "business-identity-box is-copied" : "business-identity-box"}>
        <div>
          <span>Identificacion del negocio</span>
          <code>{shortBusinessId(businessId)}</code>
        </div>
        <button className="mini-action-button" type="button" disabled={!businessId} onClick={() => void copyBusinessId()}>
          {businessIdCopied ? "Copiado" : "Copiar identificacion"}
        </button>
      </div>
      {businessIdCopied ? <Text className="business-identity-box__feedback" role="status">Identificacion copiada para soporte.</Text> : null}
      {businessIdCopyError ? <Text className="business-identity-box__feedback" role="alert">No pudimos copiar la identificacion. Puedes seleccionarla manualmente.</Text> : null}
      <Text className="auth-entry__session-meta">Puedes guardar Zelle y USDT TRC20 antes de comprar creditos.</Text>
      <Button
        mode={isAcceptingOrders ? "outline" : "filled"}
        size="s"
        disabled={!canOperate || updatingAvailability}
        onClick={() => void setBusinessAvailability(!isAcceptingOrders)}
      >
        {updatingAvailability ? "Guardando..." : isAcceptingOrders ? "Poner offline" : "Poner online"}
      </Button>
      <div className="business-shell__tabs">
        <Button mode="outline" size="s" onClick={() => setView("payment-methods")}>Zelle / USDT</Button>
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

const BUSINESS_TERMS = [
  {
    title: "Pagos directos",
    body: "NODO no custodia el dinero del cambio. Cliente y negocio pagan directamente entre ellos."
  },
  {
    title: "Verificacion obligatoria",
    body: "Antes de entregar bolivares o cripto, confirma que el dinero llego a tu banco o billetera."
  },
  {
    title: "Datos correctos",
    body: "Manten tus Zelle y wallets actualizados. Si usas datos viejos, pausa o corrige tus anuncios."
  },
  {
    title: "Uso responsable",
    body: "NODO puede pausar, revisar o bloquear operaciones si detecta abuso, riesgo o informacion falsa."
  }
];

export function BusinessTermsScreen({ model }: { model: BusinessMiniAppModel }) {
  return (
    <div className="business-card">
      <Text className="business-card__label">NODO Negocio</Text>
      <Title level="3" className="business-shell__title">Terminos y condiciones</Title>
      <div className="business-list">
        {BUSINESS_TERMS.map((rule) => (
          <div className="business-rule-item" key={rule.title}>
            <strong>{rule.title}</strong>
            <Text>{rule.body}</Text>
          </div>
        ))}
      </div>
      <Button mode="filled" stretched disabled={model.busy} onClick={() => void model.acceptBusinessTerms()}>
        {model.busy ? "Guardando..." : "Aceptar terminos"}
      </Button>
    </div>
  );
}
