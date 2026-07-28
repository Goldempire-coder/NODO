"use client";

import { useCallback, useRef, useState } from "react";
import { getAdminInvestigationCaseFile } from "../../api/admin";
import type {
  AdminInvestigationCaseFile,
  AdminInvestigationCaseFileSectionName,
  AdminInvestigationSearchItem
} from "../../types/admin";
import type { AdminWebView, RequestFn } from "./adminWebTypes";

type CaseFileHandlers = {
  openUser: (id: string) => Promise<void>;
  openBusiness: (id: string) => Promise<void>;
  openBusinessIntake: (id: string) => Promise<void>;
  openOrder: (id: string) => Promise<void>;
  openSupportTicket: (id: string) => Promise<void>;
};

function caseKey(anchor: { id: string; type: string }) {
  return `${anchor.type}:${anchor.id}`;
}

function mergeSection(
  current: AdminInvestigationCaseFile,
  next: AdminInvestigationCaseFile,
  section: AdminInvestigationCaseFileSectionName,
  append: boolean
): AdminInvestigationCaseFile {
  if (section === "evidence") {
    return {
      ...current,
      evidence: append
        ? {
            ...next.evidence,
            documents: [...current.evidence.documents, ...next.evidence.documents],
            attachments: [...current.evidence.attachments, ...next.evidence.attachments]
          }
        : next.evidence,
      warnings: next.warnings
    };
  }
  const previousPage = current[section];
  const nextPage = next[section];
  return {
    ...current,
    [section]: {
      ...nextPage,
      items: append ? [...previousPage.items, ...nextPage.items] : nextPage.items
    },
    warnings: next.warnings
  };
}

export function useAdminInvestigationCaseFileModel({
  handlers,
  request,
  setNotice,
  setView
}: {
  handlers: CaseFileHandlers;
  request: RequestFn;
  setNotice: (notice: string) => void;
  setView: (view: AdminWebView) => void;
}) {
  const [caseFile, setCaseFile] = useState<AdminInvestigationCaseFile | null>(null);
  const [loading, setLoading] = useState(false);
  const [sectionLoading, setSectionLoading] = useState<AdminInvestigationCaseFileSectionName | null>(null);
  const activeCaseKey = useRef<string | null>(null);
  const openRequestSeq = useRef(0);
  const sectionRequestSeq = useRef(0);

  const openCaseFile = useCallback(async (item: AdminInvestigationSearchItem) => {
    const requestSeq = openRequestSeq.current + 1;
    const requestedCaseKey = caseKey(item);
    openRequestSeq.current = requestSeq;
    activeCaseKey.current = requestedCaseKey;
    setLoading(true);
    setView("case-file");
    try {
      const data = await getAdminInvestigationCaseFile<AdminInvestigationCaseFile>(request, {
        anchorType: item.type,
        anchorId: item.id
      });
      if (openRequestSeq.current !== requestSeq || activeCaseKey.current !== requestedCaseKey) {
        return;
      }
      setCaseFile(data);
      setNotice("Ficha de investigacion cargada.");
    } catch (error) {
      if (openRequestSeq.current !== requestSeq || activeCaseKey.current !== requestedCaseKey) {
        return;
      }
      setCaseFile(null);
      setNotice(error instanceof Error ? error.message : "No pudimos cargar la ficha de investigacion.");
    } finally {
      if (openRequestSeq.current === requestSeq && activeCaseKey.current === requestedCaseKey) {
        setLoading(false);
      }
    }
  }, [request, setNotice, setView]);

  const loadCaseFileSection = useCallback(async (
    section: AdminInvestigationCaseFileSectionName,
    { append = false }: { append?: boolean } = {}
  ) => {
    if (!caseFile) {
      return;
    }
    const requestSeq = sectionRequestSeq.current + 1;
    const requestedCaseKey = caseKey(caseFile.anchor);
    const page = caseFile[section];
    const cursor = append ? page.next_cursor || undefined : undefined;
    sectionRequestSeq.current = requestSeq;
    setSectionLoading(section);
    try {
      const data = await getAdminInvestigationCaseFile<AdminInvestigationCaseFile>(request, {
        anchorType: caseFile.anchor.type,
        anchorId: caseFile.anchor.id,
        section,
        cursor
      });
      if (sectionRequestSeq.current !== requestSeq || activeCaseKey.current !== requestedCaseKey) {
        return;
      }
      setCaseFile((current) => (current && caseKey(current.anchor) === requestedCaseKey ? mergeSection(current, data, section, append) : current));
    } catch (error) {
      if (sectionRequestSeq.current === requestSeq && activeCaseKey.current === requestedCaseKey) {
        setNotice(error instanceof Error ? error.message : "No pudimos recargar esta seccion.");
      }
    } finally {
      if (sectionRequestSeq.current === requestSeq && activeCaseKey.current === requestedCaseKey) {
        setSectionLoading(null);
      }
    }
  }, [caseFile, request, setNotice]);

  const openCaseFileRoute = useCallback(async (route: string) => {
    const match = /^admin:\/\/(user|business|business-intake|order|support-ticket)\/([0-9a-f-]+)$/i.exec(route);
    if (!match) {
      setNotice("La ruta interna no esta disponible.");
      return;
    }
    const [, type, id] = match;
    if (type === "user") {
      await handlers.openUser(id);
    } else if (type === "business") {
      await handlers.openBusiness(id);
    } else if (type === "business-intake") {
      await handlers.openBusinessIntake(id);
    } else if (type === "order") {
      await handlers.openOrder(id);
    } else {
      await handlers.openSupportTicket(id);
    }
  }, [handlers, setNotice]);

  return {
    caseFile,
    caseFileLoading: loading,
    caseFileSectionLoading: sectionLoading,
    openCaseFile,
    loadCaseFileSection,
    openCaseFileRoute
  };
}
