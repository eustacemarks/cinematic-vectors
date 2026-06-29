using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

namespace MovieSearch.Tests;

public class HealthTests(WebApplicationFactory<Program> factory)
    : IClassFixture<WebApplicationFactory<Program>>
{
    [Fact]
    public async Task Health_Returns_Ok()
    {
        var client = factory.CreateClient();
        var response = await client.GetAsync("/health");
        response.EnsureSuccessStatusCode();
    }

    [Fact]
    public async Task Search_Without_Token_Returns_Unauthorized()
    {
        var client = factory.CreateClient();
        var response = await client.GetAsync("/api/v1/movies/search?q=action");
        Assert.Equal(System.Net.HttpStatusCode.Unauthorized, response.StatusCode);
    }
}
