import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NODO | Publica ofertas y organiza solicitudes",
  description:
    "NODO ayuda a negocios registrados a publicar ofertas, recibir solicitudes y coordinar directamente con sus clientes."
};

const botUsername = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME?.replace(/^@/, "");
const businessCtaHref = botUsername ? `https://t.me/${botUsername}` : "/business/";

const flowSteps = [
  {
    title: "Compra créditos",
    text: "Usa créditos NODO para publicar y mantener activas tus ofertas."
  },
  {
    title: "Publica tu oferta",
    text: "Define montos, tasa, método disponible y condiciones visibles."
  },
  {
    title: "Recibe solicitudes",
    text: "Los clientes ven ofertas activas y abren órdenes desde la app."
  },
  {
    title: "Coordina directo",
    text: "Negocio y cliente conversan, confirman datos y registran avances."
  },
  {
    title: "Construye reputación",
    text: "NODO organiza historial, estados y señales de confianza operativa."
  }
];

const businessBenefits = [
  "Publica disponibilidad sin manejar listas manuales.",
  "Recibe órdenes con monto, método y estado organizado.",
  "Usa créditos solo para anuncios dentro de NODO.",
  "Revisa historial, conversaciones y soporte desde el panel."
];

const clientBenefits = [
  "Encuentra ofertas activas por monto, método y disponibilidad.",
  "Revisa información del negocio antes de abrir una orden.",
  "Coordina directamente con el negocio dentro del flujo.",
  "Mantiene trazabilidad de la solicitud sin depender de capturas sueltas."
];

const safetyItems = [
  {
    title: "Sin custodia",
    text: "NODO no guarda ni controla fondos acordados entre clientes y negocios."
  },
  {
    title: "Sin claves privadas",
    text: "Nunca pedimos frase secreta, clave privada ni acceso a la wallet del usuario."
  },
  {
    title: "Estados visibles",
    text: "Las órdenes muestran estados para reducir dudas y conversaciones perdidas."
  },
  {
    title: "Revisión y alertas",
    text: "El panel operativo ayuda a revisar actividad, soporte e incidentes."
  }
];

const faqs = [
  {
    question: "¿NODO es una casa de cambio?",
    answer:
      "No. NODO es una plataforma para publicar ofertas, recibir solicitudes y organizar la comunicación entre las partes."
  },
  {
    question: "¿NODO guarda dinero de clientes o negocios?",
    answer:
      "No. Los pagos y acuerdos entre cliente y negocio ocurren directamente entre ellos. NODO no custodia, no libera y no transfiere esos fondos."
  },
  {
    question: "¿Para qué sirven los créditos?",
    answer:
      "Los créditos permiten publicar anuncios dentro de NODO. No son dinero electrónico, no son retirables y no representan saldo del cliente."
  },
  {
    question: "¿NODO garantiza pagos o entregas?",
    answer:
      "No. NODO organiza información, estados y soporte operativo, pero cada parte debe revisar los datos antes de completar un acuerdo."
  }
];

function CheckIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="public-check-icon">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="public-arrow-icon">
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </svg>
  );
}

function PhoneMockups() {
  return (
    <div className="public-phone-stage" aria-hidden="true">
      <div className="public-phone public-phone--business">
        <div className="public-phone-bar">
          <span>NODO</span>
          <small>Negocio</small>
        </div>
        <div className="public-phone-panel">
          <small>Créditos disponibles</small>
          <strong>203</strong>
          <span>Publica y administra tus anuncios.</span>
          <div className="public-phone-button">Comprar</div>
        </div>
        <div className="public-phone-grid">
          <div>
            <small>Anuncios</small>
            <b>2</b>
          </div>
          <div>
            <small>Órdenes</small>
            <b>8</b>
          </div>
        </div>
        <div className="public-phone-offer">
          <small>Oferta abierta</small>
          <b>20.00 - 500.00 USD</b>
          <span>Método visible</span>
        </div>
      </div>
      <div className="public-phone public-phone--client">
        <div className="public-phone-bar">
          <span>NODO</span>
          <small>Cliente</small>
        </div>
        <div className="public-phone-panel">
          <small>¿Qué monto buscas?</small>
          <strong>$50.00</strong>
          <span>Encuentra ofertas activas.</span>
        </div>
        <div className="public-method-row">
          <span>Zelle</span>
          <span>USDT</span>
        </div>
        <div className="public-phone-button">Buscar ofertas</div>
        <div className="public-client-card">
          <b>Envios Zulia</b>
          <span>Oferta disponible</span>
        </div>
      </div>
      <div className="public-activity-chip">
        <span />
        <strong>Actividad organizada</strong>
      </div>
    </div>
  );
}

export default function WebsitePage() {
  return (
    <main className="public-site">
      <header className="public-nav" aria-label="Navegación principal">
        <a className="public-brand" href="#inicio" aria-label="NODO inicio">
          <img src="/icon.svg" alt="" />
          <span>NODO</span>
        </a>
        <nav className="public-links" aria-label="Secciones">
          <a href="#negocios">Negocios</a>
          <a href="#clientes">Clientes</a>
          <a href="#como-funciona">Cómo funciona</a>
          <a href="#seguridad">Seguridad</a>
          <a href="#faq">FAQ</a>
        </nav>
        <a className="public-nav-cta" href={businessCtaHref}>
          Quiero ser negocio
        </a>
      </header>

      <section className="public-hero" id="inicio">
        <PhoneMockups />
        <div className="public-hero-copy">
          <p className="public-eyebrow">NODO para negocios y clientes</p>
          <h1>Publica ofertas y organiza solicitudes en un solo lugar.</h1>
          <p>
            NODO ayuda a negocios registrados a mostrar ofertas, recibir órdenes y coordinar
            directamente con clientes. Los créditos sirven para publicar anuncios dentro de la app.
          </p>
          <div className="public-hero-actions">
            <a className="public-primary-button" href={businessCtaHref}>
              Quiero ser negocio <ArrowIcon />
            </a>
            <a className="public-secondary-button" href="#como-funciona">
              Ver cómo funciona
            </a>
          </div>
          <div className="public-trust-row" aria-label="Resumen de límites de NODO">
            <span>Negocios registrados</span>
            <span>Órdenes organizadas</span>
            <span>Fondos entre las partes</span>
          </div>
        </div>
      </section>

      <section className="public-section public-flow" id="como-funciona">
        <div className="public-section-heading">
          <p className="public-eyebrow">Cómo funciona</p>
          <h2>Un flujo simple, con estados visibles.</h2>
          <p>
            La app mantiene la información ordenada para que cada parte sepa qué hacer sin
            depender de conversaciones dispersas.
          </p>
        </div>
        <div className="public-flow-grid">
          {flowSteps.map((step, index) => (
            <article className="public-flow-step" key={step.title}>
              <span>{index + 1}</span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="public-section public-two-column" id="negocios">
        <div>
          <p className="public-eyebrow">Para negocios</p>
          <h2>Control operativo para publicar y atender órdenes.</h2>
          <p>
            NODO concentra anuncios, créditos, órdenes, conversación y estados para que el
            negocio trabaje con menos fricción.
          </p>
          <ul className="public-check-list">
            {businessBenefits.map((item) => (
              <li key={item}>
                <CheckIcon /> {item}
              </li>
            ))}
          </ul>
        </div>
        <div className="public-product-panel">
          <div className="public-panel-header">
            <span>Anuncios</span>
            <strong>Ofertas publicadas</strong>
          </div>
          <div className="public-metric-grid">
            <div>
              <small>Disponibles</small>
              <b>2</b>
            </div>
            <div>
              <small>Ocupados</small>
              <b>0</b>
            </div>
          </div>
          <div className="public-offer-card">
            <small>Anuncio abierto</small>
            <strong>20.00 - 500.00 USD</strong>
            <span>Estado: activo</span>
          </div>
        </div>
      </section>

      <section className="public-section public-two-column public-two-column--reverse" id="clientes">
        <div className="public-product-panel">
          <div className="public-panel-header">
            <span>Directorio</span>
            <strong>Ofertas disponibles</strong>
          </div>
          <div className="public-client-offer">
            <b>Envios Zulia</b>
            <span>Método: Zelle / USDT</span>
            <small>Orden lista para coordinar</small>
          </div>
          <div className="public-client-offer">
            <b>Pago movil VE</b>
            <span>Oferta activa</span>
            <small>Datos visibles antes de continuar</small>
          </div>
        </div>
        <div>
          <p className="public-eyebrow">Para clientes</p>
          <h2>Encuentra ofertas y conversa dentro de un flujo claro.</h2>
          <p>
            El cliente puede buscar negocios disponibles, abrir una solicitud y mantener el
            seguimiento de la orden en NODO.
          </p>
          <ul className="public-check-list">
            {clientBenefits.map((item) => (
              <li key={item}>
                <CheckIcon /> {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="public-section public-safety" id="seguridad">
        <div className="public-section-heading">
          <p className="public-eyebrow">Seguridad y límites</p>
          <h2>NODO organiza. Las partes operan directamente.</h2>
          <p>
            El producto está diseñado para mantener claros los roles: NODO registra y
            organiza; cliente y negocio revisan y completan directamente sus acuerdos.
          </p>
        </div>
        <div className="public-safety-grid">
          {safetyItems.map((item) => (
            <article className="public-safety-item" key={item.title}>
              <CheckIcon />
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="public-section public-credits" id="creditos">
        <div>
          <p className="public-eyebrow">Créditos NODO</p>
          <h2>Los créditos activan anuncios dentro de la app.</h2>
          <p>
            Los créditos son una herramienta de publicación. No son saldo financiero, no son
            retirables y no representan dinero guardado por NODO.
          </p>
        </div>
        <div className="public-credit-card">
          <span>Starter</span>
          <strong>5 créditos</strong>
          <small>Para comenzar con anuncios y recibir solicitudes.</small>
        </div>
        <div className="public-credit-card">
          <span>Business</span>
          <strong>50 créditos</strong>
          <small>Para operar con mayor continuidad.</small>
        </div>
      </section>

      <section className="public-section public-faq" id="faq">
        <div className="public-section-heading">
          <p className="public-eyebrow">FAQ</p>
          <h2>Preguntas frecuentes</h2>
        </div>
        <div className="public-faq-list">
          {faqs.map((item) => (
            <details key={item.question}>
              <summary>{item.question}</summary>
              <p>{item.answer}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="public-final-cta">
        <div>
          <p className="public-eyebrow">Listo para empezar</p>
          <h2>Publica tus ofertas y atiende solicitudes con más orden.</h2>
        </div>
        <a className="public-primary-button" href={businessCtaHref}>
          Quiero ser negocio <ArrowIcon />
        </a>
      </section>
    </main>
  );
}
