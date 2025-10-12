using Microsoft.AspNetCore.Mvc;
using Dashboard.Backend.Services;
using Dashboard.Backend.Models;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace Dashboard.Backend.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class LeaderboardController : ControllerBase
    {
        private readonly PythonApiService _pythonApiService;

        public LeaderboardController(PythonApiService pythonApiService)
        {
            _pythonApiService = pythonApiService;
        }

        [HttpGet("{guildId}")]
        public async Task<ActionResult<IEnumerable<LeaderboardEntry>>> GetLeaderboard(int guildId)
        {
            var leaderboard = await _pythonApiService.GetAsync<IEnumerable<LeaderboardEntry>>($"/guilds/{guildId}/leaderboard");
            if (leaderboard == null)
            {
                return NotFound();
            }
            return Ok(leaderboard);
        }
    }
}