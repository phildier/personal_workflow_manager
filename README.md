# pwm

Typer-based CLI for personal workflow management.

### Install (dev)
```bash
pipx install -e .
# or
pip install -e .
```

### Config locations
- User config: `~/.config/pwm/config.toml` (optional)
- Project config: `<repo>/.pwm.toml` (optional)
- Env vars override selected fields (see below)

### Run
```bash
pwm context
```
