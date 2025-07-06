from core.nodes import *
from typing import Dict, List, Optional
from transformers.resolution_transformer import ImportResolver
from transformers.discovery_transformer import DiscoveryTransformer
from pathlib import Path


class ValidationStage:
    """
    Validates discovered CompilationUnits using file-scoped import resolution.
    
    Enhanced to detect @interface models across project files with proper symbol
    collision handling while preserving explicit annotation validation.
    """
    
    def __init__(self, import_registry: ImportRegistry, interface_models: Dict[str, Set[str]]):
        self.import_registry = import_registry
        self.interface_models = interface_models  # file_path -> {model_names}
    
    def validate_compilation_units(self, compilation_units: Dict[str, CompilationUnit]) -> Dict[str, CompilationUnit]:
        """
        Validate all compilation units and return cleaned IR.
        
        Args:
            compilation_units: Raw compilation units from discovery
            
        Returns:
            Dict of validated compilation units ready for code generation
        """
        validated_units = {}
        
        for file_path, unit in compilation_units.items():
            validated_unit = self.validate_compilation_unit(unit)
            validated_units[file_path] = validated_unit
        
        return validated_units
    
    def validate_compilation_unit(self, compilation_unit: CompilationUnit) -> CompilationUnit:
        """
        Validate a single CompilationUnit using import context.
        
        Returns a new CompilationUnit with validated routes and models.
        """
        validated_routes = []
        validated_models = []
        
        # Validate and filter routes
        for route in compilation_unit.routes:
            validated_route = self._validate_and_fix_route(route, compilation_unit)
            if validated_route:  # Only include valid routes
                validated_routes.append(validated_route)
        
        # Validate and filter models  
        for model in compilation_unit.models:
            if self._validate_model(model, compilation_unit.source_file):
                validated_models.append(model)
        
        return CompilationUnit(
            models=validated_models,
            routes=validated_routes,
            imports=compilation_unit.imports,
            source_file=compilation_unit.source_file,
            metadata=compilation_unit.metadata
        )
    
    def _validate_model(self, model: ModelNode, source_file: str) -> bool:
        """
        Validate that model uses actual Pydantic BaseModel with file-scoped resolution.
        
        For V1: Check if BaseModel inheritance is from Pydantic using file context.
        """
        if not model.inheritance:
            return True  # No inheritance requirements
        
        for base_class in model.inheritance:
            if base_class == "BaseModel":
                # Check if BaseModel is from Pydantic in this file's context
                resolved_symbol = self.import_registry.resolve_symbol_in_file("BaseModel", source_file)
                if resolved_symbol:
                    module = resolved_symbol.full_path.split('.')[0]
                    if module != "pydantic":
                        print(f"Warning: Model {model.name} uses BaseModel from {module}, not Pydantic - skipping")
                        return False
                elif not self.import_registry.is_pydantic_symbol("BaseModel"):
                    print(f"Warning: Model {model.name} uses unresolved BaseModel - skipping")
                    return False
        
        return True
    
    def _validate_and_fix_route(self, route: RouteNode, compilation_unit: CompilationUnit) -> Optional[RouteNode]:
        """
        Validate route and fix parameter classifications using file-scoped resolution.
        
        Main job: Validate FastAPI symbols and classify parameters intelligently.
        """
        validated_parameters = []
        
        for param in route.parameters:
            validated_param = self._validate_and_reclassify_parameter(param, route.path, compilation_unit)
            validated_parameters.append(validated_param)
        
        # Create new RouteNode with validated parameters
        return RouteNode(
            name=route.name,
            method=route.method,
            path=route.path,
            parameters=validated_parameters,
            return_type=route.return_type,
            docstring=route.docstring,
            location=route.location,
            ast_node=route.ast_node
        )
    
    def _validate_and_reclassify_parameter(self, param: Field, route_path: str, compilation_unit: CompilationUnit) -> Field:
        """
        Core validation: Validate FastAPI symbols and classify parameters intelligently.
        
        Enhanced with file-scoped @interface model detection for BODY parameter classification.
        """
        # No constraints means it's a model field or untyped param
        if not param.constraints:
            return param
        
        # STEP 1: Validate explicit FastAPI annotations (PRESERVE EXISTING LOGIC)
        if param.constraints.fastapi_annotation:
            annotation_name = param.constraints.fastapi_annotation
            
            # Use file-scoped validation for FastAPI symbols
            resolved_symbol = self.import_registry.resolve_symbol_in_file(annotation_name, compilation_unit.source_file)
            if resolved_symbol:
                module = resolved_symbol.full_path.split('.')[0]
                if module != "fastapi":
                    print(f"Warning: {annotation_name} for parameter {param.name} is from {module}, not FastAPI")
                    return self._create_unknown_parameter(param)
            elif not self.import_registry.is_fastapi_symbol(annotation_name):
                print(f"Warning: {annotation_name} for parameter {param.name} is not from FastAPI")
                return self._create_unknown_parameter(param)
            # Valid FastAPI symbol - keep as is
            return param
        
        # STEP 2: Intelligent classification for UNKNOWN parameters
        if param.constraints.parameter_type == ParameterType.UNKNOWN:
            return self._classify_parameter_with_context(param, route_path, compilation_unit)
        
        # STEP 3: Preserve any other classifications from Discovery
        return param
    
    def _classify_parameter_with_context(self, param: Field, route_path: str, compilation_unit: CompilationUnit) -> Field:
        """
        Classify UNKNOWN parameters using full import and @interface model context.
        
        Conservative approach - only classify if we can definitively prove the type.
        Uses file-scoped symbol resolution to avoid collision issues.
        """
        
        # Rule 1: Path parameters (100% unambiguous)
        if f"{{{param.name}}}" in route_path:
            return self._set_parameter_type(param, ParameterType.PATH)
        
        # Rule 2: Local enums become QUERY parameters (NEW!)
        if param.annotation.custom_type:
            if self._is_enum_type(param.annotation.custom_type, compilation_unit):
                return self._set_parameter_type(param, ParameterType.QUERY)
        
        # Rule 3: @interface models become BODY parameters (definitive check)
        if param.annotation.custom_type:
            if self._is_interface_model(param.annotation.custom_type, compilation_unit):
                return self._set_parameter_type(param, ParameterType.BODY)
        
        # Rule 4: Simple types become query parameters (FastAPI standard)
        if param.annotation.base_type in [BaseType.STRING, BaseType.NUMBER, BaseType.BOOLEAN]:
            return self._set_parameter_type(param, ParameterType.QUERY)
            
        # Rule 5: Optional simple types become query parameters
        if (param.annotation.container == ContainerType.OPTIONAL and 
            param.annotation.args and
            param.annotation.args[0].base_type in [BaseType.STRING, BaseType.NUMBER, BaseType.BOOLEAN]):
            return self._set_parameter_type(param, ParameterType.QUERY)
        
        # Everything else stays UNKNOWN (requires explicit annotation)
        return param
    
    def _is_enum_type(self, type_name: str, compilation_unit: CompilationUnit) -> bool:
        """
        Check if type is a local enum (should be query parameter).
        
        Only checks current file's models to avoid complexity - imported enums 
        will still be classified as BODY in V1.
        """
        # Check current file's @interface models
        for model in compilation_unit.models:
            if model.name == type_name:
                # Check if it has Enum inheritance
                if model.inheritance:
                    return any("Enum" in base for base in model.inheritance)
        # TODO: Implement enum detection using file-scoped symbol resolution
        return False
    
    def _is_interface_model(self, type_name: str, compilation_unit: CompilationUnit) -> bool:
        """Check if type is a known @interface model using absolute path matching."""
        
        source_file = compilation_unit.source_file
        
        # Rule 1: Check current file's @interface models
        abs_source_file = str(Path(source_file).resolve())
        current_file_models = self.interface_models.get(abs_source_file, set())
        if type_name in current_file_models:
            return True
        
        # Rule 2: Use file-scoped symbol resolution
        resolved_symbol = self.import_registry.resolve_symbol_in_file(type_name, source_file)
        if resolved_symbol:
            symbol_module_path = resolved_symbol.full_path.rsplit('.', 1)[0]
            symbol_source_file = self._module_path_to_file_path(symbol_module_path)
            
            if symbol_source_file and symbol_source_file in self.interface_models:
                imported_models = self.interface_models[symbol_source_file]
                if type_name in imported_models:
                    return True
        
        return False
    
    def _module_path_to_file_path(self, module_path: str) -> Optional[str]:
        """
        Convert module path to absolute file path (OS-independent).
        
        Args:
            module_path: Module path like "models" or "shared.auth"
            
        Returns:
            Absolute file path if it exists, None otherwise
        """
        if not module_path:
            return None
        
        try:
            # Use project root from ImportRegistry (already absolute)
            project_root = Path(self.import_registry.project_root)
            
            # Build file path from module parts (pathlib handles OS differences)
            module_parts = module_path.split('.')
            file_path = project_root
            for part in module_parts:
                file_path = file_path / part
            
            # Add .py extension
            file_path = file_path.with_suffix('.py')
            
            # Return absolute path if file exists (OS-independent)
            if file_path.exists():
                return str(file_path.resolve())
            
        except Exception as e:
            print(f"Warning: Failed to convert module path {module_path} to file path: {e}")
        
        return None
    
    def _set_parameter_type(self, param: Field, param_type: ParameterType) -> Field:
        """
        Create a new Field with updated parameter type while preserving other data.
        """
        new_constraints = FieldConstraints(
            parameter_type=param_type,
            fastapi_annotation=param.constraints.fastapi_annotation,
            min_value=param.constraints.min_value,
            max_value=param.constraints.max_value,
            min_length=param.constraints.min_length,
            max_length=param.constraints.max_length,
            regex_pattern=param.constraints.regex_pattern,
            media_type=param.constraints.media_type,
            include_in_schema=param.constraints.include_in_schema,
            deprecated=param.constraints.deprecated,
            custom=param.constraints.custom
        )
        
        return Field(
            name=param.name,
            annotation=param.annotation,
            default=param.default,
            constraints=new_constraints,
            description=param.description
        )
    
    def _create_unknown_parameter(self, param: Field) -> Field:
        """
        Create a parameter with UNKNOWN classification.
        
        Preserves type annotation and constraints but clears FastAPI-specific info.
        """
        # Keep validation constraints but clear FastAPI classification
        new_constraints = FieldConstraints(
            parameter_type=ParameterType.UNKNOWN,
            fastapi_annotation=None,  # Clear invalid annotation
            # Preserve validation constraints
            min_value=param.constraints.min_value,
            max_value=param.constraints.max_value,
            min_length=param.constraints.min_length,
            max_length=param.constraints.max_length,
            regex_pattern=param.constraints.regex_pattern,
            deprecated=param.constraints.deprecated,
            custom=param.constraints.custom
        )
        
        return Field(
            name=param.name,
            annotation=param.annotation,
            default=param.default,
            constraints=new_constraints,
            description=param.description
        )
    
    # === DEBUGGING HELPERS === #
    
    def print_validation_summary(self, original_units: Dict[str, CompilationUnit], 
                                validated_units: Dict[str, CompilationUnit]):
        """Print summary of validation results"""
        print("=== VALIDATION SUMMARY ===")
        
        total_original_routes = sum(len(unit.routes) for unit in original_units.values())
        total_validated_routes = sum(len(unit.routes) for unit in validated_units.values())
        total_original_models = sum(len(unit.models) for unit in original_units.values())
        total_validated_models = sum(len(unit.models) for unit in validated_units.values())
        
        print(f"Routes: {total_original_routes} → {total_validated_routes}")
        print(f"Models: {total_original_models} → {total_validated_models}")
        
        # Count parameter type distribution
        param_types = {}
        for unit in validated_units.values():
            for route in unit.routes:
                for param in route.parameters:
                    if param.constraints and param.constraints.parameter_type:
                        ptype = param.constraints.parameter_type.value
                        param_types[ptype] = param_types.get(ptype, 0) + 1
        
        print(f"Parameter types: {param_types}")
        
        # Show @interface models discovered
        total_interface_models = sum(len(models) for models in self.interface_models.values())
        print(f"@interface models: {total_interface_models}")
        for file_path, models in self.interface_models.items():
            if models:
                print(f"  {file_path}: {sorted(models)}")
        
        print("=" * 30)


def collect_interface_models(compilation_units: Dict[str, CompilationUnit]) -> Dict[str, Set[str]]:
    """
    Collect all @interface model names organized by source file.
    
    Args:
        compilation_units: Discovery stage output
        
    Returns:
        Dict mapping absolute_file_path -> set of @interface model names
    """
    interface_models = {}
    
    for file_path, unit in compilation_units.items():
        # Always use absolute paths for consistent cross-platform lookup
        abs_file_path = str(Path(file_path).resolve())
        model_names = {model.name for model in unit.models}
        if model_names:
            interface_models[abs_file_path] = model_names
    
    return interface_models


# === COMPLETE PIPELINE INTEGRATION === #

def process_fluidkit_project(file_paths: List[str]) -> Dict[str, CompilationUnit]:
    """
    Complete FluidKit processing pipeline with file-scoped @interface model detection.
    
    Returns validated CompilationUnits ready for TypeScript generation.
    """
    
    # Stage 1: Discovery
    print("Stage 1: Discovering models and routes...")
    compilation_units = {}
    for file_path in file_paths:
        transformer = DiscoveryTransformer(file_path)
        with open(file_path, 'r') as f:
            code = f.read()
        compilation_units[file_path] = transformer.transform(code)
    
    # NEW: Collect all @interface models across project
    interface_models = collect_interface_models(compilation_units)
    
    # Stage 2: Import Resolution with file-scoped symbols
    print("Stage 2: Resolving imports with file-scoped symbol tracking...")
    resolver = ImportResolver(file_paths)
    import_registry = resolver.resolve(compilation_units)
    
    # Stage 3: Enhanced Validation with file-scoped @interface model detection
    print("Stage 3: Validating FastAPI/Pydantic symbols with collision handling...")
    validator = ValidationStage(import_registry, interface_models)
    validated_units = validator.validate_compilation_units(compilation_units)
    
    # Debug output
    resolver.print_resolution_summary()
    validator.print_validation_summary(compilation_units, validated_units)
    
    return validated_units
