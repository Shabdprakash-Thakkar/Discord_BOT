using Microsoft.AspNetCore.Mvc;
using Dashboard.Backend.Services;
using Dashboard.Backend.Models;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace Dashboard.Backend.Controllers
{
    [ApiController]
    [Route("api/guilds/{guildId}/notext")]
    public class NoTextController : ControllerBase
    {
        private readonly PythonApiService _pythonApiService;

        public NoTextController(PythonApiService pythonApiService)
        {
            _pythonApiService = pythonApiService;
        }

        [HttpGet("channels")]
        public async Task<ActionResult<IEnumerable<NoTextChannel>>> GetNoTextChannels(int guildId)
        {
            var channels = await _pythonApiService.GetAsync<IEnumerable<NoTextChannel>>($"/guilds/{guildId}/no-text-channels");
            return Ok(channels);
        }

        [HttpPost("channels")]
        public async Task<IActionResult> AddNoTextChannel(int guildId, [FromBody] NoTextChannel channel)
        {
            await _pythonApiService.PostAsync<object>($"/guilds/{guildId}/no-text-channels", channel);
            return Ok();
        }

        [HttpDelete("channels/{channelId}")]
        public async Task<IActionResult> RemoveNoTextChannel(int guildId, int channelId)
        {
            await _pythonApiService.DeleteAsync($"/guilds/{guildId}/no-text-channels/{channelId}");
            return Ok();
        }

        [HttpGet("bypass-roles")]
        public async Task<ActionResult<IEnumerable<int>>> GetBypassRoles(int guildId)
        {
            var roles = await _pythonApiService.GetAsync<IEnumerable<int>>($"/guilds/{guildId}/bypass-roles");
            return Ok(roles);
        }

        [HttpPost("bypass-roles")]
        public async Task<IActionResult> AddBypassRole(int guildId, [FromBody] BypassRole role)
        {
            await _pythonApiService.PostAsync<object>($"/guilds/{guildId}/bypass-roles", role);
            return Ok();
        }

        [HttpDelete("bypass-roles/{roleId}")]
        public async Task<IActionResult> RemoveBypassRole(int guildId, int roleId)
        {
            await _pythonApiService.DeleteAsync($"/guilds/{guildId}/bypass-roles/{roleId}");
            return Ok();
        }
    }
}