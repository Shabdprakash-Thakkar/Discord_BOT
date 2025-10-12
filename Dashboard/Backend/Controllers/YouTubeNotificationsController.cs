using Microsoft.AspNetCore.Mvc;
using Dashboard.Backend.Services;
using Dashboard.Backend.Models;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace Dashboard.Backend.Controllers
{
    [ApiController]
    [Route("api/guilds/{guildId}/youtubenotifications")]
    public class YouTubeNotificationsController : ControllerBase
    {
        private readonly PythonApiService _pythonApiService;

        public YouTubeNotificationsController(PythonApiService pythonApiService)
        {
            _pythonApiService = pythonApiService;
        }

        [HttpGet("find-channel")]
        public async Task<ActionResult<YouTubeChannelFindResult>> FindChannel(string usernameOrHandle)
        {
            var channel = await _pythonApiService.GetAsync<YouTubeChannelFindResult>($"/youtube/find-channel?username_or_handle={usernameOrHandle}");
            if (channel == null)
            {
                return NotFound();
            }
            return Ok(channel);
        }

        [HttpGet]
        public async Task<ActionResult<IEnumerable<YouTubeChannel>>> GetYouTubeNotifications(int guildId)
        {
            var channels = await _pythonApiService.GetAsync<IEnumerable<YouTubeChannel>>($"/guilds/{guildId}/youtube-notifications");
            return Ok(channels);
        }

        [HttpPost]
        public async Task<IActionResult> AddYouTubeNotification(int guildId, [FromBody] YouTubeChannel channel)
        {
            await _pythonApiService.PostAsync<object>($"/guilds/{guildId}/youtube-notifications", channel);
            return Ok();
        }

        [HttpDelete("{ytChannelId}")]
        public async Task<IActionResult> RemoveYouTubeNotification(int guildId, string ytChannelId)
        {
            await _pythonApiService.DeleteAsync($"/guilds/{guildId}/youtube-notifications/{ytChannelId}");
            return Ok();
        }

        [HttpGet("check")]
        public async Task<ActionResult<IEnumerable<object>>> CheckNewVideos(int guildId)
        {
            var newVideos = await _pythonApiService.GetAsync<IEnumerable<object>>($"/guilds/{guildId}/youtube-notifications/check");
            return Ok(newVideos);
        }
    }
}