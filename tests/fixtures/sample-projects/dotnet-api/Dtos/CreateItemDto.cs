using System.ComponentModel.DataAnnotations;

namespace Api.Dtos;

public class CreateItemDto
{
    [Required]
    [StringLength(50, MinimumLength = 2)]
    public string Name { get; set; } = "";

    [Range(1, 100)]
    public int Qty { get; set; }
}
