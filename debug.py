from transformers.validation_transformer import process_fluidkit_project

out = process_fluidkit_project([
    "examples/test_project/main.py",
    "examples/test_project/models.py",      # This contains @interface models!
    "examples/test_project/shared/auth.py"  # Optional, for completeness
])

# print(out)
