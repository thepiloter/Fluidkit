import os
from pathlib import Path
from core.nodes import *
from typing import Dict, Set, Optional, Tuple, List


class ImportResolver:
    """
    Resolves import statements across FluidKit project files with file-scoped symbol resolution.
    
    Enhanced to handle symbol collisions by maintaining per-file symbol scopes while
    preserving global FastAPI/Pydantic symbol tracking for framework validation.
    """
    
    def __init__(self, files_being_analyzed: List[str]):
        """
        Initialize with the files we're actually analyzing.
        Project boundary is determined from these files.
        """
        self.project_root = self._determine_project_root(files_being_analyzed)
        self.symbols: Dict[str, ResolvedSymbol] = {}              # Global symbols (FastAPI/Pydantic)
        self.file_symbols: Dict[str, Dict[str, ResolvedSymbol]] = {}  # File-scoped symbols
        self.modules: Dict[str, str] = {}
        self.fastapi_symbols: Set[str] = set()
        self.pydantic_symbols: Set[str] = set()

    def _determine_project_root(self, file_paths: List[str]) -> Path:
        """Find the common root directory of all files being analyzed"""
        if not file_paths:
            return Path.cwd()
        
        # Convert to absolute paths and get their parent directories
        dirs = [Path(f).resolve().parent for f in file_paths]
        
        if len(dirs) == 1:
            return dirs[0]
        
        # Find the common path among all directories
        common_parts = []
        
        # Get path parts for each directory
        all_parts = [list(d.parts) for d in dirs]
        min_length = min(len(parts) for parts in all_parts)
        
        # Find common prefix
        for i in range(min_length):
            part = all_parts[0][i]
            if all(parts[i] == part for parts in all_parts):
                common_parts.append(part)
            else:
                break
        
        if common_parts:
            return Path(*common_parts)
        else:
            return Path.cwd()

    def resolve(self, compilation_units: Dict[str, CompilationUnit]) -> ImportRegistry:
        """
        Resolve all imports across all discovered CompilationUnits.
        
        Args:
            compilation_units: Dict mapping file_path -> CompilationUnit
            
        Returns:
            ImportRegistry with both global and file-scoped symbol resolution
        """
        # Clear previous resolution state
        self.symbols.clear()
        self.file_symbols.clear()
        self.modules.clear()
        self.fastapi_symbols.clear()
        self.pydantic_symbols.clear()
        
        # Process imports from each compilation unit
        for file_path, compilation_unit in compilation_units.items():
            try:
                self._process_compilation_unit_imports(compilation_unit)
            except Exception as e:
                print(f"Warning: Failed to process imports from {file_path}: {e}")
                continue
        
        return ImportRegistry(
            symbols=dict(self.symbols),
            project_root=str(self.project_root),
            file_symbols=dict(self.file_symbols),
            modules=dict(self.modules),
            fastapi_symbols=set(self.fastapi_symbols),
            pydantic_symbols=set(self.pydantic_symbols)
        )

    def _process_compilation_unit_imports(self, compilation_unit: CompilationUnit):
        """Process all imports from a single CompilationUnit"""
        
        if not compilation_unit.imports:
            return
        
        # Initialize file scope
        if compilation_unit.source_file not in self.file_symbols:
            self.file_symbols[compilation_unit.source_file] = {}
        
        for import_node in compilation_unit.imports:
            try:
                if import_node.import_type == ImportType.MODULE:
                    self._process_module_import(import_node, compilation_unit.source_file)
                elif import_node.import_type == ImportType.FROM_IMPORT:
                    self._process_from_import(import_node, compilation_unit.source_file)
                elif import_node.import_type == ImportType.STAR_IMPORT:
                    self._process_from_import(import_node, compilation_unit.source_file)  # Same logic
                    
            except Exception as e:
                print(f"Warning: Failed to process import {import_node.module} from {compilation_unit.source_file}: {e}")
                continue

    def _process_from_import(self, import_node: ImportNode, source_file: str):
        """Process from imports, registering both global and file-scoped symbols"""
        
        resolved_module = self._resolve_relative_import(import_node, source_file)
        is_fastapi, is_pydantic, is_within_project = self._classify_module(resolved_module)
        
        # Only process symbols from frameworks we care about or from within our project
        if not (is_fastapi or is_pydantic or is_within_project):
            return
        
        # Ensure file scope exists
        if source_file not in self.file_symbols:
            self.file_symbols[source_file] = {}
        
        for symbol_name in import_node.names:
            if symbol_name == "*":
                self._handle_star_import(resolved_module, source_file, is_fastapi, is_pydantic)
                continue
            
            full_path = f"{resolved_module}.{symbol_name}"
            
            resolved_symbol = ResolvedSymbol(
                name=symbol_name,
                full_path=full_path,
                source_file=source_file,
                alias=None
            )
            
            # ALWAYS add to file-scoped symbols (solves collision problem)
            self.file_symbols[source_file][symbol_name] = resolved_symbol
            
            # Add to global symbols only for framework detection (FastAPI/Pydantic)
            if is_fastapi or is_pydantic:
                # For framework symbols, global registration is OK since they don't collide
                self.symbols[symbol_name] = resolved_symbol
                
                if is_fastapi:
                    self.fastapi_symbols.add(symbol_name)
                elif is_pydantic:
                    self.pydantic_symbols.add(symbol_name)

    def _process_module_import(self, import_node: ImportNode, source_file: str):
        """Process module imports, registering aliases for relevant modules"""
        
        resolved_module = self._resolve_relative_import(import_node, source_file)
        is_fastapi, is_pydantic, is_within_project = self._classify_module(resolved_module)
        
        # Only register module aliases for modules we care about
        if is_fastapi or is_pydantic or is_within_project:
            module_alias = import_node.alias if import_node.alias else resolved_module
            self.modules[module_alias] = resolved_module

    def _resolve_relative_import(self, import_node: ImportNode, source_file: str) -> str:
        """Convert relative imports to absolute module paths"""
        
        if not import_node.is_relative:
            return import_node.module
        
        if not import_node.module:
            return import_node.module
        
        try:
            source_path = Path(source_file).resolve()
            current_dir = source_path.parent
            
            # Count dots in the module string to get the level
            dots = 0
            module_part = import_node.module
            
            while module_part.startswith('.'):
                dots += 1
                module_part = module_part[1:]
            
            if dots == 0:
                return import_node.module
            
            # Navigate up the directory tree based on dots
            target_dir = current_dir
            for _ in range(dots - 1):
                parent = target_dir.parent
                if parent == target_dir:  # Hit filesystem root
                    break
                target_dir = parent
            
            # Add module path parts if any
            if module_part:
                module_path_parts = module_part.split('.')
                for part in module_path_parts:
                    target_dir = target_dir / part
            
            try:
                relative_to_project = target_dir.relative_to(self.project_root)
                return str(relative_to_project).replace(os.sep, '.')
            except ValueError:
                # Target is outside project root
                return import_node.module
                
        except (OSError, ValueError):
            return import_node.module

    def _classify_module(self, module_path: str) -> Tuple[bool, bool, bool]:
        """
        Classify module based on logical boundaries, not hardcoded lists.
        Returns (is_fastapi, is_pydantic, is_within_project)
        """
        
        if not module_path:
            return False, False, False
        
        # Check if it's a framework we care about
        is_fastapi = module_path.startswith('fastapi')
        is_pydantic = module_path.startswith('pydantic')
        
        # Check if it's within our project boundary
        is_within_project = self._is_module_within_project(module_path)
        
        return is_fastapi, is_pydantic, is_within_project

    def _is_module_within_project(self, module_path: str) -> bool:
        """
        Determine if a module is within our project boundary.
        Project modules are those that resolve to paths within our project root.
        """
        
        # If module path contains no dots, it might be a top-level external module
        if '.' not in module_path:
            # Check if there's a corresponding file/directory in our project
            potential_path = self.project_root / (module_path + '.py')
            potential_dir = self.project_root / module_path
            return potential_path.exists() or potential_dir.exists()
        
        # For dotted modules, convert to path and check if it's within project
        module_as_path = Path(*module_path.split('.'))
        potential_file = self.project_root / module_as_path.with_suffix('.py')
        potential_dir = self.project_root / module_as_path
        
        return potential_file.exists() or potential_dir.exists()

    def _handle_star_import(self, resolved_module: str, source_file: str, 
                          is_fastapi: bool, is_pydantic: bool):
        """Handle star imports for modules we care about"""
        
        star_marker = f"__star_import__{resolved_module}"
        
        resolved_symbol = ResolvedSymbol(
            name="*",
            full_path=resolved_module,
            source_file=source_file,
            alias=None
        )
        
        # Add to file scope
        if source_file not in self.file_symbols:
            self.file_symbols[source_file] = {}
        self.file_symbols[source_file][star_marker] = resolved_symbol
        
        # Add to global if framework
        if is_fastapi or is_pydantic:
            self.symbols[star_marker] = resolved_symbol

    def is_project_symbol(self, symbol_name: str, file_path: str) -> bool:
        """Check if a symbol is from within the project (file-scoped check)"""
        if file_path not in self.file_symbols:
            return False
        
        symbol = self.file_symbols[file_path].get(symbol_name)
        if not symbol:
            return False
        
        _, _, is_within_project = self._classify_module(symbol.full_path.split('.')[0])
        return is_within_project

    # === DEBUGGING HELPERS === #
    
    def print_resolution_summary(self):
        """Print a summary of resolved symbols for debugging"""
        print(f"=== IMPORT RESOLUTION SUMMARY ===")
        print(f"Project Root: {self.project_root}")
        print(f"Total Global Symbols: {len(self.symbols)}")
        print(f"FastAPI Symbols: {sorted(self.fastapi_symbols)}")
        print(f"Pydantic Symbols: {sorted(self.pydantic_symbols)}")
        print(f"Module Aliases: {self.modules}")
        
        print(f"\nFile-Scoped Symbols: {len(self.file_symbols)} files")
        for file_path, symbols in self.file_symbols.items():
            if symbols:
                print(f"  {file_path}: {len(symbols)} symbols")
                for name, symbol in sorted(symbols.items()):
                    if not name.startswith("__star_import__"):
                        print(f"    {name} → {symbol.full_path}")
        print("=" * 40)

    def validate_symbol_origin(self, symbol_name: str, expected_module: str, file_path: str) -> bool:
        """
        Validate that a symbol comes from the expected module within file context.
        
        Args:
            symbol_name: Name of the symbol to check
            expected_module: Expected module ("fastapi", "pydantic", etc.)
            file_path: File where symbol is used
            
        Returns:
            True if symbol is from expected module
        """
        # Check file-scoped first
        if file_path in self.file_symbols and symbol_name in self.file_symbols[file_path]:
            symbol = self.file_symbols[file_path][symbol_name]
            actual_module = symbol.full_path.split('.')[0]
            return actual_module == expected_module
        
        # Fallback to global symbols
        if symbol_name in self.symbols:
            symbol = self.symbols[symbol_name]
            actual_module = symbol.full_path.split('.')[0]
            return actual_module == expected_module
        
        return False
