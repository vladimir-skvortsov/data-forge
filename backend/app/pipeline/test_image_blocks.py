from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pytest

from app.pipeline.image_blocks import enhance, grayscale, resize, upscale


@pytest.fixture
def img_file(tmp_path: Path) -> str:
    p = tmp_path / 'test.png'
    p.write_bytes(b'fake')
    return str(p)


def _mock_image(width: int = 200, height: int = 100) -> MagicMock:
    img = MagicMock()
    img.width = width
    img.height = height
    img.resize.return_value = img
    img.convert.return_value = img
    return img


def test_resize_by_scale(img_file: str) -> None:
    img = _mock_image()
    with patch('app.pipeline.image_blocks.Image.open', return_value=img):
        result = resize(img_file, {'scale': '2'})
    img.resize.assert_called_once_with((400, 200), ANY)
    img.save.assert_called_once_with(img_file)
    assert result == img_file


def test_resize_by_width_height(img_file: str) -> None:
    img = _mock_image()
    with patch('app.pipeline.image_blocks.Image.open', return_value=img):
        result = resize(img_file, {'width': 100, 'height': 50})
    img.resize.assert_called_once_with((100, 50), ANY)
    assert result == img_file


def test_resize_no_params_noop(img_file: str) -> None:
    img = _mock_image()
    with patch('app.pipeline.image_blocks.Image.open', return_value=img):
        result = resize(img_file, {})
    img.resize.assert_not_called()
    assert result == img_file


def test_upscale_default_factor(img_file: str) -> None:
    img = _mock_image(100, 80)
    with patch('app.pipeline.image_blocks.Image.open', return_value=img):
        result = upscale(img_file, {})
    img.resize.assert_called_once_with((200, 160), ANY)
    assert result == img_file


def test_upscale_custom_factor(img_file: str) -> None:
    img = _mock_image(100, 80)
    with patch('app.pipeline.image_blocks.Image.open', return_value=img):
        upscale(img_file, {'factor': '3'})
    img.resize.assert_called_once_with((300, 240), ANY)


def test_enhance_brightness_only(img_file: str) -> None:
    img = _mock_image()
    mock_enhancer = MagicMock()
    mock_enhancer.enhance.return_value = img
    with (
        patch('app.pipeline.image_blocks.Image.open', return_value=img),
        patch(
            'app.pipeline.image_blocks.ImageEnhance.Brightness',
            return_value=mock_enhancer,
        ),
    ):
        result = enhance(img_file, {'brightness': '1.5'})
    mock_enhancer.enhance.assert_called_once_with(1.5)
    assert result == img_file


def test_enhance_no_changes_skips_enhancers(img_file: str) -> None:
    img = _mock_image()
    with (
        patch('app.pipeline.image_blocks.Image.open', return_value=img),
        patch('app.pipeline.image_blocks.ImageEnhance') as mock_enhance_module,
    ):
        enhance(img_file, {})
    mock_enhance_module.Brightness.assert_not_called()
    mock_enhance_module.Contrast.assert_not_called()
    mock_enhance_module.Sharpness.assert_not_called()


def test_grayscale_converts_and_saves(img_file: str) -> None:
    img = _mock_image()
    with patch('app.pipeline.image_blocks.Image.open', return_value=img):
        result = grayscale(img_file, {})
    img.convert.assert_called_once_with('L')
    assert result == img_file
