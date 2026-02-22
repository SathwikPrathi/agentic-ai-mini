from app.agents.rule_based import build_plan


def test_weather_plan_contains_weather_step():
    plan = build_plan("Get the current weather in New York and give me a short summary")
    assert plan.steps[0].type.value == "WEATHER"
