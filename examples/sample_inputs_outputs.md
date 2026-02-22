## Sample input/output (illustrative)

### Input

`Get the current weather in New York and give me a short summary.`

### Typical Plan (Agent A)

```json
{
  "user_intent": "Get weather and summarize",
  "steps": [
    {"id": "step_1", "type": "WEATHER", "input": {"location": "New York"}, "depends_on": []},
    {"id": "step_2", "type": "SUMMARIZE", "input": {"text": "{{step_1.output}}"}, "depends_on": ["step_1"]}
  ],
  "output_style": "concise"
}
```

### Typical ExecutionResult (Agent B)

```json
{
  "steps": [
    {
      "step_id": "step_1",
      "tool": "weather",
      "input": {"location": "New York"},
      "output": {
        "location": {"name": "New York", "country": "United States", "latitude": 40.71, "longitude": -74.01},
        "current": {"temperature_2m": 10.2, "wind_speed_10m": 12.0, "weather_code": 3},
        "units": {"temperature_2m": "°C", "wind_speed_10m": "km/h"}
      }
    },
    {
      "step_id": "step_2",
      "tool": "summarize",
      "input": {"text": "{{step_1.output}}"},
      "output": {"summary": "New York is currently around 10°C with light wind; overall conditions are partly cloudy."}
    }
  ],
  "errors": []
}
```

### Final Answer (Agent A)

`New York is currently around 10°C with light wind; overall conditions are partly cloudy.`
