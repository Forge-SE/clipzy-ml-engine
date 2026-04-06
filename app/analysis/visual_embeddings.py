"""Visual embeddings using CLIP."""

from typing import Optional

import numpy as np
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModel
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class VisualEmbedder:
    """Generates visual embeddings using CLIP."""

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", device: str = "cpu"):
        """
        Initialize visual embedder.

        Args:
            model_name: CLIP model identifier
            device: Device to run on (cpu or cuda)
        """
        self.device = device
        self.model_name = model_name

        logger.info(f"Loading CLIP model: {model_name}")

        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(device)
        self.model.eval()

    def embed_frames(self, frames: list[np.ndarray], sample_rate: int = 30) -> tuple[list[np.ndarray], list[float]]:
        """
        Generate embeddings for frames at specified sample rate.

        Args:
            frames: List of frames (RGB, not BGR)
            sample_rate: Generate embedding every Nth frame

        Returns:
            Tuple of (embeddings list, timestamps list)
        """
        embeddings = []
        timestamps = []

        logger.info(f"Generating embeddings for {len(frames)} frames at sample rate {sample_rate}")

        with torch.no_grad():
            for i, frame_idx in enumerate(range(0, len(frames), sample_rate)):
                frame = frames[frame_idx]

                # Convert BGR to RGB if needed
                if len(frame.shape) == 3:
                    rgb_frame = frame[..., ::-1]  # BGR to RGB
                else:
                    rgb_frame = frame

                # Convert numpy array to PIL Image
                pil_image = Image.fromarray(rgb_frame)

                try:
                    # Process image
                    inputs = self.processor(images=pil_image, return_tensors="pt").to(self.device)

                    # Get image features (not text)
                    outputs = self.model(**inputs)
                    image_features = outputs.image_embeds

                    # Normalize
                    embedding = image_features[0].cpu().numpy()
                    embedding = embedding / (np.linalg.norm(embedding) + 1e-8)

                    embeddings.append(embedding)
                    timestamps.append(frame_idx / 30.0)  # Approximate timestamp

                except Exception as e:
                    logger.warning(f"Failed to embed frame {frame_idx}: {str(e)}")
                    continue

        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings, timestamps

    def compute_similarity_sequence(self, embeddings: list[np.ndarray]) -> list[float]:
        """
        Compute cosine similarity between consecutive embeddings.

        Args:
            embeddings: List of embedding vectors

        Returns:
            List of similarity scores
        """
        similarities = []

        for i in range(len(embeddings) - 1):
            emb1 = embeddings[i]
            emb2 = embeddings[i + 1]

            # Cosine similarity
            similarity = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-8))
            similarities.append(similarity)

        return similarities
