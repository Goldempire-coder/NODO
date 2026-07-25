import type { ClientWorkspaceModel } from "../../hooks/useClientWorkspaceModel";
import { ClientOrderChatScreen } from "./ClientOrderChatScreen";
import { ClientSupportScreen } from "./ClientSupportScreen";
import { RemitterScreens } from "./RemitterScreens";

export function ClientScreens({ model }: { model: ClientWorkspaceModel }) {
  return (
    <>
      <RemitterScreens model={model} />

      {model.view === "support" ? <ClientSupportScreen model={model} /> : null}

      {model.view === "order-chat" ? <ClientOrderChatScreen model={model} /> : null}
    </>
  );
}
