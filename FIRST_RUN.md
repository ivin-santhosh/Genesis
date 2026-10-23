# Genesis — first run

## Run immediately

Requires **Python 3.11+**, available from the official Python website. No third-party packages or models are required to launch the basic interactive assistant.

From the parent folder containing `Genesis`:

```powershell
python -m Genesis
```

On Windows, `start_genesis.bat` in the repository may be double-clicked; it invokes Python from the parent directory.

First-run commands: `/help`, `/calc (10+5)*2`, `/time`, `/system`, `/demo`, and `/doctor`. `/demo` writes its checkpoint to the user's `~/.genesis` folder; nothing is transmitted to a cloud service.

## Enable real local AI

If Ollama and a model are already installed and running, Genesis automatically detects one and lets you chat directly. Type `/models` and `/model NAME` to change models.

If no model is detected, the offline commands remain usable. Type **`/setup`**: the Doctor reports unmet requirements and offers (1) an explicitly approved supported repair or (2) guided manual repair steps and consequences. A local model usually requires installing Ollama and downloading several GB of model data; this cannot occur secretly or without a model choice.

The local AI mode uses a strictly bounded read-only tool set. For the older experimental LangGraph/Nexus/Coder/Thinker interface, see the legacy implementation and open integration issue: https://github.com/ivin-santhosh/Genesis/issues/5.

## Quality claim

The first-run launcher is usable without dependency downloads. The AI conversational component needs a local model, and **full legacy multi-agent production readiness has not been established**. The project must never represent offline fallback as equivalent to working model inference.
