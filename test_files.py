from core.nodes import *
from generators.pipeline import generate_fluidkit_project, write_generated_files

file_paths = [
    "examples/test_project/main.py",
    "examples/test_project/models.py",
    "examples/test_project/shared/auth.py"
]

generated_files = generate_fluidkit_project(file_paths)

# Print generated file paths and preview content
print("\n=== GENERATED FILES ===")
for file_path, content in generated_files.items():
    print(f"\n📁 {file_path}")
    print(f"📄 {len(content.splitlines())} lines")
    # Show first few lines as preview
    lines = content.splitlines()
    for i, line in enumerate(lines[:5]):
        print(f"   {i+1:2d}: {line}")
    if len(lines) > 5:
        print(f"   ... ({len(lines)-5} more lines)")

write_generated_files(generated_files)
