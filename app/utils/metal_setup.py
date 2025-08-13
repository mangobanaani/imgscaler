"""M1 Mac Metal GPU setup and benchmarking utilities."""
from __future__ import annotations

import os
from loguru import logger


def configure_metal_gpu():
    """Configure TensorFlow for optimal M1 Mac Metal performance."""
    # Set environment variables before TensorFlow import
    os.environ['TF_METAL_DEVICE_PLACEMENT'] = 'true'
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Reduce TF logging
    
    try:
        import tensorflow as tf
        
        # Enable Metal GPU
        gpus = tf.config.experimental.list_physical_devices('GPU')
        if gpus:
            try:
                # Enable memory growth to avoid allocating all GPU memory
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
                
                # Set mixed precision for better performance
                policy = tf.keras.mixed_precision.Policy('mixed_float16')
                tf.keras.mixed_precision.set_global_policy(policy)
                
                logger.info(f"Metal GPU configured successfully: {len(gpus)} device(s)")
                logger.info(f"Mixed precision enabled: {policy.name}")
                
                # Test GPU availability
                with tf.device('/GPU:0'):
                    test_tensor = tf.constant([[1.0, 2.0], [3.0, 4.0]])
                    result = tf.matmul(test_tensor, test_tensor)
                logger.info("Metal GPU test passed")
                
                return True
            except Exception as e:
                logger.warning(f"Metal GPU setup failed: {e}")
                return False
        else:
            logger.info("No GPU devices detected, using CPU")
            return False
            
    except ImportError:
        logger.error("TensorFlow not available")
        return False


def get_device_info():
    """Get device and performance information."""
    try:
        import tensorflow as tf
        
        info = {
            "tensorflow_version": tf.__version__,
            "gpu_available": len(tf.config.experimental.list_physical_devices('GPU')) > 0,
            "mixed_precision": tf.keras.mixed_precision.global_policy().name,
            "devices": []
        }
        
        # List all devices
        for device in tf.config.experimental.list_physical_devices():
            info["devices"].append({
                "type": device.device_type,
                "name": device.name
            })
        
        return info
    except Exception as e:
        logger.error(f"Failed to get device info: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Test Metal setup
    print("Configuring Metal GPU...")
    success = configure_metal_gpu()
    print(f"Configuration {'successful' if success else 'failed'}")
    
    print("\nDevice Information:")
    info = get_device_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
