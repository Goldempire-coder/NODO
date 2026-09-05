import { Button, Text, Title } from "@telegram-apps/telegram-ui";
import { CURRENT_CLIENT_TERMS_VERSION, hasAcceptedCurrentClientTerms } from "../../constants/legal";
import { sanitizePhoneInput } from "../../lib/numericInput";
import type { RemitterScreensModel } from "./RemitterScreens.types";

export function ClientOnboardingScreens({ model }: { model: RemitterScreensModel }) {
  const {
    acceptTerms,
    busy,
    clientProfileForm,
    loggingOut,
    logout,
    setClientProfileForm,
    setView,
    submitClientProfile,
    user,
    view
  } = model;
  const termsAccepted = hasAcceptedCurrentClientTerms(user);

  return (
    <>
      {view === "welcome" ? (
        <div className="welcome-screen">
          <div className="welcome-hero">
            <Text className="exchange-card__eyebrow">NODO</Text>
            <Title level="1" className="welcome-hero__title">Bienvenido a NODO</Title>
            <Text className="welcome-hero__copy">
              Consulta negocios registrados, revisa sus condiciones publicadas y abre una solicitud en pocos pasos.
            </Text>
          </div>
          <div className="welcome-actions">
            <Button mode="filled" stretched onClick={() => setView("terms")}>
              Comenzar
            </Button>
          </div>
        </div>
      ) : null}

      {view === "terms" ? (
        <div className="business-card terms-screen">
          <Text className="business-card__label">Antes de comenzar</Text>
          <Title level="2" className="business-shell__title">Antes de usar NODO</Title>
          <Text>NODO es un directorio de negocios registrados que publican sus propias condiciones.</Text>
          <Text>Revisamos datos del negocio antes de publicarlo y el acceso opera por invitacion.</Text>
          <Text>Tu eliges el negocio y coordinas directamente con los datos indicados en tu orden.</Text>
          <Text>NODO registra la orden y su evidencia para soporte y auditoria, pero no recibe ni retiene fondos.</Text>
          <Text>Al continuar aceptas los terminos de uso vigentes y el registro de actividad de la orden.</Text>
          <Text className="auth-entry__session-meta">Version: {CURRENT_CLIENT_TERMS_VERSION}</Text>
          <Button mode="filled" stretched disabled={busy} onClick={() => void acceptTerms()}>
            Acepto y continuar
          </Button>
          <Button mode="outline" stretched disabled={busy} onClick={() => setView("welcome")}>
            Ahora no
          </Button>
        </div>
      ) : null}

      {view === "client-profile-setup" ? (
        <div className="business-card terms-screen">
          <Text className="business-card__label">Tu contacto</Text>
          <Title level="2" className="business-shell__title">Antes de empezar</Title>
          <Text>Indicanos tu nombre y telefono de contacto para identificar tus ordenes y ayudarte si necesitas soporte.</Text>
          <label className="business-field">
            <span>Nombre</span>
            <input
              value={clientProfileForm.first_name}
              onChange={(event) => setClientProfileForm((current) => ({ ...current, first_name: event.target.value.replace(/[<>]/g, "").slice(0, 80) }))}
              autoComplete="given-name"
            />
          </label>
          <label className="business-field">
            <span>Telefono de contacto</span>
            <input
              value={clientProfileForm.phone}
              onChange={(event) => setClientProfileForm((current) => ({ ...current, phone: sanitizePhoneInput(event.target.value) }))}
              inputMode="tel"
              autoComplete="tel"
              placeholder="Escribe tu numero completo"
            />
          </label>
          <Text className="auth-entry__session-meta">Puede ser de Venezuela, Estados Unidos u otro pais.</Text>
          <Button
            mode="filled"
            stretched
            disabled={busy || clientProfileForm.first_name.trim().length < 2 || clientProfileForm.phone.replace(/\D/g, "").length < 7}
            onClick={() => void submitClientProfile()}
          >
            Guardar y continuar
          </Button>
          <Text className="auth-entry__session-meta">Estos datos quedan disponibles para soporte y administracion de NODO.</Text>
        </div>
      ) : null}

      {view === "profile" ? (
        <div className="business-card profile-screen">
          <Text className="business-card__label">Tu perfil</Text>
          <Title level="2" className="business-shell__title">{user.first_name || user.username || "Cliente NODO"}</Title>
          <Text>Modo cliente. Desde aqui puedes consultar negocios registrados y revisar tus ordenes.</Text>
          <div className="business-card business-card--nested">
            <Text className="business-card__label">Terminos y reglas</Text>
            <Text>{termsAccepted ? "Tienes aceptados los terminos vigentes." : "Debes aceptar los terminos vigentes para operar en NODO."}</Text>
            <Text className="auth-entry__session-meta">Version: {CURRENT_CLIENT_TERMS_VERSION}</Text>
            {termsAccepted ? (
              <Button mode="outline" stretched onClick={() => setView("terms")}>
                Ver terminos
              </Button>
            ) : (
              <Button mode="filled" stretched disabled={busy} onClick={() => setView("terms")}>
                Aceptar terminos
              </Button>
            )}
          </div>
          <Button mode="filled" stretched onClick={() => setView("marketplace-search")}>
            Ver directorio
          </Button>
          <Button mode="outline" stretched onClick={() => setView("support")}>
            Soporte NODO
          </Button>
          <Button mode="outline" stretched disabled={loggingOut} onClick={() => void logout()}>
            {loggingOut ? "Cerrando..." : "Cerrar sesion en este dispositivo"}
          </Button>
        </div>
      ) : null}
    </>
  );
}
