"""TensorFlow Hub ESRGAN service for high-quality image upscaling."""
from dataclasses import dataclass
from typing import Optional
import io

import numpy as np
from loguru import logger
from PIL import Image


from app.metrics import time_block


try:
    # Enable TensorFlow and TensorFlow Hub for Metal
    from app.utils.metal_setup import configure_metal_gpu
    import tensorflow as tf
    import tensorflow_hub as hub
    TF_HUB_AVAILABLE = True
    configure_metal_gpu()
    logger.info("TensorFlow Hub enabled with Metal GPU support")
except ImportError as e:
    tf = None
    hub = None
    TF_HUB_AVAILABLE = False
    logger.warning(f"TensorFlow Hub not available: {e}")


@dataclass
class TFHubUpscaleRequest:
    image: Image.Image
    factor: int = 4  # ESRGAN model is typically 4x
    denoise: bool = False


class TFHubUpscaleService:
    """High-quality image upscaling using TensorFlow Hub ESRGAN model."""

    def __init__(self) -> None:
        self._model: Optional[object] = None
        self._model_loaded = False
        
        if TF_HUB_AVAILABLE:
            self._configure_gpu()
        
        logger.info("TFHubUpscaleService initialized")

    def _configure_gpu(self):
        """Configure GPU memory growth for M1 Mac Metal."""
        try:
            gpus = tf.config.experimental.list_physical_devices('GPU')
            if gpus:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
                logger.info(f"Metal GPU configured: {len(gpus)} device(s)")
            else:
                logger.info("No GPU devices found, using CPU")
        except Exception as e:
            logger.warning(f"GPU configuration failed: {e}")

    def _load_model(self):
        """Load the TensorFlow Hub ESRGAN model."""
        if self._model_loaded:
            return self._model
            
        if not TF_HUB_AVAILABLE:
            raise ImportError("TensorFlow Hub not available. Install with: poetry install --with ml")
        
        logger.info("Loading ESRGAN model from TensorFlow Hub...")
        with time_block("model_loading"):
            self._model = hub.load("https://tfhub.dev/captain-pool/esrgan-tf2/1")
        
        self._model_loaded = True
        logger.info("ESRGAN model loaded successfully")
        return self._model

    def _preprocess_image(self, img: Image.Image):
        """Preprocess PIL image for ESRGAN model."""
        # Convert PIL to numpy array
        img_array = np.array(img)
        
        # Ensure RGB format
        if img_array.shape[-1] == 4:  # RGBA
            img_array = img_array[:, :, :3]
        elif len(img_array.shape) == 2:  # Grayscale
            img_array = np.stack([img_array] * 3, axis=-1)
        
        # Convert to float32 and normalize to [0, 1]
        img_array = img_array.astype(np.float32) / 255.0
        
        # Add batch dimension
        img_tensor = tf.convert_to_tensor(img_array)
        img_tensor = tf.expand_dims(img_tensor, 0)  # [1, H, W, 3]
        
        logger.debug(f"Preprocessed image shape: {img_tensor.shape}")
        return img_tensor

    def _postprocess_image(self, tensor) -> Image.Image:
        """Convert model output tensor back to PIL Image."""
        # Remove batch dimension
        img_array = tf.squeeze(tensor, 0).numpy()
        
        # Clip values to [0, 1] and convert to uint8
        img_array = np.clip(img_array, 0, 1) * 255.0
        img_array = img_array.astype(np.uint8)
        
        # Convert to PIL Image
        img = Image.fromarray(img_array)
        logger.debug(f"Postprocessed image size: {img.size}")
        return img

    def upscale(self, request: TFHubUpscaleRequest) -> Image.Image:
        """Upscale image using TensorFlow Hub ESRGAN model.
        
        Args:
            request: Upscale request with image and options
            
        Returns:
            Upscaled PIL Image (4x resolution)
        """
        if not TF_HUB_AVAILABLE:
            raise ImportError("TensorFlow Hub not available")
        
        img = request.image
        w, h = img.size
        
        # Validate image size
        # Use a default max image size if settings is unavailable
        max_image_pixels = 4096 * 4096  # 16MP default
        if w * h > max_image_pixels:
            logger.warning(f"Image too large ({w}x{h}), clamping")
            from app.utils.image_io import clamp_large_image
            img = clamp_large_image(img, max_image_pixels)
            w, h = img.size
        
        logger.info(f"Upscaling {w}x{h} image using TensorFlow Hub ESRGAN")
        
        with time_block(f"tfhub_esrgan_upscale"):
            # Load model if needed
            model = self._load_model()
            
            # Preprocess
            input_tensor = self._preprocess_image(img)
            
            # Run inference
            logger.debug("Running ESRGAN inference...")
            with time_block("esrgan_inference"):
                output_tensor = model(input_tensor)
            
            # Postprocess
            upscaled_img = self._postprocess_image(output_tensor)
            
            # Optional denoising (PIL-based)
            if request.denoise:
                from PIL import ImageFilter
                upscaled_img = upscaled_img.filter(ImageFilter.GaussianBlur(radius=0.5))
                upscaled_img = upscaled_img.filter(ImageFilter.SHARPEN)
        
        logger.info(f"TensorFlow Hub ESRGAN upscaling completed: {upscaled_img.size}")
        return upscaled_img

    def get_status(self) -> dict:
        """Get service status information."""
        return {
            "service": "TFHubUpscaleService",
            "method": "TensorFlow Hub ESRGAN",
            "model_url": "https://tfhub.dev/captain-pool/esrgan-tf2/1",
            "available_factors": [4],  # ESRGAN is typically 4x
            "features": ["ai_enhancement", "edge_preservation", "texture_restoration", "denoising"],
            "tf_available": TF_HUB_AVAILABLE,
            "model_loaded": self._model_loaded,
            "status": "ready" if TF_HUB_AVAILABLE else "tf_hub_required"
        }
