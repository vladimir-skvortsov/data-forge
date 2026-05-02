from PIL import Image, ImageEnhance


def resize(file_path: str, params: dict) -> str:
    img = Image.open(file_path)
    scale = params.get('scale')
    width = params.get('width')
    height = params.get('height')

    if scale:
        f = float(scale)
        new_size = (int(img.width * f), int(img.height * f))
    elif width and height:
        new_size = (int(width), int(height))
    elif width:
        ratio = int(width) / img.width
        new_size = (int(width), int(img.height * ratio))
    elif height:
        ratio = int(height) / img.height
        new_size = (int(img.width * ratio), int(height))
    else:
        return file_path

    img.resize(new_size, Image.Resampling.LANCZOS).save(file_path)
    return file_path


def upscale(file_path: str, params: dict) -> str:
    factor = float(params.get('factor', 2))
    img = Image.open(file_path)
    new_size = (int(img.width * factor), int(img.height * factor))
    img.resize(new_size, Image.Resampling.LANCZOS).save(file_path)
    return file_path


def enhance(file_path: str, params: dict) -> str:
    result: Image.Image = Image.open(file_path)

    brightness = float(params.get('brightness', 1.0))
    contrast = float(params.get('contrast', 1.0))
    sharpness = float(params.get('sharpness', 1.0))

    if brightness != 1.0:
        result = ImageEnhance.Brightness(result).enhance(brightness)
    if contrast != 1.0:
        result = ImageEnhance.Contrast(result).enhance(contrast)
    if sharpness != 1.0:
        result = ImageEnhance.Sharpness(result).enhance(sharpness)

    result.save(file_path)
    return file_path


def grayscale(file_path: str, params: dict) -> str:  # noqa: ARG001
    Image.open(file_path).convert('L').save(file_path)
    return file_path
