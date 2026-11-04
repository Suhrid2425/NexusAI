from core.llm import extract_calculation_expression

expression = extract_calculation_expression(
    "Calculate 25 percent of 80000"
)

print("Generated expression:", expression)