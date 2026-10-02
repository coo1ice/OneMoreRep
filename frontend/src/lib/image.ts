export const MAX_IMAGE_BYTES = 2 * 1024 * 1024;
const MAX_IMAGE_EDGE = 1600;

export async function prepareImage(file: File): Promise<File> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    throw new Error('Choose a JPEG, PNG, or WebP image.');
  }

  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    throw new Error('This image could not be opened. Try saving it as JPEG, PNG, or WebP.');
  }

  try {
    if (file.size <= MAX_IMAGE_BYTES && Math.max(bitmap.width, bitmap.height) <= MAX_IMAGE_EDGE) return file;

    let scale = Math.min(1, MAX_IMAGE_EDGE / Math.max(bitmap.width, bitmap.height));
    const qualities = [0.86, 0.76, 0.66, 0.56, 0.46];
    for (let resize = 0; resize < 7; resize += 1) {
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(bitmap.width * scale));
      canvas.height = Math.max(1, Math.round(bitmap.height * scale));
      const context = canvas.getContext('2d');
      if (!context) throw new Error('Image compression is unavailable in this browser.');
      context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);

      for (const quality of qualities) {
        const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve, 'image/jpeg', quality));
        if (blob && blob.size <= MAX_IMAGE_BYTES) {
          const name = file.name.replace(/\.[^.]+$/, '') || 'photo';
          return new File([blob], `${name}.jpg`, { type: 'image/jpeg', lastModified: Date.now() });
        }
      }
      scale *= 0.8;
    }
    throw new Error('This image is still larger than 2 MB after compression. Choose a smaller image.');
  } finally {
    bitmap.close();
  }
}
