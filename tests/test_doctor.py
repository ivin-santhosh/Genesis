"""Machine doctor regression tests; no live services or modifications needed."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from Genesis.runtime import doctor

class TestDoctor(unittest.TestCase):
    def test_core_passes_without_ollama(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(doctor, "STATE_DIR", Path(tmp)):
                result=doctor.inspect(mode="core")
        self.assertEqual(result["overall"], "passed")
        self.assertIn("workflow", [c["name"] for c in result["checks"]])

    def test_missing_optional_dependencies_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(doctor, "STATE_DIR", Path(tmp)):
                with patch.object(doctor.importlib.util, "find_spec", return_value=None):
                    with patch.object(doctor.shutil, "which", return_value=None):
                        with patch.object(doctor, "_ollama_tags", side_effect=OSError("offline")):
                            report=doctor.inspect(mode="full")
        self.assertEqual(report["overall"], "blocked")
        self.assertIn("ollama_api", report["failed"])
        self.assertIn("dependency_mcp", report["failed"])

    def test_safe_repair_creates_only_state_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"new_state"
            with patch.object(doctor, "STATE_DIR", folder):
                self.assertEqual(doctor._check_state_dir(False).status,"warn")
                self.assertFalse(folder.exists())
                self.assertEqual(doctor._check_state_dir(True).status,"pass")
                self.assertTrue(folder.is_dir())

    def test_approval_never_installs_globally(self):
        with patch.object(doctor.sys, "prefix", "/global"):
            with patch.object(doctor.sys, "base_prefix", "/global"):
                self.assertIn("Refusing", doctor._explicit_action("install_dependencies",model=None))

    def test_ollama_deep_inference_is_opt_in(self):
        data={"models":[{"name":"test-model"}]}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(doctor, "STATE_DIR", Path(tmp)):
                with patch.object(doctor, "_ollama_tags", return_value=data):
                    with patch.object(doctor, "_deep_llm_test") as call:
                        doctor.inspect(mode="full",deep=False)
                        call.assert_not_called()

if __name__=="__main__":
    unittest.main()
