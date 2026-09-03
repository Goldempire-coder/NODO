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
  const { business, lockBusinessPinSession, loadReferrals, loggingOut, logout, paymentMethods, setBusinessAvailability, setView, updatingAvailability } = model;
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
      <Text className="auth-entry__session-meta">Configura tus metodos de cobro para publicar anuncios y recibir solicitudes.</Text>
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
      <Button mode="outline" size="s" onClick={() => setView("business-legal-documents")}>Terminos y condiciones</Button>
      <Button mode="outline" size="s" onClick={() => setView("business-pin")}>{pinConfigured ? "Desbloquear PIN" : "Crear PIN"}</Button>
      {pinConfigured && pinUnlocked ? (
        <Button mode="outline" size="s" onClick={() => void lockBusinessPinSession()}>Bloquear acciones sensibles</Button>
      ) : null}
      <Button mode="outline" size="s" onClick={() => setView("business-support")}>Soporte NODO</Button>
      <Button mode="outline" size="s" stretched disabled={loggingOut} onClick={() => void logout()}>
        {loggingOut ? "Cerrando..." : "Cerrar sesion en este dispositivo"}
      </Button>
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
    body: "Publicar asigna un credito. Abrir una orden lo reserva. Completar o evadir consume. Cancelacion legitima puede devolver."
  },
  {
    title: "Pagos entre cliente y negocio",
    body: "NODO no custodia ni libera fondos acordados entre cliente y negocio. Las partes completan sus pagos directamente."
  },
  {
    title: "Comprobantes",
    body: "Un comprobante no confirma que el dinero llego. Verifica en tu banco o billetera antes de completar la entrega acordada."
  },
  {
    title: "USDC Base",
    body: "NODO prepara la autorizacion con el monto, token, red y contrato oficiales. La compra no acredita creditos hasta que el pago sea verificado."
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

function ReadOnlyTermsList({
  label,
  terms,
}: {
  label: string;
  terms: { title: string; body: string }[];
}) {
  return (
    <>
      <Text className="business-card__label">{label}</Text>
      <div className="business-list">
        {terms.map((rule) => (
          <div className="business-rule-item" key={`${label}-${rule.title}`}>
            <strong>{rule.title}</strong>
            <Text>{rule.body}</Text>
          </div>
        ))}
      </div>
    </>
  );
}

const BUSINESS_TERMS = [
  {
    title: "Cuenta de negocio",
    body: "La cuenta y los accesos autorizados representan al negocio dentro de NODO."
  },
  {
    title: "Creditos NODO",
    body: "Los creditos son para publicar y operar anuncios dentro de NODO. No son dinero, no se retiran ni se transfieren."
  },
  {
    title: "Pagos entre cliente y negocio",
    body: "En ordenes entre cliente y negocio, las partes pagan directamente entre ellas. NODO no custodia ni libera esos fondos."
  },
  {
    title: "Uso responsable",
    body: "NODO puede pausar, revisar o bloquear accesos, anuncios u ordenes si detecta abuso, riesgo, fraude o datos incorrectos."
  }
];

const BUSINESS_CREDIT_TERMS = [
  {
    title: "Compra de creditos",
    body: "Los creditos comprados se acreditan al negocio cuando NODO verifica el pago."
  },
  {
    title: "Pago digital",
    body: "La wallet muestra el monto, la red y el contrato antes de confirmar. NODO nunca pide frase secreta ni clave privada."
  },
  {
    title: "Sin retiros",
    body: "Los creditos solo sirven dentro de NODO para publicar anuncios. No se canjean, retiran ni transfieren."
  },
  {
    title: "Revision",
    body: "NODO puede revisar pagos, rechazar intentos invalidos o retener la acreditacion si detecta riesgo."
  }
];

export function BusinessLegalDocumentsScreen({ model }: { model: BusinessMiniAppModel }) {
  return (
    <div className="business-card">
      <Text className="business-card__label">NODO Negocio</Text>
      <Title level="3" className="business-shell__title">Terminos y condiciones</Title>
      <Text className="auth-entry__session-meta">Documentos aplicables al negocio y a la compra de creditos.</Text>
      <ReadOnlyTermsList label="Terminos de NODO Negocio" terms={BUSINESS_TERMS} />
      <ReadOnlyTermsList label="Terminos de compra de creditos" terms={BUSINESS_CREDIT_TERMS} />
      <Button mode="outline" stretched size="s" onClick={() => model.setView("business-settings")}>
        Volver al perfil
      </Button>
    </div>
  );
}

function TermsConfirmation({
  checked,
  label,
  onChange,
}: {
  checked: boolean;
  label: string;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="terms-confirmation">
      <input
        checked={checked}
        type="checkbox"
        onChange={(event) => onChange(event.currentTarget.checked)}
      />
      <span>{label}</span>
    </label>
  );
}

export function BusinessTermsScreen({ model }: { model: BusinessMiniAppModel }) {
  const [confirmed, setConfirmed] = useState(false);
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
      <TermsConfirmation
        checked={confirmed}
        label="Confirmo que acepto estos terminos como representante autorizado del negocio."
        onChange={setConfirmed}
      />
      <Button mode="filled" stretched disabled={model.busy || !confirmed} onClick={() => void model.acceptBusinessTerms()}>
        {model.busy ? "Guardando..." : "Aceptar y continuar"}
      </Button>
    </div>
  );
}

export function BusinessCreditTermsScreen({ model }: { model: BusinessMiniAppModel }) {
  const [confirmed, setConfirmed] = useState(false);
  return (
    <div className="business-card">
      <Text className="business-card__label">Creditos NODO</Text>
      <Title level="3" className="business-shell__title">Terminos de compra de creditos</Title>
      <div className="business-list">
        {BUSINESS_CREDIT_TERMS.map((rule) => (
          <div className="business-rule-item" key={rule.title}>
            <strong>{rule.title}</strong>
            <Text>{rule.body}</Text>
          </div>
        ))}
      </div>
      <TermsConfirmation
        checked={confirmed}
        label="Confirmo que entiendo y acepto las condiciones para comprar creditos NODO."
        onChange={setConfirmed}
      />
      <Button mode="filled" stretched disabled={model.busy || !confirmed} onClick={() => void model.acceptBusinessCreditTerms()}>
        {model.busy ? "Guardando..." : "Aceptar y comprar creditos"}
      </Button>
    </div>
  );
}
