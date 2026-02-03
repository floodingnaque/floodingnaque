# Floodingnaque - Flood Prediction System Instructions

## Project Context
A developmental research project implementing a machine learning-based flood prediction system with Flask backend and React/TypeScript frontend. Uses Random Forest Classifier to provide three-level risk assessments (Low, Medium, High) based on weather data from multiple sources.

## Core Architecture

### Backend (Flask/Python)
- RESTful API with versioned endpoints (`/api/v1/...`)
- Singleton ModelLoader class for ML model management
- Rate limiting and caching for performance
- Integration with: Meteostat, OpenWeatherMap, Google Earth Engine

### Frontend (React/TypeScript)
- Functional components with hooks
- Risk visualization and alert notifications
- Type-safe API communication

### ML Pipeline
- Random Forest Classifier for predictions
- Model versioning system (model_v1.pkl, model_v2.pkl, etc.)
- Three-level risk classification module

## Coding Standards

### Python
```python
# Type hints required
def predict_flood_risk(rainfall: float, water_level: float) -> dict[str, any]:
    """Predict flood risk based on weather parameters.

    Args:
        rainfall: Precipitation in mm
        water_level: Current water level in meters

    Returns:
        Dictionary with prediction and confidence score
    """
    pass

# Singleton pattern for model loading
class ModelLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### TypeScript
```typescript
// Strict interfaces for API responses
interface FloodPrediction {
  riskLevel: 'low' | 'medium' | 'high';
  confidence: number;
  timestamp: string;
}

// Async/await with error handling
const fetchPrediction = async (): Promise => {
  try {
    const response = await fetch('/api/v1/predict');
    return await response.json();
  } catch (error) {
    console.error('Prediction failed:', error);
    throw error;
  }
};
```

## API Design Patterns

### Endpoints
- POST `/api/v1/predict` - Submit prediction request
- GET `/api/v1/history` - Retrieve historical predictions
- GET `/api/v1/weather/current` - Current weather data
- GET `/api/v1/risk-levels` - Current risk assessment

### Response Format
```json
{
  "status": "success",
  "data": {
    "prediction": "medium",
    "confidence": 0.85,
    "factors": {
      "rainfall": 45.2,
      "water_level": 3.1
    }
  },
  "timestamp": "2026-01-26T10:30:00Z"
}
```

## Weather Service Integration

### Priority Order
1. Meteostat (primary, no API key required)
2. OpenWeatherMap (fallback, real-time data)
3. Google Earth Engine (satellite data backup)

### Implementation Pattern
```python
class WeatherServiceManager:
    def fetch_weather_data(self, location: tuple[float, float]) -> dict:
        """Fetch with fallback chain."""
        try:
            return self.meteostat_service.get_data(location)
        except ServiceUnavailable:
            return self.openweather_service.get_data(location)
```

## ML Model Guidelines

### Model Training
- Feature engineering: rainfall, water level, soil moisture, historical patterns
- Train/test split: 80/20
- Cross-validation: 5-fold
- Save with joblib: `joblib.dump(model, f'models/model_v{version}.pkl')`

### Prediction Pipeline
```python
def predict_with_confidence(features: np.ndarray) -> tuple[str, float]:
    """Return prediction and confidence score."""
    prediction = model.predict(features)[0]
    probabilities = model.predict_proba(features)[0]
    confidence = max(probabilities)

    risk_level = classify_risk(prediction)
    return risk_level, confidence

def classify_risk(value: float) -> str:
    """Map prediction to risk levels."""
    if value < 0.3:
        return 'low'
    elif value < 0.7:
        return 'medium'
    return 'high'
```

## Performance Optimization

### Caching Strategy
- Weather data: 15-minute TTL
- Model predictions: 5-minute TTL with input hash key
- Historical data: 1-hour TTL

### Rate Limiting
```python
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=lambda: request.remote_addr,
    default_limits=["100 per hour", "20 per minute"]
)

@app.route('/api/v1/predict', methods=['POST'])
@limiter.limit("10 per minute")
def predict():
    pass
```

## Error Handling

### Backend
- Use proper HTTP status codes (400, 404, 500, 503)
- Log errors with context: `logger.error(f"Prediction failed: {error}", exc_info=True)`
- Return user-friendly messages

### Frontend
- Implement error boundaries for React components
- Show toast notifications for API errors
- Provide retry mechanisms for failed requests

## Testing Requirements

### Backend Tests
```python
def test_flood_prediction():
    """Test prediction with known inputs."""
    result = predict_flood_risk(rainfall=50.0, water_level=4.5)
    assert result['risk_level'] in ['low', 'medium', 'high']
    assert 0 <= result['confidence'] <= 1
```

### Frontend Tests
```typescript
test('displays risk level correctly', async () => {
  render();
  await waitFor(() => {
    expect(screen.getByText(/risk level/i)).toBeInTheDocument();
  });
});
```

## Security Best Practices
- Store API keys in `.env.development`: `OPENWEATHER_API_KEY=xxx`
- Validate input ranges: rainfall (0-500mm), water_level (0-10m)
- Implement CORS with specific origins
- Sanitize user inputs before database queries
- Rate limit prediction endpoints to prevent abuse

## Documentation
- Docstrings for all Python functions/classes
- JSDoc for complex TypeScript functions
- API documentation with request/response examples
- Model training notebooks with explanations
- CHANGELOG.md for model versions

## Common Patterns to Use

### Lazy Model Loading
```python
class ModelLoader:
    def __init__(self):
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = joblib.load('models/latest.pkl')
        return self._model
```

### React Custom Hooks
```typescript
const usePrediction = () => {
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchPrediction = useCallback(async () => {
    setLoading(true);
    // fetch logic
  }, []);

  return { prediction, loading, fetchPrediction };
};
```

## File Organization
```
floodingnaque/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── models/       # ML models
│   │   ├── services/     # Weather services
│   │   └── utils/        # Helper functions
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom hooks
│   │   ├── services/     # API calls
│   │   └── types/        # TypeScript interfaces
│   └── tests/
└── models/               # Trained model files
```

**When generating code, prioritize: reliability > performance > readability > conciseness**
