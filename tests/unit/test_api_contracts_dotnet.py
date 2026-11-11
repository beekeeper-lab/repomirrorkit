"""Tests for ASP.NET Core contract extraction."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.api_contracts_dotnet import (
    populate_dotnet_api_contracts,
)
from repo_mirror_kit.harvester.analyzers.surfaces import ApiSurface, SourceRef

CTRL = """\
using System.ComponentModel.DataAnnotations;
[ApiController]
[Route("api/[controller]")]
public class ItemsController : ControllerBase
{
    [HttpPost]
    public async Task<ActionResult<ItemDto>> Create([FromBody] CreateItemDto dto)
    {
        if (dto == null) return BadRequest();
        return CreatedAtAction("x", new ItemDto());
    }

    [HttpGet("{id}")]
    public ActionResult<List<ItemDto>> Get(int id, [FromQuery] string? q) => Ok();
}
public record CreateItemDto([Required] string Name, int Qty);
public class ItemDto {
    [Required][StringLength(50)] public string Name { get; set; }
    public int? Qty { get; set; }
    public required string Sku { get; init; }
}
"""


def _surface(method: str, path: str, line: int) -> ApiSurface:
    return ApiSurface(
        name=f"{method} {path}",
        method=method,
        path=path,
        source_refs=[SourceRef(file_path="C.cs", start_line=line)],
    )


def test_controller_contracts(tmp_path: Path) -> None:
    (tmp_path / "C.cs").write_text(CTRL)
    post = _surface("POST", "/api/items", 6)
    get = _surface("GET", "/api/items/{id}", 13)
    assert populate_dotnet_api_contracts([post, get], tmp_path, ["C.cs"]) == 2

    req = {f["name"]: f for f in post.request_schema["fields"]}
    assert req["Name"]["required"] is True and req["Qty"]["type"] == "integer"
    assert post.response_schema["confidence"] == "declared"
    resp = {f["name"]: f for f in post.response_schema["fields"]}
    assert resp["Name"]["rules"] == ["max_length=50"]
    assert resp["Sku"]["required"] is True and resp["Qty"]["required"] is False
    assert post.response_schema["errors"] == [{"status": 400}]

    q = {(f["source"], f["name"]) for f in get.request_schema["fields"]}
    assert q == {("path", "id"), ("query", "q")}
    assert get.response_schema["is_array"] is True


def test_non_cs_and_missing_untouched(tmp_path: Path) -> None:
    py = ApiSurface(
        name="g",
        method="GET",
        path="/",
        source_refs=[SourceRef(file_path="a.py", start_line=1)],
    )
    assert populate_dotnet_api_contracts([py], tmp_path, []) == 0
    assert py.request_schema == {}
