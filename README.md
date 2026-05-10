# sheLLm (CachyOS Native)

An autonomous, ontological agentic interface operating at the kernel level for Arch/CachyOS via the Fish shell and Python.

## Architecture

**Tri-Kernel to Dual-Kernel Transition:** 
sheLLm has aggressively purged all legacy Windows and PowerShell code, optimizing strictly for `[POSIX_CACHYOS]`. 
It utilizes a **Dual-Kernel Routing Protocol (DTRM)**:
1. **VECTOR A (Fish):** System execution, Wayland/KDE interaction, native OS configuration.
2. **VECTOR B (Python):** Scraping, algorithms, complex JSON transformations, logic processing.

## Features
- **Dynamic Tool Routing Mechanism (DTRM):** Autonomously selects between `fish` shell execution and `python` execution.
- **Deep Telemetry Logging:** Dual-stream JSON lines capturing LLM cognitive processes alongside system `exit_code: 0` confirmation loops.
- **Advanced Parameter Matrix:** Dynamically injected runtime awareness (e.g. `CURRENT_OS: CachyOS Linux`).
- **Elevation Recovery:** Handles `Permission denied` paths automatically by shifting execution into a `pkexec` elevated context.
- **Visual & Audible Subsystem Notification:** Uses native KDE integrations (`notify-send` & `espeak-ng`).

## Deployment Structure
This repository represents a bare-bones, structurally clean deployment of the sheLLm architecture, strictly pruned of redundant nodes and old artifact data.

### Professional Installation (Auto-Updating)
Deploy the installer via bash. This automatically sets up the environment, dependencies, and a self-updating global executable wrapper.

```bash
curl -sSL https://raw.githubusercontent.com/lordmarcus13/shellm-cachyos/main/install.sh | bash
```

Once installed, simply run `shellm` from anywhere in your terminal. 
Every time you launch `shellm`, it will autonomously synchronize with this repository (`git pull origin main`) to ensure you are executing the latest architectural iteration.
