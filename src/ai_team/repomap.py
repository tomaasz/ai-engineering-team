"""AST-based repository mapping for compact codebase context."""
import ast
from pathlib import Path


IGNORED_DIRS = {
    '.git', '.ai', '.ai-team', 'venv', '.venv', '__pycache__',
    'dist', 'build', 'node_modules', '.egg-info', '.pytest_cache'
}


def _extract_py_symbols(file_path: Path) -> list[str]:
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
        tree = ast.parse(content, filename=str(file_path))
    except Exception:
        return []

    lines = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            lines.append(f"  class {node.name}:")
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [a.arg for a in item.args.args]
                    lines.append(f"    def {item.name}({', '.join(args)}): ...")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            lines.append(f"  def {node.name}({', '.join(args)}): ...")
    return lines


def generate_repomap(project: Path, max_chars: int = 8000) -> str:
    """Generate a compact structural symbol map of the repository."""
    project = project.resolve()
    map_lines = []

    all_files = []
    try:
        for p in project.rglob('*'):
            if not p.is_file():
                continue
            rel_parts = p.relative_to(project).parts
            if any(part in IGNORED_DIRS or part.startswith('.tmp') or part.endswith('.egg-info') for part in rel_parts):
                continue
            all_files.append(p)
    except Exception:
        return ''

    all_files.sort(key=lambda x: str(x.relative_to(project)))

    total_chars = 0
    for p in all_files:
        rel = p.relative_to(project).as_posix()
        if p.suffix == '.py':
            symbols = _extract_py_symbols(p)
            if symbols:
                chunk = f"{rel}:\n" + "\n".join(symbols) + "\n"
            else:
                chunk = f"{rel}\n"
        elif p.suffix in {'.ts', '.js', '.jsx', '.tsx', '.go', '.rs', '.sql', '.json', '.md', '.toml', '.yml', '.yaml'}:
            chunk = f"{rel}\n"
        else:
            continue

        if total_chars + len(chunk) > max_chars:
            map_lines.append("... (remaining files truncated for budget)\n")
            break

        map_lines.append(chunk)
        total_chars += len(chunk)

    return "".join(map_lines).strip()
