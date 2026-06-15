from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import zipfile

from .errors import IntentoProjectError, IntentoRuntimeError
from .stdlib import get_library

SUPPORTED_RUNTIME = 'INTENTO 1.1'
SUPPORTED_RUNTIMES = {'INTENTO 1.0', 'INTENTO 1.1'}


@dataclass
class IntentoProject:
    root: Path
    entry: str = 'main.intento'
    runtime: str | None = None
    libraries: list[str] = field(default_factory=list)
    permissions: str | None = None
    features: list[str] = field(default_factory=list)

    @property
    def entry_path(self) -> Path:
        return (self.root / self.entry).resolve()


def _strip_project_comment(line: str) -> str:
    return line.split('#', 1)[0]


def _split_csv(value: str) -> list[str]:
    if not value.strip():
        return []
    return [part.strip() for part in value.split(',') if part.strip()]


def parse_project_file(path: Path) -> IntentoProject:
    if not path.exists():
        raise IntentoProjectError(f'project file not found: {path}')
    root = path.parent.resolve()
    project = IntentoProject(root=root)
    allowed = {'runtime', 'entry', 'libraries', 'permissions', 'features'}
    for line_no, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
        text = _strip_project_comment(raw).strip()
        if not text:
            continue
        if ':' not in text:
            raise IntentoProjectError(f'invalid project metadata line {line_no}: expected key: value')
        key, value = text.split(':', 1)
        key = key.strip().lower()
        value = value.strip()
        if key not in allowed:
            raise IntentoProjectError(f'unknown project metadata key `{key}` on line {line_no}')
        if key == 'runtime':
            project.runtime = value
        elif key == 'entry':
            project.entry = value or 'main.intento'
        elif key == 'libraries':
            project.libraries = _split_csv(value)
        elif key == 'permissions':
            project.permissions = value
        elif key == 'features':
            project.features = _split_csv(value)
    validate_project(project)
    return project


def validate_project(project: IntentoProject) -> None:
    if project.runtime and project.runtime not in SUPPORTED_RUNTIMES:
        raise IntentoProjectError(f'required Runtime version {project.runtime} is not supported')
    if not project.entry:
        raise IntentoProjectError('project entry cannot be empty')
    entry = project.entry_path
    try:
        entry.relative_to(project.root.resolve())
    except ValueError:
        raise IntentoProjectError('project entry is outside the project folder') from None
    if not entry.exists():
        raise IntentoProjectError(f'project entry file not found: {project.entry}')
    if entry.suffix != '.intento':
        raise IntentoProjectError('project entry must use the .intento extension')
    for library in project.libraries:
        if get_library(library) is None:
            local_actions_available = library == 'local' and (project.root / 'actions' / 'intento_actions.py').exists()
            if not local_actions_available:
                raise IntentoProjectError(f'required library `{library}` is not available')


def resolve_target(target: str | Path, workspace_override: str | Path | None = None) -> tuple[Path, Path, IntentoProject | None]:
    path = Path(target).resolve()
    if path.is_dir():
        project = parse_project_file(path / 'intento.project')
        workspace = Path(workspace_override).resolve() if workspace_override else project.root.resolve()
        return project.entry_path, workspace, project
    if not path.exists():
        raise IntentoRuntimeError(f'source file not found: {path}')
    if path.suffix != '.intento':
        raise IntentoRuntimeError('INTENTO source files must use the .intento extension')
    workspace = Path(workspace_override).resolve() if workspace_override else Path.cwd().resolve()
    return path, workspace, None


def read_source(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _project_title_from_name(name: str) -> str:
    cleaned = re.sub(r'[_-]+', ' ', name).strip()
    if not cleaned:
        return 'INTENTO Project'
    return ' '.join(part[:1].upper() + part[1:] for part in cleaned.split())


def _slug_from_title(title: str) -> str:
    text = title.strip().lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text or 'intento-project'


def init_project(folder: str | Path, force: bool = False) -> Path:
    """Create a standard INTENTO project skeleton and return its root path."""
    root = Path(folder).resolve()
    if root.exists() and any(root.iterdir()) and not force:
        raise IntentoProjectError(f'cannot initialize project because folder is not empty: {root}')
    root.mkdir(parents=True, exist_ok=True)

    name = root.name
    title = _project_title_from_name(name)
    slug = _slug_from_title(title)

    folders = [
        root / 'modules',
        root / 'actions',
        root / 'data',
        root / 'output',
        root / 'tests' / 'intentotests',
    ]
    for path in folders:
        path.mkdir(parents=True, exist_ok=True)

    files: dict[Path, str] = {
        root / 'intento.project': (
            f'runtime: {SUPPORTED_RUNTIME}\n'
            'entry: main.intento\n'
            'libraries: text\n'
            'permissions: read project files, write project files with confirmation\n'
            'features: modules, symbol operators, intentotests\n'
        ),
        root / 'main.intento': (
            'use library "text"\n'
            'use module "modules/formatting.intento" as formatting\n\n'
            f'remember title as "{title}"\n'
            'formatting.show_title with title\n'
            'use action "text.slugify" with title and call the result slug\n'
            'show slug\n'
        ),
        root / 'modules' / 'formatting.intento': (
            'to show_title with title:\n'
            '    show "== " plus title plus " =="\n'
        ),
        root / 'README.md': (
            f'# {title}\n\n'
            'Generated by INTENTO Runtime v1.1.\n\n'
            'Run the project:\n\n'
            '```bash\n'
            'python3 -m intento_runtime run . --show-logs\n'
            '```\n\n'
            'Check the project:\n\n'
            '```bash\n'
            'python3 -m intento_runtime check .\n'
            '```\n'
        ),
        root / 'tests' / 'intentotests' / 'project.intentotest': (
            'name: initialized project output\n'
            'program: ../../main.intento\n'
            'workspace: ../..\n'
            'expect output:\n'
            f'== {title} ==\n'
            f'{slug}\n'
            'end\n'
        ),
    }

    for path, content in files.items():
        if path.exists() and not force:
            raise IntentoProjectError(f'cannot overwrite existing file during init: {path}')
        path.write_text(content, encoding='utf-8')

    return root


def _should_package(path: Path) -> bool:
    if path.name == '__pycache__':
        return False
    if path.name.startswith('.') and path.name not in {'.intentotest'}:
        return False
    if path.suffix in {'.pyc', '.pyo'}:
        return False
    return True


def package_project(folder: str | Path, output: str | Path | None = None, include_output: bool = False) -> tuple[Path, int]:
    """Create a zip archive for a validated INTENTO project and return (zip path, file count)."""
    root = Path(folder).resolve()
    project = parse_project_file(root / 'intento.project')
    output_path = Path(output).resolve() if output else (root.parent / f'{root.name}.zip').resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob('*')):
            if not all(_should_package(part) for part in path.relative_to(root).parents):
                continue
            if not _should_package(path):
                continue
            if path.is_dir():
                continue
            if not include_output:
                try:
                    path.relative_to(root / 'output')
                    continue
                except ValueError:
                    pass
            if path.resolve() == output_path:
                continue
            arcname = Path(root.name) / path.relative_to(root)
            zf.write(path, arcname.as_posix())
            count += 1
    return output_path, count
