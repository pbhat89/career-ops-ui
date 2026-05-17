"""Tests for services.runner — subprocess wrapper basics."""

from __future__ import annotations

import shutil

import pytest

from services import runner


def test_node_resolves_when_available():
    if shutil.which("node") is None and shutil.which("node.exe") is None:
        pytest.skip("node not on PATH")
    assert runner._node()


def test_run_script_missing_returns_failure(temp_root):
    result = runner.run_script("does-not-exist.mjs")
    assert result.ok is False
    assert result.returncode == 127
    assert "not found" in result.stderr.lower()


def test_run_script_executes_real_node(temp_root, tmp_path):
    if shutil.which("node") is None and shutil.which("node.exe") is None:
        pytest.skip("node not on PATH")
    # Put a tiny .mjs in temp_root that prints JSON
    script = temp_root / "hello.mjs"
    script.write_text('console.log(JSON.stringify({hello: "world"}));\n', encoding="utf-8")
    result = runner.run_script("hello.mjs")
    assert result.ok, result.stderr
    assert '"world"' in result.stdout
    assert result.json() == {"hello": "world"}
