export const MAX_PAYMENT_EVIDENCE_UPLOAD_BYTES = 4_750_000;
export const MAX_PAYMENT_EVIDENCE_IMAGE_DIMENSION = 1800;

const ACCEPTED_PAYMENT_EVIDENCE_MIME_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/pdf"
]);

function inferMimeType(file: File): string {
  const explicitType = file.type.toLowerCase();
  if (explicitType) {
    return explicitType;
  }
  const name = file.name.toLowerCase();
  if (name.endsWith(".jpg") || name.endsWith(".jpeg")) {
    return "image/jpeg";
  }
  if (name.endsWith(".png")) {
    return "image/png";
  }
  if (name.endsWith(".webp")) {
    return "image/webp";
  }
  if (name.endsWith(".pdf")) {
    return "application/pdf";
  }
  return "";
}

function extensionForMimeType(mimeType: string): string {
  if (mimeType === "image/jpeg") {
    return ".jpg";
  }
  if (mimeType === "image/webp") {
    return ".webp";
  }
  if (mimeType === "application/pdf") {
    return ".pdf";
  }
  return ".png";
}

function normalizedFileName(name: string, mimeType: string): string {
  const base = name.replace(/\.[^.]+$/, "").trim() || "comprobante";
  return `${base}${extensionForMimeType(mimeType)}`;
}

async function loadImage(file: File): Promise<HTMLImageElement> {
  const url = URL.createObjectURL(file);
  try {
    const image = new Image();
    image.decoding = "async";
    const loaded = new Promise<HTMLImageElement>((resolve, reject) => {
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error("No pudimos preparar la foto. Usa una captura PNG/JPG."));
    });
    image.src = url;
    return await loaded;
  } finally {
    URL.revokeObjectURL(url);
  }
}

function canvasToBlob(canvas: HTMLCanvasElement, mimeType: string, quality: number): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error("No pudimos preparar la foto. Usa una captura PNG/JPG."));
        return;
      }
      resolve(blob);
    }, mimeType, quality);
  });
}

async function compressImage(file: File): Promise<Blob> {
  const image = await loadImage(file);
  const sourceWidth = image.naturalWidth || image.width;
  const sourceHeight = image.naturalHeight || image.height;
  const scale = Math.min(1, MAX_PAYMENT_EVIDENCE_IMAGE_DIMENSION / Math.max(sourceWidth, sourceHeight));
  const width = Math.max(1, Math.round(sourceWidth * scale));
  const height = Math.max(1, Math.round(sourceHeight * scale));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("No pudimos preparar la foto. Usa una captura PNG/JPG.");
  }
  context.drawImage(image, 0, 0, width, height);
  for (const quality of [0.82, 0.72, 0.62, 0.52]) {
    const blob = await canvasToBlob(canvas, "image/jpeg", quality);
    if (blob.size <= MAX_PAYMENT_EVIDENCE_UPLOAD_BYTES) {
      return blob;
    }
  }
  return canvasToBlob(canvas, "image/jpeg", 0.46);
}

export async function preparePaymentEvidenceFile(file: File): Promise<File> {
  const mimeType = inferMimeType(file);
  if (mimeType === "application/pdf") {
    if (file.size > MAX_PAYMENT_EVIDENCE_UPLOAD_BYTES) {
      throw new Error("El PDF pesa demasiado. Adjunta una imagen o un PDF menor de 5 MB.");
    }
    if (file.type) {
      return file;
    }
    return new File([file], normalizedFileName(file.name, mimeType), {
      type: mimeType,
      lastModified: file.lastModified
    });
  }
  if (!mimeType.startsWith("image/")) {
    throw new Error("Adjunta una imagen PNG/JPG/WebP o PDF.");
  }
  if (ACCEPTED_PAYMENT_EVIDENCE_MIME_TYPES.has(mimeType) && file.size <= MAX_PAYMENT_EVIDENCE_UPLOAD_BYTES && file.type) {
    return file;
  }
  const blob = await compressImage(file);
  if (blob.size > MAX_PAYMENT_EVIDENCE_UPLOAD_BYTES) {
    throw new Error("La imagen pesa demasiado. Toma una captura mas liviana e intenta otra vez.");
  }
  return new File([blob], normalizedFileName(file.name, blob.type), {
    type: blob.type,
    lastModified: Date.now()
  });
}
