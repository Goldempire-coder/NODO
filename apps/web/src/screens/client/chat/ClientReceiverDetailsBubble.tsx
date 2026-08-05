import type { Dispatch, FormEvent, SetStateAction } from "react";
import type { ChatCapabilities } from "../../../types/chat";
import type { ReceiverDetailsInput, ReceiverDetailsMasked } from "../../../types/orders";

const PAGO_MOVIL_BANK_OPTIONS = [
  ["0102", "Banco de Venezuela"], ["0105", "Mercantil Banco"],
  ["0108", "BBVA Provincial"], ["0114", "Bancaribe"],
  ["0115", "Banco Exterior"], ["0128", "Banco Caroni"],
  ["0134", "Banesco"], ["0137", "Banco Sofitasa"],
  ["0138", "Banco Plaza"], ["0151", "Banco Fondo Comun"],
  ["0156", "100% Banco"], ["0157", "DelSur Banco Universal"],
  ["0163", "Banco del Tesoro"], ["0166", "Banco Agricola de Venezuela"],
  ["0168", "Bancrecer"], ["0169", "Mi Banco"],
  ["0171", "Banco Activo"], ["0172", "Bancamiga"],
  ["0174", "Banplus"], ["0175", "Banco Bicentenario"],
  ["0177", "Banfanb"], ["0191", "Banco Nacional de Credito"]
] as const;

export function ClientReceiverDetailsBubble({
  canShare,
  capabilities,
  form,
  masked,
  setForm,
  share,
  sharing
}: {
  canShare: boolean;
  capabilities: ChatCapabilities;
  form: ReceiverDetailsInput;
  masked: ReceiverDetailsMasked | null;
  setForm: Dispatch<SetStateAction<ReceiverDetailsInput>>;
  share: () => void | Promise<void>;
  sharing: boolean;
}) {
  const submit = (event: FormEvent) => {
    event.preventDefault();
    void share();
  };

  return (
    <>
      {canShare ? (
        <article className="business-order-chat-message business-order-chat-message--mine business-order-chat-receiver-details">
          <span className="business-order-chat-message__sender">Pago Movil</span>
          <details>
            <summary>Compartir Pago Movil</summary>
            <form className="business-order-chat-receiver-form" onSubmit={submit}>
              <label>
                Banco
                <select value={form.bank} onChange={(event) => setForm({ ...form, bank: event.target.value })}>
                  {PAGO_MOVIL_BANK_OPTIONS.map(([code, name]) => (
                    <option key={code} value={code}>{name}</option>
                  ))}
                </select>
              </label>
              <label>
                Telefono
                <input type="tel" inputMode="tel" autoComplete="tel" placeholder="0414 1234567 o +58 414 1234567" required value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
              </label>
              <label>
                Cedula
                <input type="text" autoCapitalize="characters" placeholder="V12345678" required value={form.document} onChange={(event) => setForm({ ...form, document: event.target.value })} />
              </label>
              <label>
                Titular
                <input type="text" autoComplete="name" required value={form.holder} onChange={(event) => setForm({ ...form, holder: event.target.value })} />
              </label>
              <button type="submit" disabled={sharing}>{sharing ? "Compartiendo..." : "Compartir"}</button>
            </form>
          </details>
        </article>
      ) : null}
      {capabilities.receiver_details_shared ? (
        <article className="business-order-chat-message business-order-chat-message--mine">
          <span className="business-order-chat-message__sender">Pago Movil compartido</span>
          <p>{masked ? `${masked.bank} / ${masked.phone} / ${masked.document} / ${masked.holder}` : "Datos guardados para esta orden."}</p>
        </article>
      ) : null}
    </>
  );
}
