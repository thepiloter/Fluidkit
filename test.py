from parsers.pydantic_parser import PydanticParser
from generators.interface_generator import TypeScriptGenerator

def main():
    input_file = "examples/test_model.py"
    output_file = "examples/test_output.ts"

    parser = PydanticParser()
    generator = TypeScriptGenerator()

    compilation_unit = parser.parse_file(input_file)
    generated_code = generator.generate(compilation_unit)

    with open(output_file, 'w') as f:
        f.write(generated_code)
    
    print("TypeScript interface generated successfully!")
    
if __name__ == "__main__":
    main()
