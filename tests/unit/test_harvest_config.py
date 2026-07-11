"""Tests for HarvestConfig dataclass and configuration utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_mirror_kit.harvester.config import (
    DEFAULT_EXCLUDE_GLOBS,
    DEFAULT_MAX_FILE_BYTES,
    ConfigValidationError,
    HarvestConfig,
    merge_exclude_globs,
    parse_glob_patterns,
)


class TestHarvestConfigLLMKey:
    """LLM enrichment + missing-key behavior (BEAN-045 + BEAN-056).

    Default-on per BEAN-056: a missing key must NOT raise — it would break
    every default invocation. Instead we emit a stderr warning and
    silently downgrade llm_enabled to False. Helpful pointer text is
    preserved from BEAN-045.
    """

    def test_default_llm_enabled_matches_cli_default(self) -> None:
        """BEAN-059: HarvestConfig and the CLI share one default source.

        A bare HarvestConfig (no key in play) must behave like a bare CLI
        invocation: enrichment attempts to run and downgrades on missing key.
        """
        from repo_mirror_kit.harvester.config import DEFAULT_LLM_ENABLED

        assert DEFAULT_LLM_ENABLED is True
        assert (
            HarvestConfig.__dataclass_fields__["llm_enabled"].default
            is DEFAULT_LLM_ENABLED
        )

    def test_missing_key_with_llm_enabled_warns_and_downgrades(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        config = HarvestConfig(
            repo="https://example.com/repo.git",
            llm_enabled=True,
            llm_api_key=None,
        )
        # Downgraded silently, not raised.
        assert config.llm_enabled is False

        # Warning text on stderr with the actionable guidance.
        captured = capsys.readouterr()
        assert "ANTHROPIC_API_KEY" in captured.err
        assert "https://console.anthropic.com/settings/keys" in captured.err
        assert "export ANTHROPIC_API_KEY=" in captured.err
        assert "--no-llm" in captured.err

    def test_present_key_with_llm_enabled_succeeds(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        config = HarvestConfig(
            repo="https://example.com/repo.git",
            llm_enabled=True,
            llm_api_key="sk-ant-fake",
        )
        assert config.llm_enabled is True
        # No warning when the key is present.
        assert capsys.readouterr().err == ""

    def test_explicit_disable_does_not_warn(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # llm_enabled=False (the --no-llm path) must never warn, even
        # when the key happens to be missing too.
        config = HarvestConfig(
            repo="https://example.com/repo.git",
            llm_enabled=False,
            llm_api_key=None,
        )
        assert config.llm_enabled is False
        assert capsys.readouterr().err == ""


class TestHarvestConfigUrlValidation:
    """HarvestConfig must enforce the canonical clone-URL allow-list (BEAN-044)."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/user/repo.git",
            "ssh://git@github.com/user/repo.git",
            "git@github.com:user/repo.git",
            "/abs/local/path",
        ],
    )
    def test_accepts_supported_urls(self, url: str) -> None:
        # Should construct without raising.
        HarvestConfig(repo=url)

    @pytest.mark.parametrize(
        "url",
        [
            "--upload-pack=evil",
            "ftp://bad/scheme",
            "github.com/no/scheme",
            "with spaces invalid",
        ],
    )
    def test_rejects_invalid_urls(self, url: str) -> None:
        with pytest.raises(ConfigValidationError):
            HarvestConfig(repo=url)


class TestHarvestConfigDefaults:
    """Verify that HarvestConfig defaults match the spec."""

    def test_default_exclude_globs(self) -> None:
        config = HarvestConfig(repo="https://example.com/repo.git")
        assert config.exclude == DEFAULT_EXCLUDE_GLOBS
        assert "node_modules" in config.exclude
        assert ".git" in config.exclude
        assert ".venv" in config.exclude
        assert "**/*.min.*" in config.exclude

    def test_default_max_file_bytes(self) -> None:
        config = HarvestConfig(repo="https://example.com/repo.git")
        assert config.max_file_bytes == 1_000_000
        assert config.max_file_bytes == DEFAULT_MAX_FILE_BYTES

    def test_default_fail_on_gaps_is_true(self) -> None:
        config = HarvestConfig(repo="https://example.com/repo.git")
        assert config.fail_on_gaps is True

    def test_default_log_level_is_info(self) -> None:
        config = HarvestConfig(repo="https://example.com/repo.git")
        assert config.log_level == "info"

    def test_default_ref_is_none(self) -> None:
        config = HarvestConfig(repo="https://example.com/repo.git")
        assert config.ref is None

    def test_default_out_is_none(self) -> None:
        config = HarvestConfig(repo="https://example.com/repo.git")
        assert config.out is None

    def test_default_include_is_empty(self) -> None:
        config = HarvestConfig(repo="https://example.com/repo.git")
        assert config.include == ()

    def test_default_resume_is_false(self) -> None:
        config = HarvestConfig(repo="https://example.com/repo.git")
        assert config.resume is False


class TestHarvestConfigTypes:
    """Verify that HarvestConfig fields have correct types."""

    def test_repo_is_str(self) -> None:
        config = HarvestConfig(repo="https://example.com/repo.git")
        assert isinstance(config.repo, str)

    def test_out_accepts_path(self) -> None:
        config = HarvestConfig(
            repo="https://example.com/repo.git",
            out=Path("/tmp/output"),
        )
        assert isinstance(config.out, Path)
        assert config.out == Path("/tmp/output")

    def test_include_is_tuple(self) -> None:
        config = HarvestConfig(
            repo="https://example.com/repo.git",
            include=("*.py", "*.md"),
        )
        assert isinstance(config.include, tuple)
        assert config.include == ("*.py", "*.md")

    def test_exclude_is_tuple(self) -> None:
        config = HarvestConfig(
            repo="https://example.com/repo.git",
            exclude=("*.log",),
        )
        assert isinstance(config.exclude, tuple)

    def test_frozen_dataclass_prevents_mutation(self) -> None:
        config = HarvestConfig(repo="https://example.com/repo.git")
        with pytest.raises(AttributeError):
            config.repo = "other"  # type: ignore[misc]


class TestHarvestConfigValidation:
    """Verify that HarvestConfig validation catches invalid inputs."""

    def test_empty_repo_raises_error(self) -> None:
        with pytest.raises(ConfigValidationError, match="--repo is required"):
            HarvestConfig(repo="")

    def test_invalid_log_level_raises_error(self) -> None:
        with pytest.raises(ConfigValidationError, match="Invalid --log-level"):
            HarvestConfig(repo="https://example.com/repo.git", log_level="verbose")

    def test_log_level_case_insensitive(self) -> None:
        config = HarvestConfig(repo="https://example.com/repo.git", log_level="DEBUG")
        assert config.log_level == "debug"

    def test_log_level_mixed_case(self) -> None:
        config = HarvestConfig(repo="https://example.com/repo.git", log_level="Warn")
        assert config.log_level == "warn"

    def test_valid_log_levels(self) -> None:
        for level in ("debug", "info", "warn", "error"):
            config = HarvestConfig(repo="https://example.com/repo.git", log_level=level)
            assert config.log_level == level

    def test_negative_max_file_bytes_raises_error(self) -> None:
        with pytest.raises(ConfigValidationError, match="must be positive"):
            HarvestConfig(repo="https://example.com/repo.git", max_file_bytes=-1)

    def test_zero_max_file_bytes_raises_error(self) -> None:
        with pytest.raises(ConfigValidationError, match="must be positive"):
            HarvestConfig(repo="https://example.com/repo.git", max_file_bytes=0)


class TestParseGlobPatterns:
    """Verify comma-separated glob pattern parsing."""

    def test_single_pattern(self) -> None:
        assert parse_glob_patterns("*.py") == ("*.py",)

    def test_multiple_patterns(self) -> None:
        assert parse_glob_patterns("*.py,*.md,*.txt") == ("*.py", "*.md", "*.txt")

    def test_strips_whitespace(self) -> None:
        assert parse_glob_patterns("*.py , *.md , *.txt") == ("*.py", "*.md", "*.txt")

    def test_ignores_empty_segments(self) -> None:
        assert parse_glob_patterns("*.py,,*.md") == ("*.py", "*.md")

    def test_empty_string(self) -> None:
        assert parse_glob_patterns("") == ()

    def test_whitespace_only(self) -> None:
        assert parse_glob_patterns("  ,  , ") == ()


class TestMergeExcludeGlobs:
    """Verify merging user excludes with defaults."""

    def test_none_returns_defaults(self) -> None:
        assert merge_exclude_globs(None) == DEFAULT_EXCLUDE_GLOBS

    def test_empty_returns_defaults(self) -> None:
        assert merge_exclude_globs("") == DEFAULT_EXCLUDE_GLOBS

    def test_user_patterns_appended_to_defaults(self) -> None:
        result = merge_exclude_globs("*.log,*.tmp")
        assert result[: len(DEFAULT_EXCLUDE_GLOBS)] == DEFAULT_EXCLUDE_GLOBS
        assert "*.log" in result
        assert "*.tmp" in result

    def test_defaults_preserved(self) -> None:
        result = merge_exclude_globs("custom")
        for default in DEFAULT_EXCLUDE_GLOBS:
            assert default in result


class TestHarvestConfigMirror:
    """Mirror mode + cleanup resolution (BEAN-080).

    Mirror is strict: structural-only output cannot reach mirror grade, so
    a missing key/package fails validation instead of warn-and-degrade.
    """

    _URL = "https://example.com/r.git"

    def test_mirror_without_key_raises(self) -> None:
        with pytest.raises(ConfigValidationError, match="ANTHROPIC_API_KEY"):
            HarvestConfig(repo=self._URL, mirror=True, llm_api_key=None)

    def test_mirror_with_no_llm_raises(self) -> None:
        with pytest.raises(ConfigValidationError, match="--no-llm"):
            HarvestConfig(
                repo=self._URL,
                mirror=True,
                llm_enabled=False,
                llm_api_key="sk-ant-test",
            )

    def test_mirror_without_anthropic_package_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import repo_mirror_kit.harvester.llm.client as llm_client

        monkeypatch.setattr(llm_client, "HAS_ANTHROPIC", False)
        with pytest.raises(ConfigValidationError, match="anthropic"):
            HarvestConfig(repo=self._URL, mirror=True, llm_api_key="sk-ant-test")

    def test_mirror_enables_cleanup_and_fidelity_gate(self) -> None:
        config = HarvestConfig(repo=self._URL, mirror=True, llm_api_key="sk-ant-test")
        assert config.cleanup is True
        assert config.fail_on_fidelity is True
        assert config.llm_enabled is True

    def test_default_run_has_no_cleanup_and_soft_fidelity(self) -> None:
        config = HarvestConfig(repo=self._URL, llm_enabled=False)
        assert config.mirror is False
        assert config.cleanup is False
        assert config.fail_on_fidelity is False

    def test_keep_source_wins_over_mirror(self) -> None:
        config = HarvestConfig(
            repo=self._URL,
            mirror=True,
            keep_source=True,
            llm_api_key="sk-ant-test",
        )
        assert config.cleanup is False

    def test_keep_source_wins_over_explicit_cleanup(self) -> None:
        config = HarvestConfig(
            repo=self._URL, cleanup=True, keep_source=True, llm_enabled=False
        )
        assert config.cleanup is False

    def test_cleanup_flag_without_mirror(self) -> None:
        config = HarvestConfig(repo=self._URL, cleanup=True, llm_enabled=False)
        assert config.cleanup is True
        assert config.mirror is False
        # Cleanup alone does not turn the fidelity gate on.
        assert config.fail_on_fidelity is False

    def test_explicit_no_fail_on_fidelity_respected_in_mirror(self) -> None:
        config = HarvestConfig(
            repo=self._URL,
            mirror=True,
            fail_on_fidelity=False,
            llm_api_key="sk-ant-test",
        )
        assert config.fail_on_fidelity is False
