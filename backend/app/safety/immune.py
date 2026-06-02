"""
ALAS Autonomous Immune System (Phase 16)

This module acts as the DevOps engineer for ALAS. It monitors the system for
unhandled exceptions, crashes, and anomalous behavior. When a crash occurs, it:
1. Captures the full stack trace and system state.
2. Invokes the Tree-of-Thoughts reasoner to diagnose the root cause.
3. Formulates a code patch to fix the bug.
4. Applies the patch to the local filesystem.
5. Triggers a hot-reload or restart to heal the system.
"""

import sys
import os
import traceback
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger("alas.safety.immune")

class ImmuneSystem:
    """The self-healing DevOps monitoring core."""

    def __init__(self):
        self.workspace_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.crash_logs_dir = self.workspace_dir / "logs" / "crashes"
        self.patches_dir = self.workspace_dir / "logs" / "patches"
        self.crash_logs_dir.mkdir(parents=True, exist_ok=True)
        self.patches_dir.mkdir(parents=True, exist_ok=True)
        
        self.active = False
        self._is_healing = False

    def activate(self):
        """Bind exception hooks to monitor for critical system crashes."""
        if self.active:
            return

        self._original_excepthook = sys.excepthook
        sys.excepthook = self._handle_uncaught_exception
        
        try:
            loop = asyncio.get_running_loop()
            self._original_async_handler = loop.get_exception_handler()
            loop.set_exception_handler(self._handle_async_exception)
        except RuntimeError:
            pass # No loop running yet

        self.active = True
        logger.info("🛡️ Autonomous Immune System activated.")

    def _handle_uncaught_exception(self, exc_type, exc_value, exc_traceback):
        """Handle synchronous unhandled exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical("💥 CRITICAL CRASH DETECTED. Immune System engaging...", exc_info=(exc_type, exc_value, exc_traceback))
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        # We must run the healing process in a safe synchronous wrapper or new thread
        # because the main thread is crashing.
        self._trigger_healing_process_sync(tb_str)
        
        # Call original hook to exit
        self._original_excepthook(exc_type, exc_value, exc_traceback)

    def _handle_async_exception(self, loop, context):
        """Handle asynchronous unhandled exceptions in the event loop."""
        msg = context.get("exception", context.get("message", "Unknown async error"))
        logger.error(f"⚠️ Asynchronous fault detected: {msg}")
        
        exception = context.get('exception')
        if exception:
            tb_str = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
            asyncio.create_task(self._diagnose_and_heal(tb_str))
        
        if self._original_async_handler:
            self._original_async_handler(loop, context)
        else:
            loop.default_exception_handler(context)

    def _trigger_healing_process_sync(self, tb_str: str):
        """Synchronous wrapper for catastrophic crashes."""
        try:
            # We can't easily await here if the loop is dead, so we just log the intent
            # In a fully decentralized mesh, we would broadcast the crash to another node to fix us.
            crash_file = self.crash_logs_dir / f"crash_{int(datetime.now().timestamp())}.log"
            with open(crash_file, "w") as f:
                f.write(tb_str)
            logger.info(f"Crash report saved to {crash_file}. Immune System will attempt to patch on next boot.")
        except OSError as e:
            logger.error(f"Immune System failed to log crash (disk/permissions issue): {e}")

    async def _diagnose_and_heal(self, tb_str: str):
        """
        The core DevOps loop: Analyze trace, write patch, apply, and reload.
        """
        if self._is_healing:
            return
        
        self._is_healing = True
        logger.info("🚑 Immune System diagnosing fault...")

        try:
            # 1. Save the crash log
            crash_id = f"fault_{int(datetime.now().timestamp())}"
            with open(self.crash_logs_dir / f"{crash_id}.log", "w") as f:
                f.write(tb_str)

            # 2. Extract the file and line number that caused the crash in our codebase
            target_file = None
            for line in tb_str.split('\n'):
                if 'File "' in line and 'backend/app' in line:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        target_file = parts[1]
                        break

            if not target_file or not os.path.exists(target_file):
                logger.warning("Immune System: Fault was outside ALAS source code. Cannot auto-patch.")
                return

            # Read the buggy file
            with open(target_file, "r") as f:
                code_context = f.read()

            # 3. Ask the ToT Reasoner / CodeAgent to formulate a patch
            from backend.app.llm.engine import LLMEngine
            engine = LLMEngine()
            
            prompt = f"""You are the ALAS Autonomous Immune System (Phase 16).
A subsystem has crashed. Analyze the following stack trace and the source file.
Identify the bug and provide ONLY a unified diff patch to fix it. 

Stack Trace:
{tb_str}

File ({target_file}):
```python
{code_context}
```

Provide your fix. Explain the root cause briefly, then output the patched code."""

            logger.info(f"🧠 Synthesizing cure for {target_file}...")
            response = await engine.generate(prompt)

            # 4. Save the proposed patch
            patch_file = self.patches_dir / f"{crash_id}_cure.md"
            with open(patch_file, "w") as f:
                f.write(f"Target: {target_file}\n\n{response}")
            
            logger.info(f"💉 Cure synthesized and saved to {patch_file}. Auto-patching is disabled in safe mode.")
            # Future (Phase 16 full autonomous mode):
            # Apply the diff directly using standard patch tools and call os.execv() to reload.

        except Exception as e:
            logger.error(f"Immune System failed to heal fault: {e}")
        finally:
            self._is_healing = False

# Global singleton
_immune_system = None

def get_immune_system() -> ImmuneSystem:
    global _immune_system
    if _immune_system is None:
        _immune_system = ImmuneSystem()
    return _immune_system
