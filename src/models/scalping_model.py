"""
Scalping model module for the crypto trading bot.
Provides a TensorFlow model for predicting price movements.
"""

import datetime
import json
import os
from typing import Dict, Any, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

from src.utils.logging import logger


class ScalpingModel:
    """TensorFlow model for predicting price movements."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        sequence_length: int = 60,
        prediction_horizon: int = 5,
        features: List[str] = None,
    ):
        """
        Initialize the model.

        Args:
            model_path: Path to a saved model.
            sequence_length: Length of input sequences.
            prediction_horizon: Number of steps to predict ahead.
            features: List of features to use.
        """
        self.sequence_length = sequence_length
        self.prediction_horizon = prediction_horizon
        
        # Enhanced feature set with additional technical indicators
        self.features = features or [
            # Price data
            "close", "open", "high", "low", "volume",
            
            # Basic indicators
            "rsi", "ema_short", "ema_long",
            
            # Additional indicators
            "macd", "macd_signal", "macd_hist",  # MACD
            "bb_upper", "bb_middle", "bb_lower",  # Bollinger Bands
            "atr",  # Average True Range
            "obv",  # On-Balance Volume
            "adx",  # Average Directional Index
            "cci",  # Commodity Channel Index
            
            # Price patterns
            "price_change", "volume_change",  # Rate of change
            "price_volatility",  # Price volatility
        ]
        
        self.model = None
        self.scaler = MinMaxScaler()
        
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
        else:
            self._build_model()

    def _build_model(self) -> None:
        """Build an ensemble of models for more robust predictions."""
        # Define input shape
        input_shape = (self.sequence_length, len(self.features))
        
        # Build LSTM model
        lstm_model = tf.keras.Sequential([
            tf.keras.layers.LSTM(64, return_sequences=True, input_shape=input_shape),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.LSTM(32),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(16, activation="relu"),
            tf.keras.layers.Dense(3, activation="softmax"),  # 3 classes: buy, sell, hold
        ])
        
        # Build CNN model
        cnn_model = tf.keras.Sequential([
            tf.keras.layers.Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=input_shape),
            tf.keras.layers.MaxPooling1D(pool_size=2),
            tf.keras.layers.Conv1D(filters=32, kernel_size=3, activation='relu'),
            tf.keras.layers.MaxPooling1D(pool_size=2),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(16, activation='relu'),
            tf.keras.layers.Dense(3, activation='softmax'),  # 3 classes: buy, sell, hold
        ])
        
        # Build GRU model
        gru_model = tf.keras.Sequential([
            tf.keras.layers.GRU(64, return_sequences=True, input_shape=input_shape),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.GRU(32),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(16, activation="relu"),
            tf.keras.layers.Dense(3, activation="softmax"),  # 3 classes: buy, sell, hold
        ])
        
        # Create ensemble model
        ensemble_input = tf.keras.Input(shape=input_shape)
        
        # Pass input through each model
        lstm_output = lstm_model(ensemble_input)
        cnn_output = cnn_model(ensemble_input)
        gru_output = gru_model(ensemble_input)
        
        # Concatenate outputs
        concat_output = tf.keras.layers.Concatenate()([lstm_output, cnn_output, gru_output])
        
        # Add final dense layers
        x = tf.keras.layers.Dense(16, activation="relu")(concat_output)
        x = tf.keras.layers.Dropout(0.2)(x)
        ensemble_output = tf.keras.layers.Dense(3, activation="softmax")(x)
        
        # Create ensemble model
        ensemble_model = tf.keras.Model(inputs=ensemble_input, outputs=ensemble_output)
        
        # Compile model
        ensemble_model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss="categorical_crossentropy",
            metrics=["accuracy"],
        )
        
        self.model = ensemble_model
        logger.info("Built ensemble scalping model with LSTM, CNN, and GRU components")

    def preprocess_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Preprocess data for training or prediction.

        Args:
            df: DataFrame with OHLCV and indicator data.

        Returns:
            Tuple of (X, y) for training, or just X for prediction.
        """
        # Ensure all features are present
        for feature in self.features:
            if feature not in df.columns:
                raise ValueError(f"Feature {feature} not found in DataFrame")
        
        # Extract features
        data = df[self.features].values
        
        # Scale data
        scaled_data = self.scaler.fit_transform(data)
        
        # Create sequences
        X = []
        y = []
        
        for i in range(len(scaled_data) - self.sequence_length - self.prediction_horizon):
            X.append(scaled_data[i:i+self.sequence_length])
            
            # Calculate future price change
            future_price = df["close"].iloc[i+self.sequence_length+self.prediction_horizon]
            current_price = df["close"].iloc[i+self.sequence_length-1]
            price_change = (future_price - current_price) / current_price
            
            # Convert to classification: -1 (sell), 0 (hold), 1 (buy)
            if price_change > 0.005:  # 0.5% threshold for buy
                y.append([0, 0, 1])  # buy
            elif price_change < -0.005:  # -0.5% threshold for sell
                y.append([1, 0, 0])  # sell
            else:
                y.append([0, 1, 0])  # hold
        
        return np.array(X), np.array(y)

    def prepare_prediction_data(self, df: pd.DataFrame) -> np.ndarray:
        """
        Prepare data for prediction.

        Args:
            df: DataFrame with OHLCV and indicator data.

        Returns:
            Preprocessed data for prediction.
        """
        # Ensure all features are present
        for feature in self.features:
            if feature not in df.columns:
                raise ValueError(f"Feature {feature} not found in DataFrame")
        
        # Extract features
        data = df[self.features].values
        
        # Scale data
        scaled_data = self.scaler.fit_transform(data)
        
        # Take the last sequence_length data points
        X = scaled_data[-self.sequence_length:].reshape(1, self.sequence_length, len(self.features))
        
        return X

    def train(
        self,
        df: pd.DataFrame,
        epochs: int = 50,
        batch_size: int = 32,
        validation_split: float = 0.2,
        save_checkpoints: bool = True,
        checkpoint_path: Optional[str] = None,
        checkpoint_frequency: int = 10,
    ) -> Dict[str, List[float]]:
        """
        Train the model.

        Args:
            df: DataFrame with OHLCV and indicator data.
            epochs: Number of training epochs.
            batch_size: Batch size.
            validation_split: Validation split ratio.
            save_checkpoints: Whether to save checkpoints during training.
            checkpoint_path: Path to save checkpoints.
            checkpoint_frequency: Frequency of checkpoints (in epochs).

        Returns:
            Training history.
        """
        # Preprocess data
        X, y = self.preprocess_data(df)
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=validation_split, shuffle=False
        )
        
        # Define callbacks
        callbacks = []
        
        # Add checkpoint callback if requested
        if save_checkpoints and checkpoint_path:
            # Create custom callback for our checkpointing functionality
            class CheckpointCallback(tf.keras.callbacks.Callback):
                def __init__(self, model_instance, checkpoint_path, frequency):
                    self.model_instance = model_instance
                    self.checkpoint_path = checkpoint_path
                    self.frequency = frequency
                
                def on_epoch_end(self, epoch, logs=None):
                    if (epoch + 1) % self.frequency == 0:
                        self.model_instance.save_checkpoint(
                            self.checkpoint_path, 
                            epoch + 1, 
                            logs
                        )
            
            callbacks.append(CheckpointCallback(self, checkpoint_path, checkpoint_frequency))
        
        # Train model
        history = self.model.fit(
            X_train,
            y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_val, y_val),
            verbose=1,
            callbacks=callbacks,
        )
        
        logger.info(f"Trained scalping model for {epochs} epochs")
        return history.history

    def predict(self, df: pd.DataFrame) -> int:
        """
        Make a prediction.

        Args:
            df: DataFrame with OHLCV and indicator data.

        Returns:
            Prediction: -1 (sell), 0 (hold), 1 (buy)
        """
        if self.model is None:
            logger.error("Model not initialized")
            return 0  # Default to hold
        
        try:
            # Prepare data
            X = self.prepare_prediction_data(df)
            
            # Make prediction
            prediction = self.model.predict(X, verbose=0)[0]
            
            # Convert to action: -1 (sell), 0 (hold), 1 (buy)
            action = np.argmax(prediction)
            if action == 0:
                return -1  # sell
            elif action == 2:
                return 1  # buy
            else:
                return 0  # hold
        
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return 0  # Default to hold

    def save_model(self, path: str, version: str = None) -> None:
        """
        Save the model with versioning.

        Args:
            path: Base path to save the model.
            version: Version string. If None, uses timestamp.
        """
        if self.model is None:
            logger.error("Model not initialized")
            return
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Generate version if not provided
            if version is None:
                version = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create versioned path
            versioned_path = f"{path}_v{version}"
            
            # Save model
            self.model.save(versioned_path)
            
            # Save metadata
            metadata = {
                "version": version,
                "timestamp": datetime.datetime.now().isoformat(),
                "features": self.features,
                "sequence_length": self.sequence_length,
                "prediction_horizon": self.prediction_horizon,
                "performance_metrics": {},  # Will be filled in by the caller
            }
            
            with open(f"{versioned_path}_metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            # Create symlink to latest version
            latest_symlink = f"{path}_latest"
            if os.path.exists(latest_symlink) or os.path.islink(latest_symlink):
                os.remove(latest_symlink)
            
            try:
                os.symlink(versioned_path, latest_symlink)
            except Exception as e:
                logger.warning(f"Failed to create symlink: {e}")
            
            logger.info(f"Saved model version {version} to {versioned_path}")
            return versioned_path
        
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return None
    
    def save_checkpoint(self, path: str, epoch: int, metrics: dict = None) -> None:
        """
        Save a checkpoint during training.

        Args:
            path: Base path to save the checkpoint.
            epoch: Current epoch number.
            metrics: Training metrics to save.
        """
        if self.model is None:
            logger.error("Model not initialized")
            return
        
        try:
            # Create checkpoints directory
            checkpoint_dir = os.path.join(os.path.dirname(path), "checkpoints")
            os.makedirs(checkpoint_dir, exist_ok=True)
            
            # Create checkpoint path
            checkpoint_path = os.path.join(checkpoint_dir, f"{os.path.basename(path)}_epoch{epoch}")
            
            # Save model weights
            self.model.save_weights(checkpoint_path)
            
            # Save checkpoint metadata
            metadata = {
                "epoch": epoch,
                "timestamp": datetime.datetime.now().isoformat(),
                "metrics": metrics or {},
            }
            
            with open(f"{checkpoint_path}_metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved checkpoint at epoch {epoch} to {checkpoint_path}")
        
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def load_model(self, path: str, version: str = "latest") -> None:
        """
        Load a saved model with version support.

        Args:
            path: Base path to the saved model.
            version: Version to load. Use "latest" for the latest version.
        """
        try:
            # Determine which path to load
            if version == "latest":
                versioned_path = f"{path}_latest"
                if os.path.islink(versioned_path):
                    # Follow symlink
                    actual_path = os.readlink(versioned_path)
                    logger.info(f"Following symlink {versioned_path} to {actual_path}")
                    versioned_path = actual_path
            else:
                versioned_path = f"{path}_v{version}"
            
            # Load model
            self.model = tf.keras.models.load_model(versioned_path)
            
            # Load metadata if available
            metadata_path = f"{versioned_path}_metadata.json"
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                
                # Update model parameters from metadata if available
                if "features" in metadata:
                    self.features = metadata["features"]
                if "sequence_length" in metadata:
                    self.sequence_length = metadata["sequence_length"]
                if "prediction_horizon" in metadata:
                    self.prediction_horizon = metadata["prediction_horizon"]
                
                logger.info(f"Loaded model metadata from {metadata_path}")
            
            logger.info(f"Loaded model version {version} from {versioned_path}")
        
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            # Build a new model if loading fails
            self._build_model()
    
    def load_checkpoint(self, path: str, epoch: int) -> None:
        """
        Load a specific checkpoint.

        Args:
            path: Base path to the saved checkpoints.
            epoch: Epoch number to load.
        """
        try:
            # Construct checkpoint path
            checkpoint_dir = os.path.join(os.path.dirname(path), "checkpoints")
            checkpoint_path = os.path.join(checkpoint_dir, f"{os.path.basename(path)}_epoch{epoch}")
            
            # Ensure model is initialized
            if self.model is None:
                self._build_model()
            
            # Load weights
            self.model.load_weights(checkpoint_path)
            
            # Load metadata if available
            metadata_path = f"{checkpoint_path}_metadata.json"
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                logger.info(f"Loaded checkpoint metadata from {metadata_path}")
            
            logger.info(f"Loaded checkpoint from epoch {epoch}")
        
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            # Keep current model if loading fails
