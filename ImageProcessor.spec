# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ImageProcessor."""

from pathlib import Path

block_cipher = None

project_root = Path(SPECPATH).resolve()

a = Analysis(
    [str(project_root / 'main.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        'image_processor.app',
        'image_processor.gui.main_window',
        'image_processor.gui.canvas',
        'image_processor.gui.toolbar',
        'image_processor.gui.panels.matting_panel',
        'image_processor.gui.panels.resize_panel',
        'image_processor.gui.panels.crop_panel',
        'image_processor.gui.panels.inpaint_panel',
        'image_processor.gui.panels.brush_panel',
        'image_processor.gui.panels.sprite_panel',
        'image_processor.gui.panels.adjust_panel',
        'image_processor.gui.widgets.batch_dialog',
        'image_processor.gui.widgets.compare_dialog',
        'image_processor.gui.widgets.slider_compare',
        'image_processor.gui.widgets.matting_worker',
        'image_processor.gui.widgets.toast',
        'image_processor.core.image_engine',
        'image_processor.core.batch_processor',
        'image_processor.core.history_manager',
        'image_processor.core.project_manager',
        'image_processor.models.image_item',
        'image_processor.models.project',
        'image_processor.utils.helpers',
        'image_processor.utils.recent_files',
        'image_processor.utils.themes',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageChops',
        'PIL.ImageEnhance',
        'PIL.ImageOps',
        'cv2',
        'numpy',
        'rembg',
        'onnxruntime',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ImageProcessor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ImageProcessor',
)

app = BUNDLE(
    coll,
    name='ImageProcessor.app',
    icon=None,
    bundle_identifier='com.imageprocessor.app',
)
