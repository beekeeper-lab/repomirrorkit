using System.ComponentModel.DataAnnotations;

namespace Api.Models;

public class Item
{
    public int Id { get; set; }
    [Required, StringLength(50)]
    public string Name { get; set; } = "";
    public int? Qty { get; set; }
}

public class CreateItemDto
{
    [Required]
    [StringLength(50, MinimumLength = 2)]
    public string Name { get; set; } = "";

    [Range(1, 100)]
    public int Qty { get; set; }
}
