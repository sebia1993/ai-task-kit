"""Repository entry point; the standalone skill contains the canonical helper."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parent / '.agents/skills/ai-task-kit/scripts/taskkit.py'),
                   run_name='__main__')
