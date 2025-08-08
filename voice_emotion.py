import librosa
import torch
from transformers import HubertForSequenceClassification, Wav2Vec2FeatureExtractor

# Load model once (to avoid reloading on every request)
model_name = "superb/hubert-large-superb-er"
model = HubertForSequenceClassification.from_pretrained(model_name)
feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(model_name)

# MSP-Podcast labels
labels = ['angry', 'happy', 'neutral', 'sad']

def detect_voice_emotion(audio_path):
    print(f"📥 Loading audio: {audio_path}")
    audio, sampling_rate = librosa.load(audio_path, sr=16000)

    print(f"🎧 Audio loaded. Duration: {len(audio)/sampling_rate:.2f}s, Sample rate: {sampling_rate}")

    if len(audio) < 16000:  # less than 1 second
        raise ValueError("Audio too short for emotion analysis. Minimum 1 second required.")

    # Extract features
    inputs = feature_extractor(audio, sampling_rate=16000, return_tensors="pt", padding=True)

    # Predict
    with torch.no_grad():
        logits = model(**inputs).logits

    predicted_id = torch.argmax(logits).item()
    confidence = torch.nn.functional.softmax(logits, dim=1)[0][predicted_id].item() * 100
    predicted_emotion = labels[predicted_id]

    print(f"🎯 Predicted Emotion: {predicted_emotion} ({confidence:.2f}%)")

    return {
        "emotion": predicted_emotion,
        "confidence": f"{confidence:.2f}%"
    }
