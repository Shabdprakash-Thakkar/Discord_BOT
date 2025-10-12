namespace Dashboard.Frontend.Models
{
    public class LeaderboardEntry
    {
        public int user_id { get; set; }
        public string? username { get; set; }
        public int level { get; set; }
        public int xp { get; set; }
    }
}