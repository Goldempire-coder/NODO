import type { Dispatch, SetStateAction } from "react";
import type { OrderSummary } from "../../../types/orders";

export function ClientOrderRatingBubble({
  orderId,
  rating,
  selectedStars,
  setSelectedStars,
  submit,
  submitting
}: {
  orderId: string;
  rating: NonNullable<OrderSummary["rating"]>;
  selectedStars: number;
  setSelectedStars: Dispatch<SetStateAction<number>>;
  submit: (orderId: string, surface: "order-chat") => void | Promise<void>;
  submitting: boolean;
}) {
  if (rating.already_rated && rating.stars) {
    return (
      <article className="business-order-chat-message business-order-chat-message--system business-order-chat-rating">
        <span className="business-order-chat-message__sender">NODO</span>
        <p>Calificaste {rating.stars} de 5</p>
      </article>
    );
  }
  if (!rating.can_rate) {
    return null;
  }
  return (
    <article className="business-order-chat-message business-order-chat-message--system business-order-chat-rating">
      <span className="business-order-chat-message__sender">NODO</span>
      <p>¿Cómo fue esta operación?</p>
      <div className="business-order-chat-rating__stars" role="radiogroup" aria-label="Calificacion de la operacion">
        {[1, 2, 3, 4, 5].map((stars) => (
          <button key={stars} type="button" aria-label={`${stars} de 5 estrellas`} aria-pressed={selectedStars === stars} className={selectedStars >= stars ? "is-selected" : ""} disabled={submitting} onClick={() => setSelectedStars(stars)}>
            ★
          </button>
        ))}
      </div>
      <button className="business-order-chat-rating__submit" type="button" disabled={submitting || selectedStars < 1} onClick={() => void submit(orderId, "order-chat")}>
        {submitting ? "Calificando..." : "Calificar"}
      </button>
    </article>
  );
}
