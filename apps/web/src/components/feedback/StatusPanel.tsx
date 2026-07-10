import { Button, Spinner, Text } from "@telegram-apps/telegram-ui";
import type { SessionState } from "../../types/auth";

export function StatusPanel({ state, message, onRetry }: { state: SessionState; message: string; onRetry: () => void }) {
  return (
    <>
      {state === "loading" ? (
        <div className="auth-entry__status">
          <Spinner size="m" />
          <Text>Preparando NODO</Text>
        </div>
      ) : null}

      {state === "error" ? (
        <Button mode="filled" size="l" stretched onClick={onRetry}>
          Reintentar
        </Button>
      ) : null}

      {state === "expired" ? (
        <Button mode="filled" size="l" stretched onClick={onRetry}>
          Volver a entrar
        </Button>
      ) : null}

      {state !== "authenticated" ? <Text className="auth-entry__message">{message}</Text> : null}
    </>
  );
}
