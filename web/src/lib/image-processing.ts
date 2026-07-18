const COMPANY_PROFILE_IMAGE_WIDTH = 1600;
const COMPANY_PROFILE_IMAGE_HEIGHT = 1200;
const COMPANY_PROFILE_IMAGE_QUALITY = 0.86;
const COMPANY_PROFILE_IMAGE_TYPE = "image/webp";

export async function processCompanyProfileImage(file: File) {
  if (!file.type.startsWith("image/")) {
    throw new Error("The selected file must be an image.");
  }

  const image = await loadImage(file);
  const sourceAspectRatio = image.width / image.height;
  const targetAspectRatio = COMPANY_PROFILE_IMAGE_WIDTH / COMPANY_PROFILE_IMAGE_HEIGHT;

  let sourceX = 0;
  let sourceY = 0;
  let sourceWidth = image.width;
  let sourceHeight = image.height;

  if (sourceAspectRatio > targetAspectRatio) {
    sourceWidth = image.height * targetAspectRatio;
    sourceX = (image.width - sourceWidth) / 2;
  } else {
    sourceHeight = image.width / targetAspectRatio;
    sourceY = (image.height - sourceHeight) / 2;
  }

  const canvas = document.createElement("canvas");
  canvas.width = COMPANY_PROFILE_IMAGE_WIDTH;
  canvas.height = COMPANY_PROFILE_IMAGE_HEIGHT;

  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Image processing is not supported in this browser.");
  }

  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = "high";
  context.drawImage(
    image,
    sourceX,
    sourceY,
    sourceWidth,
    sourceHeight,
    0,
    0,
    COMPANY_PROFILE_IMAGE_WIDTH,
    COMPANY_PROFILE_IMAGE_HEIGHT
  );

  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (result) => {
        if (result) {
          resolve(result);
          return;
        }
        reject(new Error("Image conversion failed."));
      },
      COMPANY_PROFILE_IMAGE_TYPE,
      COMPANY_PROFILE_IMAGE_QUALITY
    );
  });

  return new File([blob], `${removeFileExtension(file.name)}.webp`, {
    type: COMPANY_PROFILE_IMAGE_TYPE,
    lastModified: Date.now(),
  });
}

function loadImage(file: File) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    const objectUrl = URL.createObjectURL(file);

    image.onload = () => {
      URL.revokeObjectURL(objectUrl);
      resolve(image);
    };

    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error("The image could not be loaded."));
    };

    image.src = objectUrl;
  });
}

function removeFileExtension(filename: string) {
  return filename.replace(/\.[^/.]+$/, "");
}
