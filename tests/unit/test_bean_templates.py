class TestContractDrivenBeanSections:
    """Placeholders replaced by data derived from the contract (live-enrichment run)."""

    def _api(self):  # type: ignore[no-untyped-def]
        from repo_mirror_kit.harvester.analyzers.surfaces import ApiSurface

        return ApiSurface(
            name="POST /x",
            method="POST",
            path="/x",
            request_schema={
                "fields": [
                    {
                        "name": "name",
                        "type": "string",
                        "required": True,
                        "source": "body",
                    }
                ],
                "confidence": "declared",
            },
            response_schema={
                "fields": [
                    {
                        "name": "id",
                        "type": "integer",
                        "required": True,
                        "source": "body",
                    }
                ],
                "confidence": "declared",
                "status": 201,
                "errors": [{"status": 400, "message": "name required"}],
            },
        )

    def test_examples_and_errors_have_no_todo(self) -> None:
        from repo_mirror_kit.harvester.beans.templates import render_api_bean

        text = render_api_bean(self._api(), "BEAN-001")
        assert (
            '"name": "string"' in text
            and '"id": 1' in text
            and "Example success response (201)" in text
        )
        assert "| `400` | name required |" in text
        assert "TODO: Add example" not in text and "TODO: Define error" not in text

    def test_secret_like_config_defaults_are_withheld(self) -> None:
        from repo_mirror_kit.harvester.analyzers.surfaces import ConfigSurface
        from repo_mirror_kit.harvester.beans.templates import render_config_bean

        secret = ConfigSurface(
            name="API_KEY", env_var_name="API_KEY", default_value="demo-key"
        )
        plain = ConfigSurface(name="PORT", env_var_name="PORT", default_value="8080")
        assert "demo-key" not in render_config_bean(secret, "BEAN-001")
        assert "value withheld" in render_config_bean(secret, "BEAN-001")
        assert "`8080`" in render_config_bean(plain, "BEAN-002")
