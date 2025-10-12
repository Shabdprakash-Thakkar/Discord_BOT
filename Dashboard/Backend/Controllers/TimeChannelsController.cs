using Microsoft.AspNetCore.Mvc;
using Dashboard.Backend.Services;
using Dashboard.Backend.Models;
using System.Threading.Tasks;

namespace Dashboard.Backend.Controllers
{
    [ApiController]
    [Route("api/guilds/{guildId}/timechannels")]
    public class TimeChannelsController : ControllerBase
    {
        private readonly PythonApiService _pythonApiService;

        public TimeChannelsController(PythonApiService pythonApiService)
        {
            _pythonApiService = pythonApiService;
        }

        [HttpGet]
        public async Task<ActionResult<TimeChannels>> GetTimeChannels(int guildId)
        {
            var channels = await _pythonApiService.GetAsync<TimeChannels>($"/guilds/{guildId}/time-channels");
            if (channels == null)
            {
                return NotFound();
            }
            return Ok(channels);
        }

        [HttpPost]
        public async Task<IActionResult> SetTimeChannels(int guildId, [FromBody] TimeChannels channels)
        {
            await _pythonApiService.PostAsync<object>($"/guilds/{guildId}/time-channels", channels);
            return Ok();
        }
    }
}