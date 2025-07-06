from generators.import_generator import test_generate_imports
from generators.interface_generator import test_generate_interface
from generators.fetch_wrapper_generator import test_generate_fetch_wrapper
from generators.pipeline import generate_fluidkit_project, write_generated_files

def main():
    test_generate_imports()
    test_generate_interface()
    test_generate_fetch_wrapper()

    generated_files = generate_fluidkit_project(["examples/test_model.py"])
    write_generated_files(generated_files)
    print("TypeScript generated successfully!")
    
if __name__ == "__main__":
    main()
