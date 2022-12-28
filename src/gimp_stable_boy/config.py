

LOG_REQUESTS = False
TIMEOUT_REQUESTS = False
TIMEOUT_FACTOR = 1
ENABLE_SCRIPTS = True


DEFAULT_API_URL = 'http://localhost:7860'
MASK_LAYER_NAME = 'Inpainting Mask'

IMAGE_TARGETS = ['Layers', 'Images']
MODES = ['Text to Image', 'Image to Image', 'Inpainting']
INPAINTING_FILL_MODE = ['Fill', 'Original', 'Latent noise', 'Latent nothing']
UPSCALERS = ['None', 'Lanczos', 'Nearest', 'LDSR', 'ESRGAN_4x', 'SwinIR_4x', 'ScuNET', 'ScuNET PSNR']
SAMPLERS = [
    'Euler a', 'Euler', 'LMS', 'Heun', 'DPM2', 'DPM2 a', 'DPM++ 2S a', 'DPM++ 2M', 'DPM++ SDE', 'DPM fast',
    'DPM adaptive', 'LMS Karras', 'DPM2 Karras', 'DPM2 a Karras', 'DPM++ 2S a Karras', 'DPM++ 2M Karras',
    'DPM++ SDE Karras', 'DDIM', 'PLMS'
]
SCRIPT_XY_PLOT_AXIS_OPTIONS = [
    "Nothing", "Seed", "Var. seed", "Var. strength", "Steps", "CFG Scale", "Prompt S/R", "Prompt order", "Sampler",
    "Checkpoint name", "Hypernetwork", "Hypernet str.", "Sigma Churn", "Sigma min", "Sigma max", "Sigma noise", "Eta",
    "Clip skip", "Denoising", "Cond. Image Mask Weight"
]
PREFERENCES_SHELF_GROUP = 'stable_boy_preferences'
