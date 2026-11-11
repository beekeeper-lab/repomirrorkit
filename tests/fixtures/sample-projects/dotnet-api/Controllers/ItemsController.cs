using Api.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ItemsController : ControllerBase
{
    [HttpGet]
    public ActionResult<List<Item>> List([FromQuery] int? page) => Ok(new List<Item>());

    [HttpPost]
    public async Task<ActionResult<Item>> Create([FromBody] CreateItemDto dto)
    {
        if (string.IsNullOrEmpty(dto.Name)) return BadRequest();
        return CreatedAtAction(nameof(List), new Item { Name = dto.Name });
    }

    [HttpGet("{id}")]
    public ActionResult<Item> Get(int id)
    {
        return NotFound();
    }
}
