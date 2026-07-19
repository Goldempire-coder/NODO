import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import type { BusinessMiniAppModel } from "../../hooks/useBusinessMiniAppModel";

export function BusinessAccessPanel({ model }: { model: BusinessMiniAppModel }) {
  const { accessState, loadBusinessProfile } = model;
  const copyByState: Record<string, { label: string; title: string; body: string }> = {
    loading: {
      label: "Validacion",
      title: "Revisando acceso",
      body: "Estamos confirmando que este Telegram tiene un negocio aprobado asociado."
    },
    no_business_link: {
      label: "Sin acceso",
      title: "No hay negocio asociado",
      body: "Este espacio es solo para negocios aprobados y vinculados por NODO."
    },
    business_not_approved: {
      label: "En revision",
      title: "Negocio pendiente",
      body: "Tu negocio todavia no esta habilitado para operar."
    },
    business_suspended: {
      label: "Pausado",
      title: "Negocio suspendido",
      body: "NODO pauso temporalmente este negocio. Te avisaremos por Telegram cuando cambie el estado."
    },
    business_blocked: {
      label: "Bloqueado",
      title: "Acceso bloqueado",
      body: "Este negocio no puede operar desde la app. Contacta a NODO si crees que es un error."
    },
    link_suspended: {
      label: "Pausado",
      title: "Acceso suspendido",
      body: "NODO pauso temporalmente tu acceso a este negocio. Te avisaremos por Telegram cuando cambie el estado."
    },
    link_revoked: {
      label: "Sin acceso",
      title: "Acceso revocado",
      body: "Este Telegram ya no esta vinculado al negocio."
    },
    link_blocked: {
      label: "Bloqueado",
      title: "Acceso bloqueado",
      body: "Tu acceso personal al espacio negocio esta bloqueado. Contacta a NODO si crees que es un error."
    },
    user_not_active: {
      label: "No disponible",
      title: "Cuenta no activa",
      body: "Esta cuenta no puede entrar al espacio negocio en este momento."
    },
    user_blocked: {
      label: "Bloqueado",
      title: "Cuenta bloqueada",
      body: "Esta cuenta no puede usar NODO en este momento."
    },
    error: {
      label: "Conexion",
      title: "No pudimos validar acceso",
      body: "Intenta de nuevo. Si continua, contacta a NODO."
    }
  };
  const copy = copyByState[accessState] || copyByState.error;
  return (
    <div className="business-card">
      <Text className="business-card__label">{copy.label}</Text>
      <Title level="3" className="business-shell__title">
        {copy.title}
      </Title>
      <Text className="auth-entry__session-meta">{copy.body}</Text>
      <Button mode="outline" size="s" onClick={() => void loadBusinessProfile()}>
        Reintentar
      </Button>
    </div>
  );
}
